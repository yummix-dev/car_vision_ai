"""Both mocks must satisfy their ABCs and return the declared types, so any real
implementation matching the same interface is genuinely drop-in."""

import base64
import inspect
import io
from types import SimpleNamespace

import pytest
from PIL import Image

from app.models.generation import GenerationJob, GenerationResult
from app.models.pricing import Selection
from app.models.vehicle import VehicleGuess
from app.services.ai.imagegen_base import ImageGenerator
from app.services.ai.imagegen_mock import MockImageGenerator
from app.services.ai.imagegen_provider import (
    USER_ERROR,
    ProviderImageGenerator,
    _api_size,
)
from app.services.ai.vehicle_base import VehicleRecognizer
from app.services.ai.vehicle_claude import ClaudeVehicleRecognizer
from app.services.ai.vehicle_mock import MockVehicleRecognizer
from app.services import photos


def test_implementations_register_against_their_abc():
    from app.services.ai.vehicle_openai import OpenAIVehicleRecognizer

    assert issubclass(MockVehicleRecognizer, VehicleRecognizer)
    assert issubclass(ClaudeVehicleRecognizer, VehicleRecognizer)
    assert issubclass(OpenAIVehicleRecognizer, VehicleRecognizer)
    assert issubclass(MockImageGenerator, ImageGenerator)
    assert issubclass(ProviderImageGenerator, ImageGenerator)


def test_real_and_mock_share_identical_signatures():
    """A drifting signature would break the one-file swap."""
    from app.services.ai.vehicle_openai import OpenAIVehicleRecognizer

    assert inspect.signature(
        MockVehicleRecognizer.recognize
    ) == inspect.signature(ClaudeVehicleRecognizer.recognize)
    assert inspect.signature(
        MockVehicleRecognizer.recognize
    ) == inspect.signature(OpenAIVehicleRecognizer.recognize)
    assert inspect.signature(
        MockImageGenerator.generate
    ) == inspect.signature(ProviderImageGenerator.generate)


@pytest.mark.asyncio
async def test_mock_recognizer_returns_vehicle_guess():
    guess = await MockVehicleRecognizer().recognize(b"", "image/jpeg")
    assert isinstance(guess, VehicleGuess)
    assert guess.make and guess.model and guess.year > 1900
    assert 0.0 <= guess.confidence <= 1.0


@pytest.mark.asyncio
async def test_mock_generator_returns_two_distinct_images():
    demo = photos.ensure_demo_photo()
    job = GenerationJob(
        job_id="t",
        source_photo_id=demo["photo_id"],
        product_id="amg",
        category_id="rul",
        region_label="руль",
    )
    res = await MockImageGenerator().generate(job)
    assert isinstance(res, GenerationResult)
    assert res.before_url != res.after_url
    assert res.before_url.startswith("/media/")
    assert res.after_url.startswith("/media/")


def _rul_job(**overrides) -> GenerationJob:
    demo = photos.ensure_demo_photo()
    return GenerationJob(
        **{
            "job_id": "t",
            "source_photo_id": demo["photo_id"],
            "product_id": "amg",
            "category_id": "rul",
            "region_label": "руль",
            **overrides,
        }
    )


class _FakeEdits:
    """Stands in for client.images. Records the call, replays a canned image."""

    def __init__(self, reply: bytes | Exception):
        self._reply = reply
        self.calls: list[dict] = []

    async def edit(self, **kwargs):
        self.calls.append(kwargs)
        if isinstance(self._reply, Exception):
            raise self._reply
        return SimpleNamespace(
            data=[SimpleNamespace(b64_json=base64.b64encode(self._reply).decode())]
        )


def _stub_provider(reply: bytes | Exception) -> tuple[ProviderImageGenerator, _FakeEdits]:
    gen = ProviderImageGenerator(api_key="test-key")
    edits = _FakeEdits(reply)
    gen._client = SimpleNamespace(images=edits)
    return gen, edits


def _jpeg(size: tuple[int, int]) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", size, "#334455").save(buf, "JPEG")
    return buf.getvalue()


