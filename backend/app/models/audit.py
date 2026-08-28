from datetime import datetime
from typing import Literal

from pydantic import BaseModel

Actor = Literal["Mara Lindqvist", "Theo Banks", "Emptify Sync"]
Action = Literal[
    "handoff",
    "edit",
    "mark_ready",
    "send",
    "archive",
    "skip",
    "sync_archive",
    "sync_reclassify",
    "delete",
    "remove_from_emptify",
    "unsubscribe",
    "mark_read",
]


class AuditEntry(BaseModel):
    thread_id: str
    actor: Actor
    action: Action
    account_email: str | None = None
    detail: str = ""
    at: datetime
