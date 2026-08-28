from fastapi import APIRouter

from app.api.v1.accounts import router as accounts_router
from app.api.v1.audit import router as audit_router
from app.api.v1.threads import router as threads_router
from app.api.v1.voice import router as voice_router

router = APIRouter(prefix="/api/v1")
router.include_router(accounts_router)
router.include_router(audit_router)
router.include_router(threads_router)
router.include_router(voice_router)
