import asyncio
import base64
import secrets
from datetime import datetime, timedelta, timezone
from email.mime.text import MIMEText

from google.auth.transport.requests import Request
from google.oauth2 import id_token as google_id_token
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from app.config import settings

SCOPES = [
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.modify",
]

OAUTH_STATE_TTL_SECONDS = 600


def _client_config() -> dict:
    return {
        "web": {
            "client_id": settings.google_client_id,
            "client_secret": settings.google_client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [settings.google_redirect_uri],
        }
    }


def _build_flow() -> Flow:
    flow = Flow.from_client_config(_client_config(), scopes=SCOPES)
    flow.redirect_uri = settings.google_redirect_uri
    return flow


# PKCE code_verifier is generated per-Flow-instance by authorization_url() but is
# needed again on the separate callback request's Flow instance to exchange the
# code. Stashed server-side in Mongo (backend/app/api/v1/db.oauth_states) keyed by
# the OAuth `state`, rather than an in-process dict — the previous in-process
# approach didn't survive multiple Render workers or a restart between authorize
# and callback, and `state` becomes a genuine single-use, TTL'd token this way
# (a real CSRF check) rather than just a lookup key.
def _authorization_url_sync(flow: Flow) -> tuple[str, str, str]:
    auth_url, state = flow.authorization_url(
        access_type="offline", prompt="consent", include_granted_scopes="true"
    )
    return auth_url, state, flow.code_verifier


async def get_authorization_url(intent: str, user_id: str | None, db) -> str:
    flow = _build_flow()
    auth_url, state, code_verifier = await asyncio.to_thread(_authorization_url_sync, flow)
    now = datetime.now(timezone.utc)
    await db.oauth_states.insert_one(
        {
            "_id": state,
            "code_verifier": code_verifier,
            "intent": intent,
            "user_id": user_id,
            "created_at": now,
            "expires_at": now + timedelta(seconds=OAUTH_STATE_TTL_SECONDS),
        }
    )
    return auth_url


def _exchange_code_sync(code: str, code_verifier: str | None) -> Credentials:
    flow = _build_flow()
    flow.fetch_token(code=code, code_verifier=code_verifier)
    return flow.credentials


async def exchange_code(code: str, state: str | None, db) -> tuple[Credentials, dict]:
    if not state:
        raise ValueError("Missing OAuth state")
    oauth_state = await db.oauth_states.find_one_and_delete({"_id": state})
    if not oauth_state:
        raise ValueError("Unknown or already-used OAuth state")
    now = datetime.now(timezone.utc)
    expires_at = oauth_state["expires_at"]
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at <= now:
        raise ValueError("Expired OAuth state")
    creds = await asyncio.to_thread(_exchange_code_sync, code, oauth_state.get("code_verifier"))
    return creds, oauth_state


def _get_profile_email_sync(creds: Credentials) -> str:
    service = build("gmail", "v1", credentials=creds)
    profile = service.users().getProfile(userId="me").execute()
    return profile["emailAddress"]


async def get_profile_email(creds: Credentials) -> str:
    return await asyncio.to_thread(_get_profile_email_sync, creds)


def _verify_id_token_sync(id_token_str: str) -> dict:
    claims = google_id_token.verify_oauth2_token(id_token_str, Request(), audience=settings.google_client_id)
    if not claims.get("email_verified"):
        raise ValueError("Google identity's email is not verified")
    return claims


async def verify_id_token(creds: Credentials) -> dict:
    if not creds.id_token:
        raise ValueError("No ID token on credentials — was the 'openid' scope granted?")
    return await asyncio.to_thread(_verify_id_token_sync, creds.id_token)


def credentials_from_account(account: dict) -> Credentials:
    return Credentials(
        token=account["oauth_access_token"],
        refresh_token=account["oauth_refresh_token"],
        token_uri="https://oauth2.googleapis.com/token",
        client_id=settings.google_client_id,
        client_secret=settings.google_client_secret,
        scopes=SCOPES,
    )


def _refresh_sync(creds: Credentials) -> None:
    creds.refresh(Request())


async def get_valid_credentials(account: dict) -> tuple[Credentials, dict | None]:
    creds = credentials_from_account(account)
    expires_at = account.get("oauth_expires_at")
    if expires_at is not None and expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at is None or expires_at <= datetime.now(timezone.utc):
        await asyncio.to_thread(_refresh_sync, creds)
        updated = {
            "oauth_access_token": creds.token,
            "oauth_expires_at": creds.expiry,
        }
        return creds, updated
    return creds, None


def _send_message_sync(
    creds: Credentials,
    to_email: str,
    subject: str,
    body_text: str,
    gmail_thread_id: str | None,
    cc_emails: list[str] | None,
) -> dict:
    service = build("gmail", "v1", credentials=creds)
    message = MIMEText(body_text)
    message["to"] = to_email
    if cc_emails:
        message["cc"] = ", ".join(cc_emails)
    message["subject"] = subject
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
    body: dict = {"raw": raw}
    if gmail_thread_id:
        body["threadId"] = gmail_thread_id
    return service.users().messages().send(userId="me", body=body).execute()


