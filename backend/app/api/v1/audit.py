from fastapi import APIRouter, Depends, HTTPException

from app.api.v1.deps import get_current_user, resolve_thread_actor
from app.db import get_db

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("/{thread_id}")
async def get_audit_log(thread_id: str, user=Depends(get_current_user), db=Depends(get_db)):
    thread = await db.threads.find_one({"_id": thread_id})
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")
    await resolve_thread_actor(thread, user, db)  # 403 if not authorized for this thread

    cursor = db.audit_log.find({"thread_id": thread_id}).sort("at", 1)
    entries = []
    async for doc in cursor:
        doc["_id"] = str(doc["_id"])
        entries.append(doc)
    return entries
