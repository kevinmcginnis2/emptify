from datetime import datetime, timezone

from fastapi import Cookie, Depends, HTTPException

from app.db import get_db
from app.services.session import SESSION_COOKIE_NAME


async def get_current_user(
    emptify_session: str | None = Cookie(default=None, alias=SESSION_COOKIE_NAME),
    db=Depends(get_db),
) -> dict:
    if not emptify_session:
        raise HTTPException(status_code=401, detail="Not authenticated")

    session = await db.sessions.find_one({"_id": emptify_session})
    if not session:
        raise HTTPException(status_code=401, detail="Session not found")

    expires_at = session["expires_at"]
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at <= datetime.now(timezone.utc):
        raise HTTPException(status_code=401, detail="Session expired")

    user = await db.users.find_one({"_id": session["user_id"]})
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user


async def resolve_thread_actor(thread: dict, user: dict, db) -> tuple[str, str]:
    """Returns (role, actor_name) for this user acting on this specific thread, or
    raises 403. Role is derived from real ownership/grant — the thread's own
    user_id for the owning exec, or a matching exec_ea_relationships row for a
    granted EA — replacing the old client-asserted X-Role header entirely."""
    if thread.get("user_id") == user["_id"]:
        return "exec", user["name"]

    relationship = await db.exec_ea_relationships.find_one(
        {"exec_user_id": thread.get("user_id"), "ea_user_id": user["_id"]}
    )
    if relationship:
        return "ea", user["name"]

    raise HTTPException(status_code=403, detail="Not authorized for this thread")
