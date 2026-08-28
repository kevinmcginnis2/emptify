from datetime import datetime

from pydantic import BaseModel


class User(BaseModel):
    id: str
    google_sub: str
    email: str
    name: str
    picture: str | None = None
    created_at: datetime


class GoogleIdentity(BaseModel):
    google_sub: str
    user_id: str
    email: str
    linked_at: datetime


class Session(BaseModel):
    token: str
    user_id: str
    created_at: datetime
    expires_at: datetime


class OAuthState(BaseModel):
    state: str
    code_verifier: str | None = None
    intent: str
    user_id: str | None = None
    created_at: datetime
    expires_at: datetime


class ExecEaRelationship(BaseModel):
    id: str
    exec_user_id: str
    ea_user_id: str
    created_at: datetime


class PendingEaInvite(BaseModel):
    email: str
    exec_user_id: str
    invited_at: datetime