@pytest.mark.parametrize(
    "width,height,max_edge",
    [
        (1024, 1024, 1024),   # square
        (1200, 900, 1024),    # 4:3 landscape
        (900, 1200, 1024),    # portrait
        (4000, 1000, 1024),   # 4:1, clamps to the 3:1 API limit
        (3000, 1000, 1024),   # exactly 3:1
        (1920, 1080, 1024),   # 16:9, the shape a phone shoots in landscape
    ],
)
def test_api_size_is_always_acceptable_to_the_api(width, height, max_edge):
    """Every constraint the API enforces, checked together: multiples of 16,
    aspect within 3:1, no edge over 3840, and — the one that bit us — above the
    minimum pixel budget, which a wide photo at a 1024 long edge falls under."""
    size = _api_size(width, height, max_edge)
    w, h = (int(v) for v in size.split("x"))

    assert w % 16 == 0 and h % 16 == 0, f"{size} is off the 16px grid"
    assert max(w / h, h / w) <= 3.0, f"{size} exceeds the 3:1 limit"
    assert max(w, h) <= 3840, f"{size} exceeds the 3840 ceiling"
    assert w * h >= 800_000, f"{size} is below the minimum pixel budget"


def test_a_wide_photo_grows_instead_of_being_rejected():
    """1024x352 is what the old code produced for a panoramic shot — and the
    API answers "below the current minimum pixel budget" with a 400."""
    size = _api_size(4000, 1000, 1024)
    w, h = (int(v) for v in size.split("x"))

    assert w * h >= 800_000
    assert max(w, h) > 1024, "the frame had to grow past the requested long edge"


def test_the_aspect_ratio_is_preserved_while_growing():
    size = _api_size(1920, 1080, 1024)
    w, h = (int(v) for v in size.split("x"))
    assert abs((w / h) - (1920 / 1080)) < 0.05, f"{size} distorts 16:9"


@pytest.mark.asyncio
async def test_provider_returns_two_urls_and_preserves_source_dimensions():
    job = _rul_job()
    source = Image.open(io.BytesIO(photos.load_bytes(job.source_photo_id)[0]))
    # Reply at a deliberately different size: the result must be fitted back,
    # or the before/after slider overlays two mismatched images.
    gen, _ = _stub_provider(_jpeg((512, 384)))

    res = await gen.generate(job)

    assert isinstance(res, GenerationResult)
    assert res.before_url.startswith("/media/")
    assert res.after_url.startswith("/media/")
    assert res.before_url != res.after_url

    after_id = res.after_url.removeprefix("/media/").removesuffix(".jpg")
    assert Image.open(io.BytesIO(photos.load_bytes(after_id)[0])).size == source.size


@pytest.mark.asyncio
async def test_provider_prompt_carries_the_zone_and_the_resolved_config():
    """The preview must depict the config the customer is being quoted for."""
    gen, edits = _stub_provider(_jpeg((256, 256)))

    await gen.generate(_rul_job(selections=[Selection(group_id="leather", choice_id="beige")]))

    prompt = edits.calls[0]["prompt"]
    assert "руль" in prompt                 # the zone, from region_label
    assert "AMG Carbon LED" in prompt       # the product
    assert "Бежевый" in prompt              # the explicit selection
    assert "#c9b79c" in prompt              # its swatch, for colour accuracy
    assert "Красная" in prompt              # a default that was never overridden


@pytest.mark.asyncio
async def test_provider_omits_input_fidelity():
    """gpt-image-2 rejects the parameter outright — sending it 400s every job."""
    gen, edits = _stub_provider(_jpeg((256, 256)))
    await gen.generate(_rul_job())
    assert "input_fidelity" not in edits.calls[0]


@pytest.mark.asyncio
async def test_provider_failure_surfaces_the_russian_message_not_the_raw_error():
    """`state.error` is rendered verbatim on the result screen."""
    gen, _ = _stub_provider(RuntimeError("429 rate_limit_exceeded org-xyz"))

    with pytest.raises(RuntimeError) as exc:
        await gen.generate(_rul_job())

    assert str(exc.value) == USER_ERROR
    assert "rate_limit" not in str(exc.value)
