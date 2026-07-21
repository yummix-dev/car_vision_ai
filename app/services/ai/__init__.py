"""Provider selection for the two AI seams.

Swapping either seam to a real implementation is an env change. No call site
edits. The image seam stays named `provider` rather than `openai` on purpose —
the vendor behind it is an implementation detail of one file.
"""

from functools import lru_cache

from app.config import get_settings
from app.services.ai.imagegen_base import ImageGenerator
from app.services.ai.imagegen_mock import MockImageGenerator
from app.services.ai.vehicle_base import VehicleRecognizer
from app.services.ai.vehicle_mock import MockVehicleRecognizer


@lru_cache
def get_vehicle_recognizer() -> VehicleRecognizer:
    provider = get_settings().ai_provider.lower()
    if provider == "openai":
        # Reuses OPENAI_API_KEY — the same vendor as the image seam.
        from app.services.ai.vehicle_openai import OpenAIVehicleRecognizer

        return OpenAIVehicleRecognizer(get_settings().openai_api_key)
    if provider == "claude":
        # Imported lazily so the app runs without the anthropic SDK configured.
        from app.services.ai.vehicle_claude import ClaudeVehicleRecognizer

        return ClaudeVehicleRecognizer(get_settings().anthropic_api_key)
    if provider == "mock":
        return MockVehicleRecognizer()
    raise ValueError(
        f"Unknown AI_PROVIDER: {provider!r} (expected 'mock', 'openai' or 'claude')"
    )


@lru_cache
def get_image_generator() -> ImageGenerator:
    provider = get_settings().imagegen_provider.lower()
    if provider == "mock":
        return MockImageGenerator()
    if provider == "provider":
        # Imported lazily so the app runs without the openai SDK configured.
        from app.services.ai.imagegen_provider import ProviderImageGenerator

        return ProviderImageGenerator()
    raise ValueError(
        f"Unknown IMAGEGEN_PROVIDER: {provider!r} (expected 'mock' or 'provider')"
    )
