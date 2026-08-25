import re
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from fastapi.responses import RedirectResponse

from app.config import settings
from app.db import get_db
from app.services import gmail

router = APIRouter(prefix="/accounts", tags=["accounts"])


def _slugify_email(email: str) -> str:
    local = email.split("@")[0]
    return re.sub(r"[^a-z0-9]+", "-", local.lower()).strip("-")


@router.get("")
async def list_accounts(db=Depends(get_db)):
    accounts = []
    async for doc in db.accounts.find():
        accounts.append(
            {
                "id": doc["_id"],
                "name": doc["name"],
                "type": doc["type"],
                "email": doc["email"],
                "status": doc["status"],
                "lastSync": doc["last_sync"],
                "internalDomains": doc.get("internal_domains", ""),
            }
        )
    return accounts


@router.get("/connect")
async def connect_account():
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

    return RedirectResponse(url=settings.frontend_url)
