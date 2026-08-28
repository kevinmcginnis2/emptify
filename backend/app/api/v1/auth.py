from fastapi import APIRouter, Cookie, Depends, Response

from app.api.v1.deps import get_current_user
from app.db import get_db
from app.services import gmail
from app.services.session import SESSION_COOKIE_NAME, cookie_kwargs

router = APIRouter(prefix="/auth", tags=["auth"])


def _user_response(doc: dict) -> dict:
    return {
        "id": str(doc["_id"]),
        "name": doc["name"],
        "email": doc["email"],
        "picture": doc.get("picture"),
    }


@router.get("/login")
async def login(db=Depends(get_db)):
    auth_url = await gmail.get_authorization_url(intent="login", user_id=None, db=db)
    return {"authUrl": auth_url}


@router.get("/me")
async def me(user=Depends(get_current_user), db=Depends(get_db)):
    ea_relationship = await db.exec_ea_relationships.find_one({"exec_user_id": user["_id"]})
    ea = None
    if ea_relationship:
        ea_user = await db.users.find_one({"_id": ea_relationship["ea_user_id"]})
        if ea_user:
            ea = _user_response(ea_user)

    acting_as_ea_for = await db.exec_ea_relationships.find_one({"ea_user_id": user["_id"]})
    ea_of_exec = None
    if acting_as_ea_for:
        exec_user = await db.users.find_one({"_id": acting_as_ea_for["exec_user_id"]})
        if exec_user:
            ea_of_exec = _user_response(exec_user)

    return {**_user_response(user), "ea": ea, "eaOfExec": ea_of_exec}


@router.post("/logout")
async def logout(
    response: Response,
    emptify_session: str | None = Cookie(default=None, alias=SESSION_COOKIE_NAME),
    db=Depends(get_db),
):
    if emptify_session:
        await db.sessions.delete_one({"_id": emptify_session})
    kwargs = cookie_kwargs()
    response.delete_cookie(
        key=SESSION_COOKIE_NAME, path=kwargs["path"], secure=kwargs["secure"], samesite=kwargs["samesite"]
    )
    return {"ok": True}
