import asyncio
import re
from datetime import datetime, timedelta, timezone
from email.utils import getaddresses

from anthropic import Anthropic

from app.config import settings
from app.db import get_db
from app.services import gmail
from app.services.audit import write_audit_entry
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


def _addresses(header_value: str) -> list[str]:
    return [addr for _, addr in getaddresses([header_value]) if addr]


def _extract_messages(full_thread: dict) -> list[dict]:
    result = []
    for msg in full_thread.get("messages", []):
        payload = msg.get("payload", {})
        headers = _headers_dict(payload)
        from_name, from_email = _parse_from(headers.get("from", ""))
        body = extract_body_text(payload).strip()[:MESSAGE_BODY_TRUNCATE]
        internal_date_ms = int(msg.get("internalDate", "0") or "0")
        at = datetime.fromtimestamp(internal_date_ms / 1000, tz=timezone.utc).isoformat()
        result.append(
            {
                "messageId": msg.get("id", ""),
                "from": from_name or from_email,
                "at": at,
                "body": body,
                "to": _addresses(headers.get("to", "")),
                "cc": _addresses(headers.get("cc", "")),
            }
        )
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
            "informational": {
                "type": "boolean",
                "description": (
                    "true if this is a subscription, promotional/marketing email, newsletter, "
                    "donation/fundraising blast, automated notification or digest, or anything else "
                    "that doesn't call for a personal reply"
                ),
            },
            "handoff_suggested": {"type": "boolean"},
            "handoff_reason": {"type": "string"},
            "draft": {"type": "string"},
        },
        "required": ["bucket", "reason", "informational", "handoff_suggested", "handoff_reason", "draft"],
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
        "details from the email, not generic language. First decide whether this email is "
        "informational — a subscription, promotional/marketing email, newsletter, donation/fundraising "
        "blast, automated notification, or digest that doesn't call for a personal reply — and set "
        "informational accordingly. If informational is true, set handoff_suggested false with an "
        "empty handoff_reason and leave draft as an empty string. Otherwise, decide whether this looks "
        "like something an executive assistant usually handles on the exec's behalf (e.g. scheduling "
        "requests, routine logistics) — if so, set handoff_suggested true with a short handoff_reason; "
        "otherwise false with an empty handoff_reason. Then write a complete, ready-to-send draft "
        f"reply to this email, addressing its specific content. "
        f"{_voice_profile_clause(voice_traits, voice_notes)}"
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
    return {
        "bucket": "wait",
        "reason": "",
        "informational": False,
        "handoff_suggested": False,
        "handoff_reason": "",
        "draft": "",
    }


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


_DRAFT_GATE_TOOL = {
    "name": "emit_draft_decision",
    "description": "Decide whether an already-triaged email needs a personal reply drafted.",
    "input_schema": {
        "type": "object",
        "properties": {
            "informational": {
                "type": "boolean",
                "description": (
                    "true if this is a subscription, promotional/marketing email, newsletter, "
                    "donation/fundraising blast, automated notification or digest, or anything else "
                    "that doesn't call for a personal reply"
                ),
            },
            "draft": {
                "type": "string",
                "description": "A complete, ready-to-send draft reply. Empty string if informational is true.",
            },
        },
        "required": ["informational", "draft"],
    },
}


def _draft_gate_sync(
    subject: str,
    from_name: str,
    from_email: str,
    body: str,
    voice_traits: list[dict],
    voice_notes: str,
) -> dict:
    client = Anthropic(api_key=settings.anthropic_api_key)
    prompt = (
        f"From: {from_name} <{from_email}>\nSubject: {subject}\n"
        f"Body:\n{body[:CLASSIFY_BODY_TRUNCATE]}\n\n"
        "First decide whether this email is informational (a subscription, promotional/marketing "
        "email, newsletter, donation/fundraising blast, automated notification, or digest) rather "
        "than something that calls for a personal reply. If it is informational, set informational "
        "true and leave draft as an empty string. Otherwise set informational false and write a "
        f"complete, ready-to-send draft reply addressing its specific content. "
        f"{_voice_profile_clause(voice_traits, voice_notes)}"
    )
    resp = client.messages.create(
        model=settings.anthropic_model,
        max_tokens=1024,
        tools=[_DRAFT_GATE_TOOL],
        tool_choice={"type": "tool", "name": "emit_draft_decision"},
        messages=[{"role": "user", "content": prompt}],
    )
    for block in resp.content:
        if block.type == "tool_use":
            return block.input
    return {"informational": False, "draft": ""}


