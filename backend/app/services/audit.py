from datetime import datetime, timezone

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.models.audit import Action, Actor


async def write_audit_entry(
    db: AsyncIOMotorDatabase,
    *,
    thread_id: str,
    actor: Actor,
    action: Action,
    account_email: str | None = None,
    detail: str = "",
) -> None:
    await db.audit_log.insert_one(
        {
            "thread_id": thread_id,
            "actor": actor,
            "action": action,
            "account_email": account_email,
            "detail": detail,
            "at": datetime.now(timezone.utc),
        }
    )
