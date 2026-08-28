import re
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, ConfigDict, Field

from app.api.v1.deps import get_current_user
from app.config import settings
from app.db import get_db
from app.services import gmail
from app.services.session import cookie_kwargs, create_session, SESSION_COOKIE_NAME

router = APIRouter(prefix="/accounts", tags=["accounts"])


class PatchAccountBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    internal_domains: str = Field(alias="internalDomains")


def _to_response(doc: dict) -> dict:
    return {
        "id": doc["_id"],
        "name": doc["name"],
        "type": doc["type"],
        "email": doc["email"],
        "status": doc["status"],
        "lastSync": doc["last_sync"],
        "internalDomains": doc.get("internal_domains", ""),
    }


def _slugify_email(email: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", email.lower()).strip("-")


async def _get_owned_account(db, account_id: str, user_id) -> dict:
    doc = await db.accounts.find_one({"_id": account_id, "user_id": user_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Account not found")
    return doc


@router.get("")
async def list_accounts(user=Depends(get_current_user), db=Depends(get_db)):
    accounts = []
    async for doc in db.accounts.find({"user_id": user["_id"]}):
        accounts.append(_to_response(doc))
    return accounts


@router.get("/connect")
async def connect_account(user=Depends(get_current_user), db=Depends(get_db)):
    auth_url = await gmail.get_authorization_url(intent="connect", user_id=user["_id"], db=db)
    return {"authUrl": auth_url}


@router.patch("/{account_id}")
async def patch_account(
    account_id: str, body: PatchAccountBody, user=Depends(get_current_user), db=Depends(get_db)
):
    await _get_owned_account(db, account_id, user["_id"])
    doc = await db.accounts.find_one_and_update(
        {"_id": account_id},
        {"$set": {"internal_domains": body.internal_domains}},
        return_document=True,
    )
    return _to_response(doc)


@router.post("/{account_id}/reconnect")
async def reconnect_account(account_id: str, user=Depends(get_current_user), db=Depends(get_db)):
    await _get_owned_account(db, account_id, user["_id"])
    auth_url = await gmail.get_authorization_url(intent="connect", user_id=user["_id"], db=db)
    return {"authUrl": auth_url}


def _error_redirect(reason: str) -> RedirectResponse:
    return RedirectResponse(url=f"{settings.frontend_url}/?screen=connect&error={reason}")


async def _link_identity(db, google_sub: str, user_id, email: str) -> None:
    now = datetime.now(timezone.utc)
    await db.google_identities.update_one(
        {"_id": google_sub},
        {"$set": {"user_id": user_id, "email": email, "linked_at": now}},
        upsert=True,
    )


async def _resolve_or_create_login_user(db, google_sub: str, email: str, name: str, picture: str | None) -> dict:
    identity = await db.google_identities.find_one({"_id": google_sub})
    if identity:
        user = await db.users.find_one({"_id": identity["user_id"]})
        if user:
            return user

    now = datetime.now(timezone.utc)
    result = await db.users.insert_one(
        {"google_sub": google_sub, "email": email, "name": name, "picture": picture, "created_at": now}
    )
    await _link_identity(db, google_sub, result.inserted_id, email)
    return await db.users.find_one({"_id": result.inserted_id})


class AccountOwnedElsewhere(Exception):
    """The Gmail address being connected already belongs to a different Emptify
    user. Without this check, re-authenticating as an already-connected mailbox
    (e.g. a shared/delegated inbox, or two different addresses that collide
    under _slugify_email) would silently reassign that account — and every
    thread synced under it — away from its current owner."""


async def _upsert_account(db, user_id, email: str, creds) -> None:
    account_id = _slugify_email(email)
    existing = await db.accounts.find_one({"_id": account_id})
    if existing and existing.get("user_id") is not None and existing["user_id"] != user_id:
        raise AccountOwnedElsewhere()

    now = datetime.now(timezone.utc)
    update: dict = {
        "user_id": user_id,
        "name": email,
        "type": "Work",
        "email": email,
        "status": "connected",
        "last_sync": now,
        "oauth_access_token": creds.token,
        "oauth_expires_at": creds.expiry,
    }
    set_on_insert: dict = {"internal_domains": "", "history_id": None}
    if creds.refresh_token:
        update["oauth_refresh_token"] = creds.refresh_token
    else:
        set_on_insert["oauth_refresh_token"] = ""

    await db.accounts.update_one(
        {"_id": account_id},
        {"$set": update, "$setOnInsert": set_on_insert},
        upsert=True,
    )


@router.get("/oauth/callback")
async def oauth_callback(response: Response, code: str, state: str | None = None, db=Depends(get_db)):
    try:
        creds, oauth_state = await gmail.exchange_code(code, state, db)
        claims = await gmail.verify_id_token(creds)
    except ValueError:
        return _error_redirect("oauth_failed")

    google_sub = claims["sub"]
    email = claims["email"]
    name = claims.get("name") or email
    picture = claims.get("picture")

    intent = oauth_state["intent"]

    if intent == "login":
        user = await _resolve_or_create_login_user(db, google_sub, email, name, picture)
        try:
            await _upsert_account(db, user["_id"], email, creds)
        except AccountOwnedElsewhere:
            return _error_redirect("account_owned_elsewhere")
        await _link_identity(db, google_sub, user["_id"], email)

        pending_invite = await db.pending_ea_invites.find_one_and_delete({"_id": email.lower()})
        if pending_invite:
            await db.exec_ea_relationships.update_one(
                {"exec_user_id": pending_invite["exec_user_id"]},
                {"$set": {"ea_user_id": user["_id"], "created_at": datetime.now(timezone.utc)}},
                upsert=True,
            )

        session_token = await create_session(db, user["_id"])
        redirect = RedirectResponse(url=f"{settings.frontend_url}/")
        redirect.set_cookie(key=SESSION_COOKIE_NAME, value=session_token, **cookie_kwargs())
        return redirect

    # intent == "connect": a logged-in user connecting an additional inbox.
    calling_user_id = oauth_state["user_id"]
    existing_identity = await db.google_identities.find_one({"_id": google_sub})
    if existing_identity and existing_identity["user_id"] != calling_user_id:
        return _error_redirect("identity_linked_elsewhere")

    try:
        await _upsert_account(db, calling_user_id, email, creds)
    except AccountOwnedElsewhere:
        return _error_redirect("account_owned_elsewhere")
    await _link_identity(db, google_sub, calling_user_id, email)
    return RedirectResponse(url=f"{settings.frontend_url}/?screen=connect")
