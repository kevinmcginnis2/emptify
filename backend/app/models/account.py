from datetime import datetime
from typing import Literal

from pydantic import BaseModel

AccountStatus = Literal["connected", "expiring", "reconnect"]


class Account(BaseModel):
    id: str
    user_id: str
    name: str
    type: str
    email: str
    status: AccountStatus
    last_sync: datetime
    internal_domains: str = ""
    oauth_refresh_token: str
    oauth_access_token: str
    oauth_expires_at: datetime
