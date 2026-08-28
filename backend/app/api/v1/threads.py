import asyncio
from datetime import datetime, timedelta, timezone
from typing import Literal

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel

from app.api.v1.deps import get_current_user, resolve_thread_actor
from app.db import get_db
from app.services import gmail, handoff as handoff_service, tone as tone_service, unsubscribe as unsubscribe_service
from app.services.audit import write_audit_entry
from app.services.triage import sync_board

router = APIRouter(prefix="/threads", tags=["threads"])

UNDO_WINDOW_SECONDS = 12
VALID_STATUSES = ("board", "withEA", "readyToSend")
EDITABLE_STATUSES = ("board", "withEA", "readyToSend")


class PatchDraftBody(BaseModel):
    draft: str


class ToneBody(BaseModel):
    tone: Literal["shorter", "warmer", "firmer"]


class HandoffBody(BaseModel):
    note: str


class SendBody(BaseModel):
    cc: list[str] = []


def _check_actionable(role: str, status: str, exec_statuses: tuple[str, ...]) -> None:
    allowed = status in exec_statuses if role == "exec" else status == "withEA"
    if not allowed:
        raise HTTPException(status_code=409, detail="Thread is not in an actionable status")


async def _get_thread_or_404(db, thread_id: str) -> dict:
    thread = await db.threads.find_one({"_id": thread_id})
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")
    return thread


async def _load_actionable_thread(
    thread_id: str, user: dict, db, exec_statuses: tuple[str, ...]
) -> tuple[dict, str, str]:
    """Fetch the thread, derive (role, actor_name) from real ownership/grant (never
    a client-asserted header), and enforce the same status-gating rules that have
    always governed these actions. Raises 404/403/409 as appropriate."""
    thread = await _get_thread_or_404(db, thread_id)
    role_value, actor = await resolve_thread_actor(thread, user, db)
    _check_actionable(role_value, thread["status"], exec_statuses)
    return thread, role_value, actor


def _thread_response(doc: dict) -> dict:
    return {
        "id": doc["_id"],
        "account": doc["account_id"],
        "accountLabel": doc["account_label"],
        "accountEmail": doc["account_email"],
        "from": doc["from_name"],
        "fromEmail": doc["from_email"],
        "replyToEmail": doc.get("reply_to_email") or doc["from_email"],
        "subject": doc["subject"],
        "bucket": doc["bucket"],
        "reason": doc["reason"],
        "informational": doc.get("informational", False),
        "read": doc.get("read", False),
        "voiceMode": doc["voice_mode"],
        "voiceWhy": doc["voice_why"],
        "messages": doc.get("messages", []),
        "draft": doc.get("draft", ""),
        "draftAuthor": doc.get("draft_author", "emptify"),
        "versionStack": doc.get("version_stack", []),
        "handoffSuggested": doc.get("handoff_suggested", False),
        "handoffReason": doc.get("handoff_reason", ""),
        "status": doc["status"],
        "prevStatus": doc.get("prev_status"),
        "ccEmails": doc.get("cc_emails", []),
        "eaNote": doc.get("ea_note", ""),
        "eaChangeSummary": doc.get("ea_change_summary", ""),
        "draftAtHandoff": doc.get("draft_at_handoff", ""),
    }


@router.get("")
async def list_threads(
    status: str,
    account: str | None = None,
    as_ea: bool = False,
    user=Depends(get_current_user),
    db=Depends(get_db),
):
    if status not in VALID_STATUSES:
        raise HTTPException(status_code=400, detail="status must be 'board', 'withEA', or 'readyToSend'")

    if status == "board":
        await sync_board(user["_id"])
        owner_id = user["_id"]
    elif as_ea:
        # The queue this caller is handling on behalf of an exec who granted them
        # access — distinct from an exec's own "with my EA" view below. This
        # sprint's EA view is deliberately 1:1 — whichever single exec has granted
        # access, no multi-exec switcher.
        relationship = await db.exec_ea_relationships.find_one({"ea_user_id": user["_id"]})
        if not relationship:
            return []
        owner_id = relationship["exec_user_id"]
    else:
        # An exec's own withEA/readyToSend threads — the ones they've handed off,
        # scoped to their own account regardless of whether they're also someone
        # else's granted EA.
        owner_id = user["_id"]

    query: dict = {"status": status, "user_id": owner_id}
    if account:
        query["account_id"] = account

    threads = []
    async for doc in db.threads.find(query):
        threads.append(_thread_response(doc))
    return threads


