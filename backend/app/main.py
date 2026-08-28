from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1 import router as api_v1_router
from app.config import settings
from app.db import get_db, ping_db

app = FastAPI(title="Emptify API")

_ALLOWED_ORIGINS = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
_UNSAFE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}

app.add_middleware(
    CORSMiddleware,
    allow_origins=_ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Session auth moved from a custom X-Role header to a cookie (needed for the
# cross-site Render deployment — see app/services/session.py). A SameSite=None
# cookie is attached by the browser to plain cross-site form POSTs, which don't
# trigger a CORS preflight for body-less/simple requests, so the origin
# allowlist above only stops attacker JS from reading the response — it doesn't
# stop the request from being sent and executed. Browsers reliably send Origin
# on every state-changing request (unlike GET), so checking it here closes that
# CSRF gap for the whole app in one place, rather than per-route.
@app.middleware("http")
async def enforce_same_origin_for_mutations(request: Request, call_next):
    if request.method in _UNSAFE_METHODS:
        origin = request.headers.get("origin")
        if origin is None or origin not in _ALLOWED_ORIGINS:
            return JSONResponse(status_code=403, content={"error": "Origin not allowed"})
    return await call_next(request)


app.include_router(api_v1_router)


@app.on_event("startup")
async def ensure_indexes() -> None:
    db = get_db()
    await db.users.create_index("google_sub", unique=True)
    await db.accounts.create_index("email")
    await db.accounts.create_index("user_id")
    await db.threads.create_index([("user_id", 1), ("status", 1)])
    await db.voice_profiles.create_index([("exec_user_id", 1), ("mode", 1)], unique=True)
    await db.exec_ea_relationships.create_index("exec_user_id", unique=True)
    await db.exec_ea_relationships.create_index("ea_user_id")
    await db.sessions.create_index("expires_at", expireAfterSeconds=0)
    await db.oauth_states.create_index("expires_at", expireAfterSeconds=0)


@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc: HTTPException):
    return JSONResponse(status_code=exc.status_code, content={"error": exc.detail})


@app.get("/healthz")
async def healthz():
    db_ok = await ping_db()
    return JSONResponse(
        status_code=200 if db_ok else 503,
        content={"status": "ok" if db_ok else "error", "db": "connected" if db_ok else "unreachable"},
    )
