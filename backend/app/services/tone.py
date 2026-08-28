import asyncio

from anthropic import Anthropic

from app.config import settings

_TONE_INSTRUCTIONS = {
    "shorter": "Cut it down to the essentials — keep the core ask and any concrete details, drop everything else.",
    "warmer": "Make it noticeably friendlier and more personable, even if it already sounds polite — add genuine warmth, not just politeness.",
    "firmer": "Make it noticeably more direct and decisive — remove hedging and soft language, state the ask plainly.",
}

_TONE_TOOL = {
    "name": "emit_rewrite",
    "description": "Rewrite an email draft to a different tone while staying in the same voice.",
    "input_schema": {
        "type": "object",
        "properties": {
            "draft": {"type": "string"},
        },
        "required": ["draft"],
    },
}


def _voice_profile_clause(voice_traits: list[dict], voice_notes: str) -> str:
    if not voice_traits:
        return ""
    traits_joined = "; ".join(f"{t['label']}: {t['value']}" for t in voice_traits)
    notes_clause = f" Additional guidance: {voice_notes}" if voice_notes else ""
    return f" Stay within this voice profile — {traits_joined}.{notes_clause}"


def _rewrite_sync(draft: str, tone: str, voice_traits: list[dict], voice_notes: str) -> str:
    client = Anthropic(api_key=settings.anthropic_api_key)
    instruction = _TONE_INSTRUCTIONS[tone]
    prompt = (
        f"Rewrite this email draft. {instruction}{_voice_profile_clause(voice_traits, voice_notes)} "
        "The rewrite must be genuinely, noticeably different wording from the current draft — don't "
        "just return it unchanged.\n\n"
        f"Current draft:\n{draft}"
    )
    resp = client.messages.create(
        model=settings.anthropic_model,
        max_tokens=1024,
        tools=[_TONE_TOOL],
        tool_choice={"type": "tool", "name": "emit_rewrite"},
        messages=[{"role": "user", "content": prompt}],
    )
    for block in resp.content:
        if block.type == "tool_use":
            return block.input["draft"]
    return draft


async def rewrite_tone(draft: str, tone: str, voice_traits: list[dict], voice_notes: str) -> str:
    return await asyncio.to_thread(_rewrite_sync, draft, tone, voice_traits, voice_notes)
