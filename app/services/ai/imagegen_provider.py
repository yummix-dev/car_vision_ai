"""Seam 2, real implementation: OpenAI gpt-image-2.

Swap in by setting IMAGEGEN_PROVIDER=provider and OPENAI_API_KEY. No call site
changes.

Notes on the API shape (these are load-bearing):
  * `mask` is optional. We deliberately do not send one: we have no per-pixel
    segmentation of the zone, and a crude rectangle would wipe out real interior
    detail around the part. gpt-image-2 processes every input image at high
    fidelity automatically, so "change only X, keep everything else" as an
    instruction preserves the rest of the photo well enough for a preview.
    If drift ever becomes a problem, add a real mask here — nothing above this
    file has to change.
  * `input_fidelity` must be OMITTED for gpt-image-2 — the request 400s
    otherwise. The model always runs inputs at high fidelity.
  * `size` must have both edges a multiple of 16, max edge <= 3840, aspect
    <= 3:1. It is NOT free-form, so we snap the source aspect onto that grid.
  * The response is base64 in `data[0].b64_json`; there is no URL to fetch.
"""

import asyncio
import base64
import io
import logging

from openai import AsyncOpenAI
from PIL import Image

from app.config import get_settings
from app.models.generation import GenerationJob, GenerationResult
from app.services import photos
from app.services.ai.imagegen_base import ImageGenerator
from app.services.catalog_service import get_catalog
from app.services.pricing_service import resolve_selections

log = logging.getLogger(__name__)

# The user-facing failure. Provider errors are logged, never surfaced: the
# result screen renders `state.error` verbatim in Russian.
USER_ERROR = "Не удалось сгенерировать изображение. Попробуйте ещё раз."

SIZE_STEP = 16
MIN_EDGE = 256
MAX_ASPECT = 3.0

# The instruction scaffolding is English (image models follow it more reliably),
# while part and option names stay in their catalog Russian — gpt-image-2 is
# multilingual and the labels are what the shop actually sells.
PROMPT_TEMPLATE = (
    "Photorealistic edit of a real photograph of a car. "
    "Replace ONLY the {zone} with the aftermarket part described below. "
    "Keep everything else in the frame exactly as it is: the camera angle, "
    "framing, perspective, lighting, reflections, shadows, colours and every "
    "other part of the car must stay identical to the original photo. "
    "Do not restyle, relight or clean up the rest of the image. "
    "Match the new part's lighting and perspective to the original scene so the "
    "result looks like an unretouched photograph.\n\n"
    "The new part: {part}."
)


def _snap(value: int) -> int:
    """Round to the multiple of 16 the API requires."""
    return max(MIN_EDGE, int(round(value / SIZE_STEP)) * SIZE_STEP)


def _api_size(width: int, height: int, max_edge: int) -> str:
    """Nearest API-legal size preserving the photo's aspect ratio.

    Sending a size that does not match the source would letterbox or crop the
    result, and the before/after slider overlays the two images — any aspect
    drift shows up as the photo jumping under the handle.
    """
    aspect = width / height
    aspect = min(MAX_ASPECT, max(1 / MAX_ASPECT, aspect))
    if aspect >= 1:
        long_edge, short_edge = max_edge, _snap(max_edge / aspect)
    else:
        long_edge, short_edge = max_edge, _snap(max_edge * aspect)

    # Snapping to the grid can round the short edge past the aspect limit
    # (1024/3 = 341.3, which snaps down to 336 — a 3.05:1 the API rejects).
    # Widen it back rather than narrowing the long edge, which would cost detail.
    while long_edge / short_edge > MAX_ASPECT:
        short_edge += SIZE_STEP

    return (
        f"{long_edge}x{short_edge}" if aspect >= 1 else f"{short_edge}x{long_edge}"
    )


def _describe_part(job: GenerationJob) -> str:
    """Product name plus the options the user actually picked.

    Reuses the pricing seam's resolver so the description reflects the same
    merged defaults-plus-selections that the customer is being charged for —
    a preview of a config nobody quoted would be worse than no preview.
    """
    catalog = get_catalog()
    found = catalog.find_product(job.product_id)
    if found is None:
        raise ValueError(f"Unknown product: {job.product_id}")
    category, product = found

    parts = [product.name]
    if product.material:
        parts.append(product.material)

    resolved = resolve_selections(category, product, job.selections)
    for group in category.option_groups:
        choice_id = resolved.get(group.id)
        if choice_id in (None, "off"):
            continue
        choice = group.choice(choice_id)
        if choice is None:
            continue
        if group.type == "toggle":
            parts.append(choice.label)
            continue
        # Leather and stitch choices carry the swatch the UI renders; handing the
        # model the hex pins the colour far better than "Бежевый" alone.
        colour = f" ({choice.hex})" if choice.hex else ""
        parts.append(f"{group.label} — {choice.label}{colour}")

    return ", ".join(parts)


class ProviderImageGenerator(ImageGenerator):
    def __init__(self, api_key: str | None = None) -> None:
        settings = get_settings()
        key = api_key or settings.openai_api_key
        # A bare constructor resolves OPENAI_API_KEY from the environment.
        self._client = (
            AsyncOpenAI(api_key=key, timeout=settings.imagegen_timeout_seconds)
            if key
            else AsyncOpenAI(timeout=settings.imagegen_timeout_seconds)
        )

    async def generate(self, job: GenerationJob) -> GenerationResult:
        settings = get_settings()
        if settings.generation_force_error:
            raise RuntimeError(USER_ERROR)

        raw, media_type = photos.load_bytes(job.source_photo_id)
        source = Image.open(io.BytesIO(raw)).convert("RGB")

        prompt = PROMPT_TEMPLATE.format(
            zone=job.region_label, part=_describe_part(job)
        )

        try:
            response = await self._client.images.edit(
                model=settings.imagegen_model,
                image=(f"{job.source_photo_id}.jpg", raw, media_type),
                prompt=prompt,
                size=_api_size(source.width, source.height, settings.imagegen_max_edge),
                quality=settings.imagegen_quality,
                output_format="jpeg",
                n=1,
            )
            edited = base64.b64decode(response.data[0].b64_json)
        except Exception as exc:  # noqa: BLE001 - every failure is one job failing
            log.exception("gpt-image-2 edit failed for job %s", job.job_id)
            raise RuntimeError(USER_ERROR) from exc

        after = await asyncio.to_thread(self._fit_to_source, edited, source.size)

        _, before_url = photos.save_generated(source, "before")
        after_id, after_url = photos.save_generated(after, "after")
        return GenerationResult(
            before_url=before_url, after_url=after_url, after_photo_id=after_id
        )

    @staticmethod
    def _fit_to_source(
        edited: bytes, size: tuple[int, int]
    ) -> Image.Image:
        """Snapping the aspect to the API grid can shift dimensions by a few
        pixels. Resize back so before/after line up under the slider handle."""
        img = Image.open(io.BytesIO(edited)).convert("RGB")
        if img.size != size:
            img = img.resize(size, Image.LANCZOS)
        return img
