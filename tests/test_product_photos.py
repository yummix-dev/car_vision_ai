"""Product reference photos: validation, and how they reach the image model."""

import io

import pytest
from PIL import Image

from app.config import get_settings
from app.models.generation import GenerationJob
from app.services import catalog_service, photos
from app.services.ai.imagegen_provider import (
    PROMPT_TEMPLATE,
    PROMPT_WITH_REFERENCE,
    ProviderImageGenerator,
)
from app.services.catalog_service import CatalogError, load_catalog

from tests.test_ai_seams import _FakeEdits, _jpeg


@pytest.fixture
def catalog_file(tmp_path, monkeypatch):
    """A copy of the catalog with every photo stripped, so a test starts from a
    known 'no photos' baseline and adds back only what it means to test.

    Without stripping, the real catalog's own photo: lines point at files that
    do not exist in this temp dir, and validation fails before the test runs.
    """
    lines = catalog_service.CATALOG_PATH.read_text(encoding="utf-8").splitlines(
        keepends=True
    )
    stripped = [ln for ln in lines if not ln.lstrip().startswith("photo:")]

    path = tmp_path / "catalog.yaml"
    path.write_text("".join(stripped), encoding="utf-8")
    monkeypatch.setattr(catalog_service, "PRODUCT_IMAGE_DIR", tmp_path / "products")
    monkeypatch.setattr(catalog_service, "CATEGORY_IMAGE_DIR", tmp_path / "products")
    (tmp_path / "products").mkdir()
    return path


def _write_photo(tmp_path, name="amg.jpg", size=(400, 400)):
    path = tmp_path / "products" / name
    Image.new("RGB", size, "#334455").save(path, "JPEG")
    return path


def _add_photo_to_catalog(path, product_id="amg", filename="amg.jpg"):
    text = path.read_text(encoding="utf-8")
    text = text.replace(
        f"      - id: {product_id}\n",
        f"      - id: {product_id}\n        photo: {filename}\n",
        1,
    )
    path.write_text(text, encoding="utf-8")


# ── validation ────────────────────────────────────────────────


def test_a_catalog_without_photos_still_loads(catalog_file):
    catalog = load_catalog(catalog_file)
    assert catalog.find_product("amg")[1].photo is None


def test_a_named_photo_that_exists_loads(catalog_file, tmp_path):
    _write_photo(tmp_path)
    _add_photo_to_catalog(catalog_file)

    catalog = load_catalog(catalog_file)
    assert catalog.find_product("amg")[1].photo == "amg.jpg"


def test_a_missing_photo_fails_at_startup(catalog_file):
    """Silently falling back would let the shop believe customers see a real
    part while the model quietly invents one."""
    _add_photo_to_catalog(catalog_file, filename="not-there.jpg")

    with pytest.raises(CatalogError, match="not found"):
        load_catalog(catalog_file)


# ── how it reaches the model ──────────────────────────────────


def _job() -> GenerationJob:
    demo = photos.ensure_demo_photo()
    return GenerationJob(
        job_id="t",
        source_photo_id=demo["photo_id"],
        product_id="amg",
        category_id="rul",
        region_label="руль",
    )


def _stub(monkeypatch, reply):
    gen = ProviderImageGenerator(api_key="test-key")
    edits = _FakeEdits(reply)
    gen._client = type("C", (), {"images": edits})()
    return gen, edits


@pytest.mark.asyncio
async def test_without_a_photo_one_image_and_the_plain_prompt(monkeypatch):
    monkeypatch.setattr(get_settings(), "quota_enabled", False)
    # amg ships with a placeholder photo now; clear it to exercise the no-photo
    # branch explicitly rather than depend on the catalog's current contents.
    product = catalog_service.get_catalog().find_product("amg")[1]
    monkeypatch.setattr(product, "photo", None)

    gen, edits = _stub(monkeypatch, _jpeg((256, 256)))

    await gen.generate(_job())
    call = edits.calls[0]

    assert isinstance(call["image"], tuple), "a single image, not a list"
    assert call["prompt"].startswith(PROMPT_TEMPLATE[:40])


@pytest.mark.asyncio
async def test_with_a_photo_the_customer_photo_goes_first(monkeypatch, tmp_path):
    """Order is load-bearing: the first image is the one being edited, and a
    mask — if one is ever added — applies to the first."""
    monkeypatch.setattr(catalog_service, "PRODUCT_IMAGE_DIR", tmp_path)
    Image.new("RGB", (400, 400), "#993322").save(tmp_path / "amg.jpg", "JPEG")

    catalog = catalog_service.get_catalog()
    product = catalog.find_product("amg")[1]
    monkeypatch.setattr(product, "photo", "amg.jpg")

    gen, edits = _stub(monkeypatch, _jpeg((256, 256)))
    job = _job()
    await gen.generate(job)
    call = edits.calls[0]

    assert isinstance(call["image"], list) and len(call["image"]) == 2
    assert call["image"][0][0].startswith(job.source_photo_id), "customer photo first"
    assert call["image"][1][0] == "amg.jpg", "reference second"

    # The prompt has to say what the second image is for, or the model treats
    # it as loose inspiration.
    assert "SECOND image" in call["prompt"]
    assert PROMPT_WITH_REFERENCE[:40] in call["prompt"]


@pytest.mark.asyncio
async def test_an_unreadable_photo_falls_back_instead_of_failing(monkeypatch, tmp_path):
    """A renamed file must not deny a waiting customer their render."""
    monkeypatch.setattr(catalog_service, "PRODUCT_IMAGE_DIR", tmp_path)
    product = catalog_service.get_catalog().find_product("amg")[1]
    monkeypatch.setattr(product, "photo", "vanished.jpg")

    gen, edits = _stub(monkeypatch, _jpeg((256, 256)))
    await gen.generate(_job())

    call = edits.calls[0]
    assert isinstance(call["image"], tuple), "fell back to one image"
    assert "SECOND image" not in call["prompt"]
