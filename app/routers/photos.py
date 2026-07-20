import hashlib
import time

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel

from app.db import connect
from app.routers.deps import current_user
from app.services import photos

router = APIRouter(prefix="/api/photos", tags=["photos"])


@router.post("")
async def upload_photo(
    file: UploadFile = File(...),
    user: dict | None = Depends(current_user),
):
    raw = await file.read()
    try:
        saved = photos.save_upload(raw, file.content_type or "")
    except photos.PhotoError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    _remember_upload(saved["photo_id"], raw, user)
    return saved


def _remember_upload(photo_id: str, raw: bytes, user: dict | None) -> None:
    """Fingerprint the original bytes.

    This is what catches the one abuse pattern worth catching: many accounts
    submitting the same photograph. Hashing the raw upload rather than the
    stored file means a re-encode does not disguise it.
    """
    if user is None:
        return
    try:
        with connect(immediate=True) as conn:
            conn.execute(
                "INSERT OR IGNORE INTO photo_uploads(photo_id, user_id, sha256,"
                " created_at) VALUES(?,?,?,?)",
                (photo_id, user["id"], hashlib.sha256(raw).hexdigest(), int(time.time())),
            )
    except Exception:  # noqa: BLE001 - a fraud signal must not fail an upload
        pass


class RotateRequest(BaseModel):
    photo_id: str


@router.post("/rotate")
def rotate_photo(req: RotateRequest, user: dict | None = Depends(current_user)):
    try:
        rotated = photos.rotate(req.photo_id)
    except photos.PhotoError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    _inherit_fingerprint(req.photo_id, rotated["photo_id"], user)
    return rotated


def _inherit_fingerprint(source_id: str, new_id: str, user: dict | None) -> None:
    """Carry the original's hash onto the rotated copy.

    Rotating changes every byte, so a fresh hash would make one photograph look
    like two — which is exactly the move somebody farming referrals would try.
    """
    if user is None:
        return
    try:
        with connect(immediate=True) as conn:
            row = conn.execute(
                "SELECT sha256 FROM photo_uploads WHERE photo_id=?", (source_id,)
            ).fetchone()
            if row is None:
                return
            conn.execute(
                "INSERT OR IGNORE INTO photo_uploads(photo_id, user_id, sha256,"
                " created_at) VALUES(?,?,?,?)",
                (new_id, user["id"], row["sha256"], int(time.time())),
            )
    except Exception:  # noqa: BLE001 - a fraud signal must not fail a rotation
        pass


@router.get("/demo")
def demo_photo():
    """The demo path uploads nothing — the funnel is walkable with zero input."""
    return photos.ensure_demo_photo()
