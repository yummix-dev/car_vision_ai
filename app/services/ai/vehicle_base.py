from abc import ABC, abstractmethod

from app.models.vehicle import VehicleGuess


class VehicleRecognizer(ABC):
    """Seam 1: photo -> vehicle identity.

    Real implementations are latent and fallible. The manual chip-editor
    correction path in the UI is the recovery route and must always stay wired.
    """

    @abstractmethod
    async def recognize(self, image_bytes: bytes, media_type: str) -> VehicleGuess:
        ...
