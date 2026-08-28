import asyncio

from anthropic import Anthropic

from app.config import settings

_CHANGE_SUMMARY_TOOL = {
    "name": "emit_change_summary",
    "description": "Summarize what changed between an EA's starting draft and their final draft.",
    "input_schema": {
        "type": "object",
        "properties": {
            "summary": {"type": "string"},
        },
        "required": ["summary"],
    },
}


def _summarize_sync(draft_at_handoff: str, final_draft: str) -> str:
    client = Anthropic(api_key=settings.anthropic_api_key)
    prompt = (
        "An executive assistant was handed a draft email reply and edited it before marking it "
        "ready to send. Compare the two versions below and write one specific, concise line "
        "summarizing what the assistant changed, for the executive to scan before sending — from "
        "the assistant's perspective (e.g. \"Shortened the closing paragraph and firmed up the "
        "Friday deadline.\").\n\n"
        f"Starting draft:\n{draft_at_handoff}\n\nFinal draft:\n{final_draft}"
    )
    resp = client.messages.create(
        model=settings.anthropic_model,
        max_tokens=256,
        tools=[_CHANGE_SUMMARY_TOOL],
        tool_choice={"type": "tool", "name": "emit_change_summary"},
        messages=[{"role": "user", "content": prompt}],
    )
    for block in resp.content:
        if block.type == "tool_use":
            return block.input["summary"]
    return "Edited before marking ready."


async def summarize_change(draft_at_handoff: str, final_draft: str) -> str:
    if draft_at_handoff.strip() == final_draft.strip():
        return "Reviewed as-is — no changes."
    return await asyncio.to_thread(_summarize_sync, draft_at_handoff, final_draft)