def _reply_subject(subject: str) -> str:
    return subject if subject.strip().lower().startswith("re:") else f"Re: {subject}"


async def dispatch_send(thread_id: str, actor: str) -> None:
    await asyncio.sleep(UNDO_WINDOW_SECONDS)
    db = get_db()
    thread = await db.threads.find_one({"_id": thread_id})
    if not thread or thread.get("pending_action") != "send":
        return

    account = await db.accounts.find_one({"_id": thread["account_id"]})
    creds, refreshed = await gmail.get_valid_credentials(account)
    if refreshed:
        await db.accounts.update_one({"_id": account["_id"]}, {"$set": refreshed})

    to_email = thread.get("reply_to_email") or thread["from_email"]
    cc_emails = thread.get("pending_cc") or []
    response = await gmail.send_message(
        creds,
        to_email=to_email,
        subject=_reply_subject(thread["subject"]),
        body_text=thread["draft"],
        gmail_thread_id=thread.get("gmail_thread_id") or None,
        cc_emails=cc_emails,
    )

    sent_message = {
        "messageId": response.get("id", ""),
        "from": thread["account_email"],
        "at": datetime.now(timezone.utc).isoformat(),
        "body": thread["draft"],
        "to": [to_email],
        "cc": cc_emails,
    }

    await db.threads.update_one(
        {"_id": thread_id},
        {
            "$unset": {"pending_action": "", "pending_dispatch_at": "", "prev_status": "", "pending_cc": ""},
            "$push": {"messages": sent_message},
        },
    )
    await write_audit_entry(
        db,
        thread_id=thread_id,
        actor=actor,
        action="send",
        account_email=thread["account_email"],
    )


@router.post("/{thread_id}/send")
async def send_thread(
    thread_id: str,
    body: SendBody,
    background_tasks: BackgroundTasks,
    user=Depends(get_current_user),
    db=Depends(get_db),
):
    thread, _role, actor = await _load_actionable_thread(
        thread_id, user, db, exec_statuses=("board", "readyToSend")
    )

    prev_status = thread["status"]
    dispatch_at = datetime.now(timezone.utc) + timedelta(seconds=UNDO_WINDOW_SECONDS)
    await db.threads.update_one(
        {"_id": thread_id},
        {
            "$set": {
                "status": "sent",
                "prev_status": prev_status,
                "pending_action": "send",
                "pending_dispatch_at": dispatch_at,
                "pending_cc": body.cc,
            }
        },
    )
    background_tasks.add_task(dispatch_send, thread_id, actor)
    return {"status": "sent"}


async def dispatch_archive(thread_id: str, actor: str) -> None:
    await asyncio.sleep(UNDO_WINDOW_SECONDS)
    db = get_db()
    thread = await db.threads.find_one({"_id": thread_id})
    if not thread or thread.get("pending_action") != "archive":
        return

    account = await db.accounts.find_one({"_id": thread["account_id"]})
    creds, refreshed = await gmail.get_valid_credentials(account)
    if refreshed:
        await db.accounts.update_one({"_id": account["_id"]}, {"$set": refreshed})

    await gmail.archive_thread(creds, thread_id)

    await db.threads.update_one(
        {"_id": thread_id},
        {"$unset": {"pending_action": "", "pending_dispatch_at": "", "prev_status": ""}},
    )
    await write_audit_entry(
        db,
        thread_id=thread_id,
        actor=actor,
        action="archive",
        account_email=thread["account_email"],
    )


