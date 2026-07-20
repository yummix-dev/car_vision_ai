"""Seam 2, mock implementation.

Returns the user's *real* uploaded photo as "before" and a visibly altered copy
as "after", so the result screen's before/after slider has two genuine image
layers to reveal. The prototype faked this with CSS stripes, which only works on
the read-only example screen.
"""

import asyncio
import io

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter

from app.config import get_settings
from app.models.generation import GenerationJob, GenerationResult
from app.services import photos
from app.services.ai.imagegen_base import ImageGenerator


class MockImageGenerator(ImageGenerator):
    async def generate(self, job: GenerationJob) -> GenerationResult:
        if get_settings().generation_force_error:
            raise RuntimeError("Не удалось точно распознать фото")

        raw, _ = photos.load_bytes(job.source_photo_id)
        source = Image.open(io.BytesIO(raw)).convert("RGB")

        _before_id, before_url = photos.save_generated(source, "before")
        after = await asyncio.to_thread(self._fake_edit, source, job)
        after_id, after_url = photos.save_generated(after, "after")

        return GenerationResult(
            before_url=before_url, after_url=after_url, after_photo_id=after_id
        )

    @staticmethod
    def _fake_edit(source: Image.Image, job: GenerationJob) -> Image.Image:
        """Stand in for inpainting: highlight the target region and warm the image.

        Deliberately obvious — nobody should mistake the mock for a real result.
        """
        img = source.copy()
        w, h = img.size

        # Rough per-category region box, in fractions of the frame.
        boxes = {
            "rul": (0.24, 0.34, 0.76, 0.92),
            "audio": (0.30, 0.28, 0.70, 0.62),
            "bumperF": (0.08, 0.55, 0.92, 0.95),
            "bumperR": (0.08, 0.55, 0.92, 0.95),
            "camF": (0.38, 0.40, 0.62, 0.60),
            "camR": (0.38, 0.40, 0.62, 0.60),
            "park": (0.15, 0.62, 0.85, 0.90),
        }
        fx0, fy0, fx1, fy1 = boxes.get(job.category_id, (0.2, 0.3, 0.8, 0.9))
        box = (int(w * fx0), int(h * fy0), int(w * fx1), int(h * fy1))

        region = img.crop(box)
        region = region.filter(ImageFilter.GaussianBlur(radius=3))
        region = ImageEnhance.Brightness(region).enhance(1.18)
        img.paste(region, box)

        overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)
        draw.rectangle(box, outline=(59, 130, 246, 220), width=max(3, w // 260))
        draw.rectangle(box, fill=(59, 130, 246, 28))
        img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")

        img = ImageEnhance.Color(img).enhance(1.12)
        return img
