import re
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, ConfigDict, Field

from app.config import settings
from app.db import get_db
from app.services import gmail

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


@router.get("")
async def list_accounts(db=Depends(get_db)):
    accounts = []
    async for doc in db.accounts.find():
        accounts.append(_to_response(doc))
    return accounts


@router.get("/connect")
async def connect_account():
    auth_url = await gmail.get_authorization_url()
    return {"authUrl": auth_url}


@router.patch("/{account_id}")
async def patch_account(account_id: str, body: PatchAccountBody, db=Depends(get_db)):
    doc = await db.accounts.find_one_and_update(
        {"_id": account_id},
        {"$set": {"internal_domains": body.internal_domains}},
        return_document=True,
    )
    if not doc:
        raise HTTPException(status_code=404, detail="Account not found")
    return _to_response(doc)


@router.post("/{account_id}/reconnect")
async def reconnect_account(account_id: str, db=Depends(get_db)):
    doc = await db.accounts.find_one({"_id": account_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Account not found")
    auth_url = await gmail.get_authorization_url()
    return {"authUrl": auth_url}


@router.get("/oauth/callback")
async def oauth_callback(code: str, state: str | None = None, db=Depends(get_db)):
    creds = await gmail.exchange_code(code, state)
    email = await gmail.get_profile_email(creds)
    account_id = _slugify_email(email)
    now = datetime.now(timezone.utc)

    update: dict = {
        "name": email,
        "type": "Work",
        "email": email,
        "status": "connected",
        "last_sync": now,
        "oauth_access_token": creds.token,
        "oauth_expires_at": creds.expiry,
    }
    set_on_insert: dict = {"internal_domains": ""}
    if creds.refresh_token:
        update["oauth_refresh_token"] = creds.refresh_token
    else:
        set_on_insert["oauth_refresh_token"] = ""

    await db.accounts.update_one(
        {"_id": account_id},
        {"$set": update, "$setOnInsert": set_on_insert},
        upsert=True,
    )

    return RedirectResponse(url=f"{settings.frontend_url}/?screen=connect")
