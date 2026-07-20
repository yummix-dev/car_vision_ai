import asyncio

from app.models.vehicle import VehicleGuess
from app.services.ai.vehicle_base import VehicleRecognizer

# Matches the prototype's 1700ms analyzing spinner so the UI timing is honest.
MOCK_LATENCY_SECONDS = 1.7


class MockVehicleRecognizer(VehicleRecognizer):
    async def recognize(self, image_bytes: bytes, media_type: str) -> VehicleGuess:
        await asyncio.sleep(MOCK_LATENCY_SECONDS)
        return VehicleGuess(
            make="Chevrolet", model="Malibu", year=2023, confidence=0.9
        )
