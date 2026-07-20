"""Seam 1, real implementation: Claude vision.

Swap in by setting AI_PROVIDER=claude. No call site changes.

Notes on the API shape (these are load-bearing):
  * The image content block must come BEFORE the text block.
  * `messages.parse(output_format=...)` returns a validated model on `.parsed_output`.
  * `temperature` / `top_p` / `budget_tokens` are rejected with a 400 on this model —
    use `thinking={"type": "adaptive"}` instead of a thinking budget.
"""

import base64

import anthropic

from app.models.vehicle import VehicleGuess
from app.services.ai.vehicle_base import VehicleRecognizer

MODEL = "claude-opus-4-8"

PROMPT = (
    "На фотографии — фрагмент автомобиля (салон или кузов). "
    "Определи марку, модель и примерный год выпуска автомобиля. "
    "Учитывай, что это рынок Узбекистана: чаще всего встречаются "
    "Chevrolet Cobalt, Chevrolet Malibu, Ravon Nexia, Daewoo Gentra. "
    "Если уверенности мало, всё равно назови наиболее вероятный вариант "
    "и поставь низкое значение confidence."
)


class ClaudeVehicleRecognizer(VehicleRecognizer):
    def __init__(self, api_key: str | None = None) -> None:
        # A bare constructor resolves ANTHROPIC_API_KEY or an `ant auth login`
        # profile from the environment.
        self._client = (
            anthropic.AsyncAnthropic(api_key=api_key)
            if api_key
            else anthropic.AsyncAnthropic()
        )

    async def recognize(self, image_bytes: bytes, media_type: str) -> VehicleGuess:
        b64 = base64.standard_b64encode(image_bytes).decode("utf-8")
        response = await self._client.messages.parse(
            model=MODEL,
            max_tokens=1024,
            thinking={"type": "adaptive"},
            output_format=VehicleGuess,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": media_type,
                                "data": b64,
                            },
                        },
                        {"type": "text", "text": PROMPT},
                    ],
                }
            ],
        )
        return response.parsed_output
