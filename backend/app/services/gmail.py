import asyncio
import base64
from datetime import datetime, timezone
from email.mime.text import MIMEText

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build

from app.config import settings

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.modify",
]


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


# PKCE code_verifier is generated per-Flow-instance by authorization_url() but
# is needed again on the separate callback request's Flow instance to exchange
# the code, so it's stashed here keyed by the OAuth `state` in between.
_pending_verifiers: dict[str, str] = {}


def _authorization_url_sync() -> str:
    flow = _build_flow()
    auth_url, state = flow.authorization_url(
        access_type="offline", prompt="consent", include_granted_scopes="true"
    )
    _pending_verifiers[state] = flow.code_verifier
    return auth_url


async def get_authorization_url() -> str:
    return await asyncio.to_thread(_authorization_url_sync)


def _exchange_code_sync(code: str, state: str | None) -> Credentials:
    flow = _build_flow()
    code_verifier = _pending_verifiers.pop(state, None) if state else None
    flow.fetch_token(code=code, code_verifier=code_verifier)
    return flow.credentials


async def exchange_code(code: str, state: str | None) -> Credentials:
    return await asyncio.to_thread(_exchange_code_sync, code, state)


def _get_profile_email_sync(creds: Credentials) -> str:
    service = build("gmail", "v1", credentials=creds)
    profile = service.users().getProfile(userId="me").execute()
    return profile["emailAddress"]


async def get_profile_email(creds: Credentials) -> str:
    return await asyncio.to_thread(_get_profile_email_sync, creds)


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
) -> None:
    service = build("gmail", "v1", credentials=creds)
    message = MIMEText(body_text)
    message["to"] = to_email
    message["subject"] = subject
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
    body: dict = {"raw": raw}
    if gmail_thread_id:
        body["threadId"] = gmail_thread_id
    service.users().messages().send(userId="me", body=body).execute()


async def send_message(
    creds: Credentials,
    to_email: str,
    subject: str,
    body_text: str,
    gmail_thread_id: str | None = None,
) -> None:
    await asyncio.to_thread(_send_message_sync, creds, to_email, subject, body_text, gmail_thread_id)


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
