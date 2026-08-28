from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.api.v1.deps import get_current_user
from app.db import get_db

router = APIRouter(prefix="/relationships", tags=["relationships"])


class InviteEaBody(BaseModel):
    eaEmail: str


def _user_response(doc: dict) -> dict:
    return {"id": str(doc["_id"]), "name": doc["name"], "email": doc["email"], "picture": doc.get("picture")}


@router.get("")
async def get_relationship(user=Depends(get_current_user), db=Depends(get_db)):
    relationship = await db.exec_ea_relationships.find_one({"exec_user_id": user["_id"]})
    if relationship:
        ea_user = await db.users.find_one({"_id": relationship["ea_user_id"]})
        if ea_user:
            return {"status": "linked", "ea": _user_response(ea_user)}

    pending = await db.pending_ea_invites.find_one({"exec_user_id": user["_id"]})
    if pending:
        return {"status": "pending", "eaEmail": pending["_id"]}

    return {"status": "none"}


@router.post("")
async def invite_ea(body: InviteEaBody, user=Depends(get_current_user), db=Depends(get_db)):
    email = body.eaEmail.strip().lower()
    now = datetime.now(timezone.utc)

    # Clear any stale pending invite from a previous attempt for this exec.
    await db.pending_ea_invites.delete_many({"exec_user_id": user["_id"]})

    ea_user = await db.users.find_one({"email": email})
    if ea_user:
        await db.exec_ea_relationships.update_one(
            {"exec_user_id": user["_id"]},
            {"$set": {"ea_user_id": ea_user["_id"], "created_at": now}},
            upsert=True,
        )
        return {"status": "linked", "ea": _user_response(ea_user)}

    await db.pending_ea_invites.update_one(
        {"_id": email},
        {"$set": {"exec_user_id": user["_id"], "invited_at": now}},
        upsert=True,
    )
    return {"status": "pending", "eaEmail": email}


@router.delete("")
async def revoke_relationship(user=Depends(get_current_user), db=Depends(get_db)):
    await db.exec_ea_relationships.delete_one({"exec_user_id": user["_id"]})
    await db.pending_ea_invites.delete_many({"exec_user_id": user["_id"]})
    return {"status": "none"}