async def decide_draft(
    subject: str,
    from_name: str,
    from_email: str,
    body: str,
    voice_traits: list[dict],
    voice_notes: str,
) -> dict:
    return await asyncio.to_thread(
        _draft_gate_sync, subject, from_name, from_email, body, voice_traits, voice_notes
    )


def _classification_fields(
    full_thread: dict, messages: list[dict], account: dict
) -> tuple[dict, str, str]:
    """Derive subject/from/reply-to/cc/voice fields from a freshly fetched thread, and
    return them alongside the from_email and latest body needed to run classification."""
    last_message = full_thread["messages"][-1]
    headers = _headers_dict(last_message.get("payload", {}))
    subject = headers.get("subject", "(no subject)")
    from_name, from_email = _parse_from(headers.get("from", ""))
    latest_body = messages[-1]["body"]

    _, reply_to_email = _parse_from(headers.get("reply-to", ""))
    reply_to_email = reply_to_email or from_email
    cc_emails = [a for a in _addresses(headers.get("cc", "")) if a.lower() != account["email"].lower()]

    domain_match = re.search(r"@([\w.-]+)", from_email)
    domain = domain_match.group(1).lower() if domain_match else ""
    voice_mode = classify_domain(from_email, account.get("internal_domains", ""))
    voice_why = _voice_why(voice_mode, domain)

    fields = {
        "from_name": from_name or from_email,
        "from_email": from_email,
        "reply_to_email": reply_to_email,
        "cc_emails": cc_emails,
        "subject": subject,
        "voice_mode": voice_mode,
        "voice_why": voice_why,
        "list_unsubscribe": headers.get("list-unsubscribe", ""),
        "list_unsubscribe_post": headers.get("list-unsubscribe-post", ""),
    }
    return fields, from_name, latest_body