@router.post("/{thread_id}/archive")
async def archive_thread_route(
    thread_id: str,
    background_tasks: BackgroundTasks,
    user=Depends(get_current_user),
    db=Depends(get_db),
):
    thread, _role, actor = await _load_actionable_thread(thread_id, user, db, exec_statuses=("board",))

    prev_status = thread["status"]
    dispatch_at = datetime.now(timezone.utc) + timedelta(seconds=UNDO_WINDOW_SECONDS)
    await db.threads.update_one(
        {"_id": thread_id},
        {
            "$set": {
                "status": "archived",
                "prev_status": prev_status,
                "pending_action": "archive",
                "pending_dispatch_at": dispatch_at,
            }
        },
    )
    background_tasks.add_task(dispatch_archive, thread_id, actor)
    return {"status": "archived"}


@router.post("/{thread_id}/skip")
async def skip_thread(thread_id: str, user=Depends(get_current_user), db=Depends(get_db)):
    thread, _role, actor = await _load_actionable_thread(thread_id, user, db, exec_statuses=("board",))

    await db.threads.update_one({"_id": thread_id}, {"$set": {"status": "skipped"}})
    await write_audit_entry(
        db,
        thread_id=thread_id,
        actor=actor,
        action="skip",
        account_email=thread["account_email"],
    )
    return {"status": "skipped"}


@router.post("/{thread_id}/mark-read")
async def mark_read_thread(thread_id: str, user=Depends(get_current_user), db=Depends(get_db)):
    thread, _role, actor = await _load_actionable_thread(thread_id, user, db, exec_statuses=("board",))

    doc = await db.threads.find_one_and_update(
        {"_id": thread_id}, {"$set": {"read": True}}, return_document=True
    )
    await write_audit_entry(
        db,
        thread_id=thread_id,
        actor=actor,
        action="mark_read",
        account_email=thread["account_email"],
    )
    return _thread_response(doc)


@router.post("/{thread_id}/remove")
async def remove_thread(thread_id: str, user=Depends(get_current_user), db=Depends(get_db)):
    thread, _role, actor = await _load_actionable_thread(thread_id, user, db, exec_statuses=("board",))

    await db.threads.update_one({"_id": thread_id}, {"$set": {"status": "removed"}})
    await write_audit_entry(
        db,
        thread_id=thread_id,
        actor=actor,
        action="remove_from_emptify",
        account_email=thread["account_email"],
    )
    return {"status": "removed"}


async def dispatch_delete(thread_id: str, actor: str) -> None:
    await asyncio.sleep(UNDO_WINDOW_SECONDS)
    db = get_db()
    thread = await db.threads.find_one({"_id": thread_id})
    if not thread or thread.get("pending_action") != "delete":
        return

    account = await db.accounts.find_one({"_id": thread["account_id"]})
    creds, refreshed = await gmail.get_valid_credentials(account)
    if refreshed:
        await db.accounts.update_one({"_id": account["_id"]}, {"$set": refreshed})

    await gmail.trash_thread(creds, thread_id)

    await db.threads.update_one(
        {"_id": thread_id},
        {"$unset": {"pending_action": "", "pending_dispatch_at": "", "prev_status": ""}},
    )
    await write_audit_entry(
        db,
        thread_id=thread_id,
        actor=actor,
        action="delete",
        account_email=thread["account_email"],
    )


