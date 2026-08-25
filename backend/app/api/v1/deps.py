from fastapi import Header, HTTPException

ACTOR_NAMES = {"exec": "Mara Lindqvist", "ea": "Theo Banks"}


def require_role(x_role: str | None = Header(default=None)) -> tuple[str, str]:
    if x_role not in ACTOR_NAMES:
        raise HTTPException(status_code=400, detail="X-Role header must be 'exec' or 'ea'")
    return x_role, ACTOR_NAMES[x_role]


def require_exec(x_role: str | None = Header(default=None)) -> tuple[str, str]:
    role, actor = require_role(x_role)
    if role != "exec":
        raise HTTPException(status_code=403, detail="This action requires X-Role: exec")
    return role, actor


def require_ea(x_role: str | None = Header(default=None)) -> tuple[str, str]:
    role, actor = require_role(x_role)
    if role != "ea":
        raise HTTPException(status_code=403, detail="This action requires X-Role: ea")
    return role, actor
