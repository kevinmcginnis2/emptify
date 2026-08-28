import secrets
from datetime import datetime, timedelta, timezone

from app.config import settings

SESSION_COOKIE_NAME = "emptify_session"
SESSION_TTL_DAYS = 30


def cookie_kwargs() -> dict:
    # Render deploys the frontend and backend on different onrender.com
    # subdomains — a genuinely cross-site relationship, not just cross-origin —
    # so the cookie needs SameSite=None + Secure in production. Locally,
    # localhost:3000 -> localhost:8000 is same-site (same host, different port),
    # so Lax + non-Secure works over plain HTTP without extra dev-only TLS setup.
    if settings.app_env == "production":
        return {"httponly": True, "secure": True, "samesite": "none", "path": "/"}
    return {"httponly": True, "secure": False, "samesite": "lax", "path": "/"}


async def create_session(db, user_id) -> str:
    token = secrets.token_urlsafe(32)
    now = datetime.now(timezone.utc)
    await db.sessions.insert_one(
        {
            "_id": token,
            "user_id": user_id,
            "created_at": now,
            "expires_at": now + timedelta(days=SESSION_TTL_DAYS),
        }
    )
    return token
