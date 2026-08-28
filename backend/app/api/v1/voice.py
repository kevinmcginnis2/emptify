from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from app.api.v1.deps import get_current_user
from app.db import get_db
from app.services.voice import rebuild_profile

router = APIRouter(prefix="/voice", tags=["voice"])

MODES = ("client", "internal")

_PLACEHOLDER = {
    "sampleSize": "Not built yet — click Rebuild",
    "rebuilding": False,
    "notes": "",
    "traits": [],
}


class PatchNotesBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    notes: str


def _to_response(doc: dict | None) -> dict:
    if not doc:
        return dict(_PLACEHOLDER)
    return {
        "sampleSize": doc.get("sample_size", _PLACEHOLDER["sampleSize"]),
        "rebuilding": doc.get("rebuilding", False),
        "notes": doc.get("notes", ""),
        "traits": doc.get("traits", []),
    }


@router.get("")
async def get_voice(user=Depends(get_current_user), db=Depends(get_db)):
    result = {}
    for mode in MODES:
        doc = await db.voice_profiles.find_one({"exec_user_id": user["_id"], "mode": mode})
        result[mode] = _to_response(doc)
    return result


@router.patch("/{mode}")
async def patch_voice_notes(
    mode: str, body: PatchNotesBody, user=Depends(get_current_user), db=Depends(get_db)
):
    if mode not in MODES:
        raise HTTPException(status_code=400, detail="mode must be 'client' or 'internal'")
    doc = await db.voice_profiles.find_one_and_update(
        {"exec_user_id": user["_id"], "mode": mode},
        {"$set": {"notes": body.notes}},
        upsert=True,
        return_document=True,
    )
    return _to_response(doc)


@router.post("/{mode}/rebuild")
async def rebuild_voice(
    mode: str, background_tasks: BackgroundTasks, user=Depends(get_current_user), db=Depends(get_db)
):
    if mode not in MODES:
        raise HTTPException(status_code=400, detail="mode must be 'client' or 'internal'")
    doc = await db.voice_profiles.find_one_and_update(
        {"exec_user_id": user["_id"], "mode": mode},
        {"$set": {"rebuilding": True}},
        upsert=True,
        return_document=True,
    )
    background_tasks.add_task(rebuild_profile, mode, user["_id"])
    return _to_response(doc)