@router.post("/{thread_id}/delete")
async def delete_thread_route(
    thread_id: str,
    background_tasks: BackgroundTasks,
    user=Depends(get_current_user),
    db=Depends(get_db),
):
    thread, _role, actor = await _load_actionable_thread(thread_id, user, db, exec_statuses=("board",))

    prev_status = thread["status"]
    dispatch_at = datetime.now(timezone.utc) + timedelta(seconds=UNDO_WINDOW_SECONDS)
    await db.threads.update_one(
        {"_id": thread_id},
        {
            "$set": {
                "status": "deleted",
                "prev_status": prev_status,
                "pending_action": "delete",
                "pending_dispatch_at": dispatch_at,
            }
        },
    )
    background_tasks.add_task(dispatch_delete, thread_id, actor)
    return {"status": "deleted"}


@router.post("/{thread_id}/unsubscribe")
async def unsubscribe_thread(thread_id: str, user=Depends(get_current_user), db=Depends(get_db)):
    thread, _role, actor = await _load_actionable_thread(thread_id, user, db, exec_statuses=("board",))

    urls = unsubscribe_service.parse_list_unsubscribe(thread.get("list_unsubscribe", ""))
    https_url = next((u for u in urls if u.lower().startswith("https://")), None)
    one_click_ok = https_url and unsubscribe_service.supports_one_click(thread.get("list_unsubscribe_post", ""))

    mechanism = "reply_fallback"
    if one_click_ok:
        try:
            if await unsubscribe_service.one_click_unsubscribe(https_url):
                mechanism = "one_click"
        except Exception:
            pass  # fall through to the reply fallback below

    if mechanism == "reply_fallback":
        account = await db.accounts.find_one({"_id": thread["account_id"]})
        creds, refreshed = await gmail.get_valid_credentials(account)
        if refreshed:
            await db.accounts.update_one({"_id": account["_id"]}, {"$set": refreshed})
        to_email = thread.get("reply_to_email") or thread["from_email"]
        body_text = "Unsubscribe / remove me from this list."
        response = await gmail.send_message(
            creds,
            to_email=to_email,
            subject=_reply_subject(thread["subject"]),
            body_text=body_text,
            gmail_thread_id=thread.get("gmail_thread_id") or None,
        )
        # Record the reply in the thread's own messages array — same anti-loop fix as
        # dispatch_send — so the next sync recognizes it as Emptify's own outgoing
        # message rather than a genuine new inbound message and spuriously re-triages.
        sent_message = {
            "messageId": response.get("id", ""),
            "from": thread["account_email"],
            "at": datetime.now(timezone.utc).isoformat(),
            "body": body_text,
            "to": [to_email],
            "cc": [],
        }
        await db.threads.update_one({"_id": thread_id}, {"$push": {"messages": sent_message}})

    await write_audit_entry(
        db,
        thread_id=thread_id,
        actor=actor,
        action="unsubscribe",
        account_email=thread["account_email"],
        detail=mechanism,
    )
    return {"mechanism": mechanism}


@router.post("/{thread_id}/undo")
async def undo_thread(thread_id: str, user=Depends(get_current_user), db=Depends(get_db)):
    thread = await _get_thread_or_404(db, thread_id)
    await resolve_thread_actor(thread, user, db)  # 403 if not authorized for this thread
    if not thread.get("pending_action"):
        raise HTTPException(status_code=409, detail="No pending action to undo")

    prev_status = thread.get("prev_status", "board")
    await db.threads.update_one(
        {"_id": thread_id},
        {
            "$set": {"status": prev_status},
            "$unset": {
                "pending_action": "",
                "pending_dispatch_at": "",
                "prev_status": "",
                "pending_cc": "",
            },
        },
    )
    return {"status": prev_status}


@router.patch("/{thread_id}/draft")
async def patch_draft(
    thread_id: str, body: PatchDraftBody, user=Depends(get_current_user), db=Depends(get_db)
):
    thread = await _get_thread_or_404(db, thread_id)
    await resolve_thread_actor(thread, user, db)  # 403 if not authorized for this thread
    doc = await db.threads.find_one_and_update(
        {"_id": thread_id},
        {"$set": {"draft": body.draft}},
        return_document=True,
    )
    return _thread_response(doc)