async def send_message(
    creds: Credentials,
    to_email: str,
    subject: str,
    body_text: str,
    gmail_thread_id: str | None = None,
    cc_emails: list[str] | None = None,
) -> dict:
    return await asyncio.to_thread(
        _send_message_sync, creds, to_email, subject, body_text, gmail_thread_id, cc_emails
    )


def _archive_thread_sync(creds: Credentials, gmail_thread_id: str) -> None:
    service = build("gmail", "v1", credentials=creds)
    service.users().threads().modify(
        userId="me", id=gmail_thread_id, body={"removeLabelIds": ["INBOX"]}
    ).execute()


async def archive_thread(creds: Credentials, gmail_thread_id: str) -> None:
    await asyncio.to_thread(_archive_thread_sync, creds, gmail_thread_id)


def _trash_thread_sync(creds: Credentials, gmail_thread_id: str) -> None:
    service = build("gmail", "v1", credentials=creds)
    service.users().threads().trash(userId="me", id=gmail_thread_id).execute()


async def trash_thread(creds: Credentials, gmail_thread_id: str) -> None:
    await asyncio.to_thread(_trash_thread_sync, creds, gmail_thread_id)


def _list_sent_sync(creds: Credentials, since_date: str, max_results: int) -> tuple[list[str], int]:
    service = build("gmail", "v1", credentials=creds)
    query = f"in:sent after:{since_date}"
    message_ids: list[str] = []
    page_token = None
    total_estimate = 0
    while len(message_ids) < max_results:
        resp = (
            service.users()
            .messages()
            .list(
                userId="me",
                q=query,
                maxResults=min(100, max_results - len(message_ids)),
                pageToken=page_token,
            )
            .execute()
        )
        if page_token is None:
            total_estimate = resp.get("resultSizeEstimate", 0)
        message_ids.extend(m["id"] for m in resp.get("messages", []))
        page_token = resp.get("nextPageToken")
        if not page_token:
            break
    return message_ids, total_estimate


async def list_sent_since(creds: Credentials, since_date: str, max_results: int = 60) -> tuple[list[str], int]:
    return await asyncio.to_thread(_list_sent_sync, creds, since_date, max_results)


def _get_message_full_sync(creds: Credentials, message_id: str) -> dict:
    service = build("gmail", "v1", credentials=creds)
    return service.users().messages().get(userId="me", id=message_id, format="full").execute()


async def get_message_full(creds: Credentials, message_id: str) -> dict:
    return await asyncio.to_thread(_get_message_full_sync, creds, message_id)


def _list_inbox_sync(creds: Credentials, since_date: str, max_results: int) -> tuple[list[str], bool]:
    service = build("gmail", "v1", credentials=creds)
    query = f"in:inbox after:{since_date}"
    message_ids: list[str] = []
    page_token = None
    while len(message_ids) < max_results:
        resp = (
            service.users()
            .messages()
            .list(
                userId="me",
                q=query,
                maxResults=min(100, max_results - len(message_ids)),
                pageToken=page_token,
            )
            .execute()
        )
        message_ids.extend(m["id"] for m in resp.get("messages", []))
        page_token = resp.get("nextPageToken")
        if not page_token:
            break
    hit_cap = len(message_ids) >= max_results
    return message_ids[:max_results], hit_cap


async def list_inbox_since(creds: Credentials, since_date: str, max_results: int) -> tuple[list[str], bool]:
    return await asyncio.to_thread(_list_inbox_sync, creds, since_date, max_results)


def _get_thread_full_sync(creds: Credentials, gmail_thread_id: str) -> dict:
    service = build("gmail", "v1", credentials=creds)
    return service.users().threads().get(userId="me", id=gmail_thread_id, format="full").execute()


async def get_thread_full(creds: Credentials, gmail_thread_id: str) -> dict:
    return await asyncio.to_thread(_get_thread_full_sync, creds, gmail_thread_id)


def _get_current_history_id_sync(creds: Credentials) -> str:
    service = build("gmail", "v1", credentials=creds)
    profile = service.users().getProfile(userId="me").execute()
    return profile["historyId"]


async def get_current_history_id(creds: Credentials) -> str:
    return await asyncio.to_thread(_get_current_history_id_sync, creds)


def _get_history_sync(creds: Credentials, start_history_id: str) -> tuple[list[dict] | None, str | None]:
    service = build("gmail", "v1", credentials=creds)
    records: list[dict] = []
    page_token = None
    new_history_id = None
    while True:
        try:
            resp = (
                service.users()
                .history()
                .list(
                    userId="me",
                    startHistoryId=start_history_id,
                    historyTypes=["messageAdded", "messageDeleted", "labelAdded", "labelRemoved"],
                    pageToken=page_token,
                )
                .execute()
            )
        except HttpError as e:
            if e.resp.status == 404:
                return None, None
            raise
        records.extend(resp.get("history", []))
        if new_history_id is None:
            new_history_id = resp.get("historyId")
        page_token = resp.get("nextPageToken")
        if not page_token:
            break
    return records, new_history_id or start_history_id


async def get_history(creds: Credentials, start_history_id: str) -> tuple[list[dict] | None, str | None]:
    return await asyncio.to_thread(_get_history_sync, creds, start_history_id)
