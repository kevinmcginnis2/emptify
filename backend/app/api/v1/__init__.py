from fastapi import APIRouter

from app.api.v1.audit import router as audit_router

router = APIRouter(prefix="/api/v1")
router.include_router(audit_router)
