from fastapi import APIRouter, Depends

from app.db import get_db

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("/{thread_id}")
async def get_audit_log(thread_id: str, db=Depends(get_db)):
    cursor = db.audit_log.find({"thread_id": thread_id}).sort("at", 1)
    entries = []
    async for doc in cursor:
        doc["_id"] = str(doc["_id"])
        entries.append(doc)
    return entries
