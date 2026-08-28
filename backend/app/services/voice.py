import asyncio
import base64
import re
from datetime import datetime, timedelta, timezone

from anthropic import Anthropic

from app.config import settings
from app.db import get_db
from app.services import gmail

NOISE_MIN_WORDS = 12
MAX_MESSAGES_PER_ACCOUNT = 60
MAX_SAMPLES_FOR_LLM = 40
BODY_TRUNCATE_CHARS = 600

TRAIT_LABELS = ["Sentence length", "Greeting", "Sign-off", "Formality", "Hedging", "Characteristic phrases"]

_AUTO_REPLY_PHRASES = [
    "out of office",
    "automatic reply",
    "auto-reply",
    "autoreply",
    "away from my email",
    "on vacation",
]

_QUOTE_MARKERS = [
    re.compile(r"^On .{0,120} wrote:\s*$", re.IGNORECASE),
    re.compile(r"^-{2,}\s*Original Message\s*-{2,}", re.IGNORECASE),
    re.compile(r"^>"),
]


def _headers_dict(payload: dict) -> dict:
    return {h["name"].lower(): h["value"] for h in payload.get("headers", [])}


def _is_forward(subject: str) -> bool:
    return "fwd:" in subject.lower() or subject.lower().startswith("fw:")


def _is_auto_response(headers: dict, subject: str) -> bool:
    auto_submitted = headers.get("auto-submitted", "").lower()
    if auto_submitted and auto_submitted != "no":
        return True
    if headers.get("x-autoreply"):
        return True
    subject_lower = subject.lower()
    return any(phrase in subject_lower for phrase in _AUTO_REPLY_PHRASES)


def _decode_body_data(data: str) -> str:
    padded = data + "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(padded).decode("utf-8", errors="replace")


def _find_part(payload: dict, mime_type: str) -> dict | None:
    if payload.get("mimeType") == mime_type and payload.get("body", {}).get("data"):
        return payload
    for part in payload.get("parts", []) or []:
        found = _find_part(part, mime_type)
        if found:
            return found
    return None


def extract_body_text(payload: dict) -> str:
    plain = _find_part(payload, "text/plain")
    if plain:
        return _decode_body_data(plain["body"]["data"])
    html_part = _find_part(payload, "text/html")
    if html_part:
        html = _decode_body_data(html_part["body"]["data"])
        return re.sub(r"<[^>]+>", " ", html)
    return ""


def _extract_new_content(body_text: str) -> str:
    new_lines: list[str] = []
    for line in body_text.splitlines():
        if any(marker.match(line.strip()) for marker in _QUOTE_MARKERS):
            break
        new_lines.append(line)
    return "\n".join(new_lines).strip()


def classify_domain(to_header: str, internal_domains: str) -> str:
    if not to_header:
        return "client"
    first_recipient = to_header.split(",")[0]
    match = re.search(r"@([\w.-]+)", first_recipient)
    if not match:
        return "client"
    domain = match.group(1).lower()
    internal_set = {d.strip().lower() for d in re.split(r"[,\s]+", internal_domains) if d.strip()}
    return "internal" if domain in internal_set else "client"


async def collect_samples(mode: str) -> tuple[list[str], int, int]:
    """Returns (samples_for_llm, qualifying_count, total_sent_estimate)."""
    db = get_db()
    since_date = (datetime.now(timezone.utc) - timedelta(days=90)).strftime("%Y/%m/%d")

    samples: list[str] = []
    qualifying_count = 0
    total_estimate = 0

    async for account in db.accounts.find({"status": "connected"}):
        creds, refreshed = await gmail.get_valid_credentials(account)
        if refreshed:
            await db.accounts.update_one({"_id": account["_id"]}, {"$set": refreshed})

        message_ids, estimate = await gmail.list_sent_since(creds, since_date, MAX_MESSAGES_PER_ACCOUNT)
        total_estimate += estimate

        for message_id in message_ids:
            detail = await gmail.get_message_full(creds, message_id)
            payload = detail.get("payload", {})
            headers = _headers_dict(payload)
            subject = headers.get("subject", "")
            to_header = headers.get("to", "")

            if _is_forward(subject) or _is_auto_response(headers, subject):
                continue

            new_content = _extract_new_content(extract_body_text(payload))
            if len(new_content.split()) < NOISE_MIN_WORDS:
                continue

            if classify_domain(to_header, account.get("internal_domains", "")) != mode:
                continue

            qualifying_count += 1
            if len(samples) < MAX_SAMPLES_FOR_LLM:
                samples.append(new_content[:BODY_TRUNCATE_CHARS])

    return samples, qualifying_count, total_estimate


def _build_voice_prompt(mode: str, samples: list[str]) -> str:
    mode_label = "client-facing" if mode == "client" else "internal"
    joined = "\n\n---\n\n".join(f"Email {i + 1}:\n{s}" for i, s in enumerate(samples))
    return (
        f"Below are {len(samples)} real {mode_label} sent emails from one person. Analyze their "
        f"writing style and extract these exact 6 traits: {', '.join(TRAIT_LABELS)}. Each trait's "
        'value should be a short, specific, plain-English description (like "Short — averages 14 '
        'words per sentence"), not generic advice. Also write a one-to-two sentence default note '
        "suggesting how future drafts in this voice should be steered, written as if the person "
        f"wrote it themselves.\n\n{joined}"
    )


_VOICE_TOOL = {
    "name": "emit_voice_profile",
    "description": "Report the extracted voice-profile traits and a default note.",
    "input_schema": {
        "type": "object",
        "properties": {
            "traits": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "label": {"type": "string"},
                        "value": {"type": "string"},
                    },
                    "required": ["label", "value"],
                },
            },
            "notes": {"type": "string"},
        },
        "required": ["traits", "notes"],
    },
}


def _extract_traits_sync(mode: str, samples: list[str]) -> tuple[list[dict], str]:
    client = Anthropic(api_key=settings.anthropic_api_key)
    resp = client.messages.create(
        model=settings.anthropic_model,
        max_tokens=1024,
        tools=[_VOICE_TOOL],
        tool_choice={"type": "tool", "name": "emit_voice_profile"},
        messages=[{"role": "user", "content": _build_voice_prompt(mode, samples)}],
    )
    for block in resp.content:
        if block.type == "tool_use":
            return block.input["traits"], block.input["notes"]
    return [], ""


async def extract_traits_and_notes(mode: str, samples: list[str]) -> tuple[list[dict], str]:
    if not samples:
        return [], "Not enough sent mail in the last 90 days to build this profile yet."
    return await asyncio.to_thread(_extract_traits_sync, mode, samples)


async def rebuild_profile(mode: str) -> None:
    db = get_db()
    try:
        samples, qualifying_count, total_estimate = await collect_samples(mode)
        traits, default_notes = await extract_traits_and_notes(mode, samples)

        sample_size = f"{qualifying_count} of {total_estimate} sent emails (last 90 days)"
        existing = await db.voice_profiles.find_one({"_id": mode})
        update: dict = {"sample_size": sample_size, "rebuilding": False, "traits": traits}
        if not existing or not existing.get("notes"):
            update["notes"] = default_notes

        await db.voice_profiles.update_one({"_id": mode}, {"$set": update}, upsert=True)
    except Exception:
        await db.voice_profiles.update_one({"_id": mode}, {"$set": {"rebuilding": False}}, upsert=True)
        raise