@router.post("/{thread_id}/tone")
async def tone_thread(
    thread_id: str, body: ToneBody, user=Depends(get_current_user), db=Depends(get_db)
):
    thread = await _get_thread_or_404(db, thread_id)
    await resolve_thread_actor(thread, user, db)  # 403 if not authorized for this thread
    if thread["status"] not in EDITABLE_STATUSES:
        raise HTTPException(status_code=409, detail="Thread is not in an editable status")

    voice_profile = await db.voice_profiles.find_one(
        {"exec_user_id": thread["user_id"], "mode": thread["voice_mode"]}
    )
    voice_traits = (voice_profile or {}).get("traits", [])
    voice_notes = (voice_profile or {}).get("notes", "")

    new_draft = await tone_service.rewrite_tone(thread["draft"], body.tone, voice_traits, voice_notes)

    doc = await db.threads.find_one_and_update(
        {"_id": thread_id},
        {
            "$set": {"draft": new_draft},
            "$push": {"version_stack": thread["draft"]},
        },
        return_document=True,
    )
    return _thread_response(doc)


@router.post("/{thread_id}/revert")
async def revert_thread(thread_id: str, user=Depends(get_current_user), db=Depends(get_db)):
    thread = await _get_thread_or_404(db, thread_id)
    await resolve_thread_actor(thread, user, db)  # 403 if not authorized for this thread

    version_stack = thread.get("version_stack", [])
    if not version_stack:
        raise HTTPException(status_code=409, detail="No prior version to revert to")

    prior_draft = version_stack[-1]
    remaining_stack = version_stack[:-1]

    doc = await db.threads.find_one_and_update(
        {"_id": thread_id},
        {"$set": {"draft": prior_draft, "version_stack": remaining_stack}},
        return_document=True,
    )
    return _thread_response(doc)


@router.post("/{thread_id}/handoff")
async def handoff_thread(
    thread_id: str, body: HandoffBody, user=Depends(get_current_user), db=Depends(get_db)
):
    thread = await _get_thread_or_404(db, thread_id)
    role_value, actor = await resolve_thread_actor(thread, user, db)
    if role_value != "exec":
        raise HTTPException(status_code=403, detail="This action requires being the owning exec")
    if thread["status"] != "board":
        raise HTTPException(status_code=409, detail="Thread is not in a handoff-able status")

    ea_note = body.note.strip() or "Handed off from the board."
    doc = await db.threads.find_one_and_update(
        {"_id": thread_id},
        {"$set": {"status": "withEA", "ea_note": ea_note, "draft_at_handoff": thread["draft"]}},
        return_document=True,
    )
    await write_audit_entry(
        db,
        thread_id=thread_id,
        actor=actor,
        action="handoff",
        account_email=thread["account_email"],
        detail=ea_note,
    )
    return _thread_response(doc)


@router.post("/{thread_id}/mark-ready")
async def mark_ready_thread(thread_id: str, user=Depends(get_current_user), db=Depends(get_db)):
    thread = await _get_thread_or_404(db, thread_id)
    role_value, actor = await resolve_thread_actor(thread, user, db)
    if role_value != "ea":
        raise HTTPException(status_code=403, detail="This action requires being the granted EA")
    if thread["status"] != "withEA":
        raise HTTPException(status_code=409, detail="Thread is not in a mark-ready-able status")

    summary = await handoff_service.summarize_change(thread.get("draft_at_handoff", ""), thread["draft"])

    doc = await db.threads.find_one_and_update(
        {"_id": thread_id},
        {"$set": {"status": "readyToSend", "draft_author": "ea", "ea_change_summary": summary}},
        return_document=True,
    )
    await write_audit_entry(
        db,
        thread_id=thread_id,
        actor=actor,
        action="mark_ready",
        account_email=thread["account_email"],
    )
    return _thread_response(doc)