async def _ingest_new_thread(db, account: dict, creds, gmail_thread_id: str) -> None:
    full_thread = await gmail.get_thread_full(creds, gmail_thread_id)
    messages = _extract_messages(full_thread)
    if not messages:
        return

    fields, from_name, latest_body = _classification_fields(full_thread, messages, account)

    voice_profile = await db.voice_profiles.find_one({"_id": fields["voice_mode"]})
    voice_traits = (voice_profile or {}).get("traits", [])
    voice_notes = (voice_profile or {}).get("notes", "")

    classification = await classify_thread(
        fields["subject"], from_name, fields["from_email"], latest_body, voice_traits, voice_notes
    )

    doc = {
        "_id": gmail_thread_id,
        "account_id": account["_id"],
        "account_label": account["name"],
        "account_email": account["email"],
        **fields,
        "bucket": classification.get("bucket", "wait"),
        "reason": classification.get("reason", ""),
        "informational": classification.get("informational", False),
        "read": False,
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


async def _resync_existing_thread(db, account: dict, creds, thread_id: str) -> None:
    doc = await db.threads.find_one({"_id": thread_id})
    if not doc:
        return

    full_thread = await gmail.get_thread_full(creds, thread_id)
    messages = _extract_messages(full_thread)
    if not messages:
        return

    known_ids = {m.get("messageId") for m in doc.get("messages", []) if m.get("messageId")}
    fresh_ids = {m.get("messageId") for m in messages if m.get("messageId")}
    if fresh_ids <= known_ids:
        # Nothing genuinely new — this touch was Emptify's own send rippling through
        # History. Just keep the stored messages current and stop.
        await db.threads.update_one({"_id": thread_id}, {"$set": {"messages": messages}})
        return

    fields, from_name, latest_body = _classification_fields(full_thread, messages, account)

    voice_profile = await db.voice_profiles.find_one({"_id": fields["voice_mode"]})
    voice_traits = (voice_profile or {}).get("traits", [])
    voice_notes = (voice_profile or {}).get("notes", "")

    classification = await classify_thread(
        fields["subject"], from_name, fields["from_email"], latest_body, voice_traits, voice_notes
    )

    await db.threads.update_one(
        {"_id": thread_id},
        {
            "$set": {
                **fields,
                "bucket": classification.get("bucket", "wait"),
                "reason": classification.get("reason", ""),
                "informational": classification.get("informational", False),
                "read": False,
                "messages": messages,
                "draft": classification.get("draft", ""),
                "draft_author": "emptify",
                "version_stack": [],
                "handoff_suggested": classification.get("handoff_suggested", False),
                "handoff_reason": classification.get("handoff_reason", ""),
                "status": "board",
            }
        },
    )
    await write_audit_entry(
        db,
        thread_id=thread_id,
        actor="Emptify Sync",
        action="sync_reclassify",
        account_email=account["email"],
        detail="New message detected directly in Gmail; re-triaged.",
    )


async def _mark_deleted_in_gmail(
    db, thread_id: str, account: dict, detail: str = "Message deleted/trashed directly in Gmail."
) -> None:
    doc = await db.threads.find_one_and_update(
        {"_id": thread_id, "status": {"$ne": "archived"}},
        {"$set": {"status": "archived"}},
        return_document=True,
    )
    if doc:
        await write_audit_entry(
            db,
            thread_id=thread_id,
            actor="Emptify Sync",
            action="sync_archive",
            account_email=account["email"],
            detail=detail,
        )


async def _bootstrap_sync(db, account: dict, creds) -> None:
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

        await _ingest_new_thread(db, account, creds, gmail_thread_id)

    if hit_cap:
        return  # still catching up on the backlog — next call continues from here

    await db.accounts.update_one({"_id": account["_id"]}, {"$set": {"last_sync": datetime.now(timezone.utc)}})
    new_history_id = await gmail.get_current_history_id(creds)
    if new_history_id:
        await db.accounts.update_one({"_id": account["_id"]}, {"$set": {"history_id": new_history_id}})


async def sync_account_board(account: dict) -> None:
    db = get_db()
    creds, refreshed = await gmail.get_valid_credentials(account)
    if refreshed:
        await db.accounts.update_one({"_id": account["_id"]}, {"$set": refreshed})

    history_id = account.get("history_id")
    if not history_id:
        await _bootstrap_sync(db, account, creds)
        return

    records, new_history_id = await gmail.get_history(creds, history_id)
    if records is None:
        # startHistoryId aged out of Gmail's retention window — fall back to a full
        # resync. Anything that changed during the gap is a known, accepted miss.
        await db.accounts.update_one({"_id": account["_id"]}, {"$unset": {"history_id": ""}})
        await _bootstrap_sync(db, account, creds)
        return

    new_thread_ids: set[str] = set()
    touched_thread_ids: set[str] = set()
    deleted_thread_ids: set[str] = set()
    removed_from_inbox_ids: set[str] = set()

    for record in records:
        for added in record.get("messagesAdded", []):
            msg = added.get("message", {})
            thread_id = msg.get("threadId")
            if not thread_id:
                continue
            if await db.threads.find_one({"_id": thread_id}):
                touched_thread_ids.add(thread_id)
            elif "INBOX" in (msg.get("labelIds") or []):
                new_thread_ids.add(thread_id)
        for deleted in record.get("messagesDeleted", []):
            deleted_msg = deleted.get("message", {})
            if "DRAFT" in (deleted_msg.get("labelIds") or []):
                # Gmail's own compose-then-send cleanup (a Draft object created and
                # deleted as part of sending), not a real message deletion.
                continue
            thread_id = deleted_msg.get("threadId")
            if thread_id:
                deleted_thread_ids.add(thread_id)
        for label_change in record.get("labelsAdded", []):
            if "TRASH" in (label_change.get("labelIds") or []):
                thread_id = label_change.get("message", {}).get("threadId")
                if thread_id:
                    deleted_thread_ids.add(thread_id)
        for label_change in record.get("labelsRemoved", []):
            if "INBOX" in (label_change.get("labelIds") or []):
                thread_id = label_change.get("message", {}).get("threadId")
                if thread_id:
                    removed_from_inbox_ids.add(thread_id)

    removed_from_inbox_ids -= deleted_thread_ids

    for thread_id in deleted_thread_ids:
        await _mark_deleted_in_gmail(db, thread_id, account)

    for thread_id in removed_from_inbox_ids:
        await _mark_deleted_in_gmail(
            db, thread_id, account, detail="Message archived/removed from Inbox directly in Gmail."
        )

    all_removed_ids = deleted_thread_ids | removed_from_inbox_ids

    for thread_id in new_thread_ids - all_removed_ids:
        await _ingest_new_thread(db, account, creds, thread_id)

    for thread_id in touched_thread_ids - all_removed_ids:
        await _resync_existing_thread(db, account, creds, thread_id)

    await db.accounts.update_one({"_id": account["_id"]}, {"$set": {"history_id": new_history_id}})


async def sync_board() -> None:
    db = get_db()
    async for account in db.accounts.find({"status": "connected"}):
        try:
            await sync_account_board(account)
        except Exception:
            continue
