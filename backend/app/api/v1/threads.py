import asyncio
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException

from app.api.v1.deps import require_exec, require_role
from app.db import get_db
from app.services import gmail
from app.services.audit import write_audit_entry

router = APIRouter(prefix="/threads", tags=["threads"])

SEND_UNDO_WINDOW_SECONDS = 12


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
        to_email=thread["from_email"],
        subject=thread["subject"],
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
