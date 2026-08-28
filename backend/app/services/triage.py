import asyncio
import re
from datetime import datetime, timedelta, timezone

from anthropic import Anthropic

from app.config import settings
from app.db import get_db
from app.services import gmail
from app.services.voice import classify_domain, extract_body_text

NEW_MESSAGES_CAP = 20
MESSAGE_BODY_TRUNCATE = 2000
CLASSIFY_BODY_TRUNCATE = 1200

_FROM_RE = re.compile(r'^\s*"?([^"<]*)"?\s*<([^>]+)>\s*$')
_EMAIL_RE = re.compile(r"[\w.+-]+@[\w.-]+")


def _headers_dict(payload: dict) -> dict:
    return {h["name"].lower(): h["value"] for h in payload.get("headers", [])}


def _parse_from(from_header: str) -> tuple[str, str]:
    match = _FROM_RE.match(from_header)
    if match:
        return match.group(1).strip(), match.group(2).strip()
    email_match = _EMAIL_RE.search(from_header)
    email = email_match.group(0) if email_match else from_header
    return "", email


def _extract_messages(full_thread: dict) -> list[dict]:
    result = []
    for msg in full_thread.get("messages", []):
        payload = msg.get("payload", {})
        headers = _headers_dict(payload)
        from_name, from_email = _parse_from(headers.get("from", ""))
        body = extract_body_text(payload).strip()[:MESSAGE_BODY_TRUNCATE]
        internal_date_ms = int(msg.get("internalDate", "0") or "0")
        at = datetime.fromtimestamp(internal_date_ms / 1000, tz=timezone.utc).isoformat()
        result.append({"from": from_name or from_email, "at": at, "body": body})
    return result


def _voice_why(voice_mode: str, domain: str) -> str:
    if voice_mode == "internal":
        return f"From {domain}, one of this account's internal domains — using the internal voice."
    return f"From {domain}, outside this account's internal domains — using the client-facing voice."


_TRIAGE_TOOL = {
    "name": "emit_triage",
    "description": "Classify an inbound email for an executive's triage inbox and draft a reply.",
    "input_schema": {
        "type": "object",
        "properties": {
            "bucket": {"type": "string", "enum": ["today", "week", "wait"]},
            "reason": {"type": "string"},
            "handoff_suggested": {"type": "boolean"},
            "handoff_reason": {"type": "string"},
            "draft": {"type": "string"},
        },
        "required": ["bucket", "reason", "handoff_suggested", "handoff_reason", "draft"],
    },
}


def _voice_profile_clause(voice_traits: list[dict], voice_notes: str) -> str:
    if not voice_traits:
        return "No voice profile is available yet — write the reply in a neutral, professional voice."
    traits_joined = "; ".join(f"{t['label']}: {t['value']}" for t in voice_traits)
    notes_clause = f" Additional guidance: {voice_notes}" if voice_notes else ""
    return f"Write the reply matching this voice profile — {traits_joined}.{notes_clause}"


def _classify_thread_sync(
    subject: str,
    from_name: str,
    from_email: str,
    body: str,
    today_str: str,
    voice_traits: list[dict],
    voice_notes: str,
) -> dict:
    client = Anthropic(api_key=settings.anthropic_api_key)
    prompt = (
        f"Today's date is {today_str}. Classify this inbound email for a busy executive's triage "
        f"inbox.\n\nFrom: {from_name} <{from_email}>\nSubject: {subject}\n"
        f"Body:\n{body[:CLASSIFY_BODY_TRUNCATE]}\n\n"
        "Assign a bucket: 'today' (needs attention today), 'week' (can wait a few days), or 'wait' "
        "(low urgency). Give a one-line, specific reason for that bucket that mentions concrete "
        "details from the email, not generic language. Then decide whether this looks like something "
        "an executive assistant usually handles on the exec's behalf (e.g. scheduling requests, "
        "routine logistics) — if so, set handoff_suggested true with a short handoff_reason; "
        "otherwise false with an empty handoff_reason. "
        "Finally, write a complete, ready-to-send draft reply to this email, addressing its specific "
        f"content. {_voice_profile_clause(voice_traits, voice_notes)}"
    )
    resp = client.messages.create(
        model=settings.anthropic_model,
        max_tokens=1024,
        tools=[_TRIAGE_TOOL],
        tool_choice={"type": "tool", "name": "emit_triage"},
        messages=[{"role": "user", "content": prompt}],
    )
    for block in resp.content:
        if block.type == "tool_use":
            return block.input
    return {"bucket": "wait", "reason": "", "handoff_suggested": False, "handoff_reason": "", "draft": ""}


