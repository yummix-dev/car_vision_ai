"""Photo intake, storage and the seeded demo photo.

Local disk is fine for a single shop. If this ever needs multi-instance or CDN
storage, this module is the only place that changes.
"""

import io
import uuid
from pathlib import Path

from PIL import Image, ImageDraw, ImageOps

from app.config import get_settings

ALLOWED_TYPES = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
}
MAX_EDGE = 2048
DEMO_PHOTO_ID = "demo-interior"


class PhotoError(ValueError):
    pass


def _media_dir() -> Path:
    return get_settings().media_path


def _path_for(photo_id: str) -> Path:
    matches = sorted(_media_dir().glob(f"{photo_id}.*"))
    if not matches:
        raise PhotoError(f"Unknown photo: {photo_id}")
    return matches[0]


def url_for(photo_id: str) -> str:
    return f"/media/{_path_for(photo_id).name}"


def load_bytes(photo_id: str) -> tuple[bytes, str]:
    """Return (bytes, media_type) — what the recognition seam needs."""
    path = _path_for(photo_id)
    ext = path.suffix.lstrip(".").lower()
    media_type = next(
        (mt for mt, e in ALLOWED_TYPES.items() if e == ext), "image/jpeg"
    )
    return path.read_bytes(), media_type


def save_upload(raw: bytes, content_type: str) -> dict:
    """Validate, auto-orient, downscale and strip EXIF, then store."""
    if content_type not in ALLOWED_TYPES:
        raise PhotoError(
            "Поддерживаются только JPEG, PNG и WebP."
        )
    if len(raw) > get_settings().max_upload_bytes:
        raise PhotoError(
            f"Файл больше {get_settings().max_upload_mb} МБ."
        )

    try:
        img = Image.open(io.BytesIO(raw))
        img.verify()  # cheap structural check
        img = Image.open(io.BytesIO(raw))
    except Exception as exc:  # noqa: BLE001 - any decode failure is a bad upload
        raise PhotoError("Не удалось прочитать изображение.") from exc

    img = ImageOps.exif_transpose(img)
    img = img.convert("RGB")
    img.thumbnail((MAX_EDGE, MAX_EDGE), Image.LANCZOS)

    photo_id = uuid.uuid4().hex
    path = _media_dir() / f"{photo_id}.jpg"
    # Re-encoding through a fresh image drops EXIF along with it.
    img.save(path, "JPEG", quality=88, optimize=True)

    return {
        "photo_id": photo_id,
        "url": f"/media/{path.name}",
        "width": img.width,
        "height": img.height,
    }


def rotate(photo_id: str, degrees: int = 90) -> dict:
    """Rotate a stored photo, saving the result as a new photo.

    A new id rather than an overwrite: the URL is what the browser caches, and
    the same URL with different bytes is the classic way to show a customer a
    stale image. The superseded file ages out with the usual media sweep.
    """
    path = _path_for(photo_id)
    img = Image.open(path)
    # expand=True so a portrait photo does not get cropped into a landscape box.
    img = img.rotate(-degrees, expand=True).convert("RGB")

    new_id = uuid.uuid4().hex
    new_path = _media_dir() / f"{new_id}.jpg"
    img.save(new_path, "JPEG", quality=88, optimize=True)

    return {
        "photo_id": new_id,
        "url": f"/media/{new_path.name}",
        "width": img.width,
        "height": img.height,
    }


def save_generated(image: Image.Image, suffix: str) -> tuple[str, str]:
    """Persist a generated image. Returns (photo_id, url)."""
    photo_id = f"{uuid.uuid4().hex}-{suffix}"
    path = _media_dir() / f"{photo_id}.jpg"
    image.convert("RGB").save(path, "JPEG", quality=88, optimize=True)
    return photo_id, f"/media/{path.name}"


def ensure_demo_photo() -> dict:
    """Seed a demo photo so the funnel is walkable with zero user input.

    The prototype shipped no image assets, so this draws a placeholder car
    interior procedurally — the same diagonal-stripe motif the UI uses. Drop a
    real photo at media/demo-interior.jpg to replace it.
    """
    existing = sorted(_media_dir().glob(f"{DEMO_PHOTO_ID}.*"))
    if existing:
        return {
            "photo_id": DEMO_PHOTO_ID,
            "url": f"/media/{existing[0].name}",
            "width": 0,
            "height": 0,
        }

    w, h = 1200, 900
    img = Image.new("RGB", (w, h), "#131922")
    draw = ImageDraw.Draw(img)
    for x in range(-h, w, 22):
        draw.polygon(
            [(x, h), (x + 11, h), (x + 11 + h, 0), (x + h, 0)], fill="#171d26"
        )
    # A suggestion of a steering wheel, so the before/after has a subject.
    cx, cy, r = w // 2, int(h * 0.58), 250
    draw.ellipse(
        [cx - r, cy - r, cx + r, cy + r], outline="#2a323d", width=46
    )
    draw.rounded_rectangle(
        [cx - 62, cy - 46, cx + 62, cy + 46], radius=18, fill="#1c232d"
    )

    path = _media_dir() / f"{DEMO_PHOTO_ID}.jpg"
    img.save(path, "JPEG", quality=88, optimize=True)
    return {
        "photo_id": DEMO_PHOTO_ID,
        "url": f"/media/{path.name}",
        "width": w,
        "height": h,
    }
