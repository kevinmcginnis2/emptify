from datetime import datetime
from typing import Literal

from pydantic import BaseModel

Actor = Literal["Mara Lindqvist", "Theo Banks"]
Action = Literal["handoff", "edit", "mark_ready", "send", "archive", "skip"]


class AuditEntry(BaseModel):
    thread_id: str
    actor: Actor
    action: Action
    account_email: str | None = None
    detail: str = ""
    at: datetime