async def classify_thread(
    subject: str,
    from_name: str,
    from_email: str,
    body: str,
    voice_traits: list[dict],
    voice_notes: str,
) -> dict:
    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return await asyncio.to_thread(
        _classify_thread_sync, subject, from_name, from_email, body, today_str, voice_traits, voice_notes
    )


async def sync_account_board(account: dict) -> None:
    db = get_db()
    creds, refreshed = await gmail.get_valid_credentials(account)
    if refreshed:
        await db.accounts.update_one({"_id": account["_id"]}, {"$set": refreshed})

    since = account.get("last_sync") or (datetime.now(timezone.utc) - timedelta(days=90))
    since_str = since.strftime("%Y/%m/%d")

    message_ids, hit_cap = await gmail.list_inbox_since(creds, since_str, NEW_MESSAGES_CAP)

    seen_thread_ids: set[str] = set()
    for message_id in message_ids:
        meta = await gmail.get_message_full(creds, message_id)
        gmail_thread_id = meta.get("threadId")
        if not gmail_thread_id or gmail_thread_id in seen_thread_ids:
            continue
        seen_thread_ids.add(gmail_thread_id)

        if await db.threads.find_one({"_id": gmail_thread_id}):
            continue

        full_thread = await gmail.get_thread_full(creds, gmail_thread_id)
        messages = _extract_messages(full_thread)
        if not messages:
            continue

        last_message = full_thread["messages"][-1]
        headers = _headers_dict(last_message.get("payload", {}))
        subject = headers.get("subject", "(no subject)")
        from_name, from_email = _parse_from(headers.get("from", ""))
        latest_body = messages[-1]["body"]

        domain_match = re.search(r"@([\w.-]+)", from_email)
        domain = domain_match.group(1).lower() if domain_match else ""
        voice_mode = classify_domain(from_email, account.get("internal_domains", ""))
        voice_why = _voice_why(voice_mode, domain)

        voice_profile = await db.voice_profiles.find_one({"_id": voice_mode})
        voice_traits = (voice_profile or {}).get("traits", [])
        voice_notes = (voice_profile or {}).get("notes", "")

        classification = await classify_thread(
            subject, from_name, from_email, latest_body, voice_traits, voice_notes
        )

        doc = {
            "_id": gmail_thread_id,
            "account_id": account["_id"],
            "account_label": account["name"],
            "account_email": account["email"],
            "from_name": from_name or from_email,
            "from_email": from_email,
            "subject": subject,
            "bucket": classification.get("bucket", "wait"),
            "reason": classification.get("reason", ""),
            "voice_mode": voice_mode,
            "voice_why": voice_why,
            "messages": messages,
            "draft": classification.get("draft", ""),
            "draft_author": "emptify",
            "version_stack": [],
            "handoff_suggested": classification.get("handoff_suggested", False),
            "handoff_reason": classification.get("handoff_reason", ""),
            "status": "board",
            "ea_note": "",
            "ea_change_summary": "",
            "draft_at_handoff": "",
            "gmail_thread_id": gmail_thread_id,
        }
        await db.threads.insert_one(doc)

    if not hit_cap:
        await db.accounts.update_one({"_id": account["_id"]}, {"$set": {"last_sync": datetime.now(timezone.utc)}})


async def sync_board() -> None:
    db = get_db()
    async for account in db.accounts.find({"status": "connected"}):
        try:
            await sync_account_board(account)
        except Exception:
            continue
