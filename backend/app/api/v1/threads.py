import asyncio
from datetime import datetime, timedelta, timezone
from typing import Literal

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel

from app.api.v1.deps import require_exec, require_role
from app.db import get_db
from app.services import gmail, tone as tone_service
from app.services.audit import write_audit_entry
from app.services.triage import sync_board

router = APIRouter(prefix="/threads", tags=["threads"])

SEND_UNDO_WINDOW_SECONDS = 12
VALID_STATUSES = ("board", "withEA", "readyToSend")
EDITABLE_STATUSES = ("board", "withEA", "readyToSend")


class PatchDraftBody(BaseModel):
    draft: str


class ToneBody(BaseModel):
    tone: Literal["shorter", "warmer", "firmer"]


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
        "eaNote": doc.get("ea_note", ""),
        "eaChangeSummary": doc.get("ea_change_summary", ""),
        "draftAtHandoff": doc.get("draft_at_handoff", ""),
    }


@router.get("")
async def list_threads(status: str, account: str | None = None, db=Depends(get_db)):
    if status not in VALID_STATUSES:
        raise HTTPException(status_code=400, detail="status must be 'board', 'withEA', or 'readyToSend'")

    if status == "board":
        await sync_board()

    query: dict = {"status": status}
    if account:
        query["account_id"] = account

    threads = []
    async for doc in db.threads.find(query):
        threads.append(_thread_response(doc))
    return threads


def _reply_subject(subject: str) -> str:
    return subject if subject.strip().lower().startswith("re:") else f"Re: {subject}"


async def dispatch_send(thread_id: str, actor: str) -> None:
    await asyncio.sleep(SEND_UNDO_WINDOW_SECONDS)
    db = get_db()
    thread = await db.threads.find_one({"_id": thread_id})
    if not thread or thread.get("pending_action") != "send":
        return

    account = await db.accounts.find_one({"_id": thread["account_id"]})
    creds, refreshed = await gmail.get_valid_credentials(account)
    if refreshed:
        await db.accounts.update_one({"_id": account["_id"]}, {"$set": refreshed})

    await gmail.send_message(
        creds,
        to_email=thread.get("reply_to_email") or thread["from_email"],
        subject=_reply_subject(thread["subject"]),
        body_text=thread["draft"],
        gmail_thread_id=thread.get("gmail_thread_id") or None,
    )

    await db.threads.update_one(
        {"_id": thread_id},
        {"$unset": {"pending_action": "", "pending_dispatch_at": "", "prev_status": ""}},
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
    background_tasks: BackgroundTasks,
    role=Depends(require_exec),
    db=Depends(get_db),
):
    _role, actor = role
    thread = await db.threads.find_one({"_id": thread_id})
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")
    if thread["status"] not in ("board", "readyToSend"):
        raise HTTPException(status_code=409, detail="Thread is not in a sendable status")

    prev_status = thread["status"]
    dispatch_at = datetime.now(timezone.utc) + timedelta(seconds=SEND_UNDO_WINDOW_SECONDS)
    await db.threads.update_one(
        {"_id": thread_id},
        {
            "$set": {
                "status": "sent",
                "prev_status": prev_status,
                "pending_action": "send",
                "pending_dispatch_at": dispatch_at,
            }
        },
    )
    background_tasks.add_task(dispatch_send, thread_id, actor)
    return {"status": "sent"}


@router.post("/{thread_id}/undo")
async def undo_thread(thread_id: str, role=Depends(require_role), db=Depends(get_db)):
    thread = await db.threads.find_one({"_id": thread_id})
    if not thread or not thread.get("pending_action"):
        raise HTTPException(status_code=409, detail="No pending action to undo")

    prev_status = thread.get("prev_status", "board")
    await db.threads.update_one(
        {"_id": thread_id},
        {
            "$set": {"status": prev_status},
            "$unset": {"pending_action": "", "pending_dispatch_at": "", "prev_status": ""},
        },
    )
    return {"status": prev_status}


@router.patch("/{thread_id}/draft")
async def patch_draft(thread_id: str, body: PatchDraftBody, role=Depends(require_role), db=Depends(get_db)):
    doc = await db.threads.find_one_and_update(
        {"_id": thread_id},
        {"$set": {"draft": body.draft}},
        return_document=True,
    )
    if not doc:
        raise HTTPException(status_code=404, detail="Thread not found")
    return _thread_response(doc)


@router.post("/{thread_id}/tone")
async def tone_thread(thread_id: str, body: ToneBody, role=Depends(require_role), db=Depends(get_db)):
    thread = await db.threads.find_one({"_id": thread_id})
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")
    if thread["status"] not in EDITABLE_STATUSES:
        raise HTTPException(status_code=409, detail="Thread is not in an editable status")

    voice_profile = await db.voice_profiles.find_one({"_id": thread["voice_mode"]})
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
async def revert_thread(thread_id: str, role=Depends(require_role), db=Depends(get_db)):
    thread = await db.threads.find_one({"_id": thread_id})
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")

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
