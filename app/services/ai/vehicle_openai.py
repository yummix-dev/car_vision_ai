"""Seam 1, OpenAI implementation: vehicle recognition by a vision chat model.

Swap in with AI_PROVIDER=openai. Reuses the same OPENAI_API_KEY the image seam
uses — no second vendor. gpt-image-2 cannot do this; it generates images, it does
not read them. Recognition needs a multimodal chat model (gpt-4o-mini by
default, configurable).

Notes:
  * The image goes as a data URI in an image_url content block.
  * response_format=json_object forces a parseable object; the prompt pins the
    exact keys, and pydantic rejects anything off-shape so a bad answer fails
    loudly rather than becoming a wrong guess.
"""

import base64
import json

from openai import AsyncOpenAI

from app.config import get_settings
from app.models.vehicle import VehicleGuess
from app.services.ai.vehicle_base import VehicleRecognizer

PROMPT = (
    "На фото — фрагмент автомобиля (салон или кузов). Определи марку, модель и "
    "примерный год выпуска. Рынок Узбекистана: чаще всего Chevrolet Cobalt, "
    "Chevrolet Malibu, Ravon Nexia, Daewoo Gentra. Если уверенности мало, всё "
    "равно назови наиболее вероятный вариант и поставь низкое значение "
    "confidence.\n\n"
    'Ответь строго JSON-объектом с ключами: "make" (строка), "model" (строка), '
    '"year" (целое число), "confidence" (число от 0 до 1). Без пояснений.'
)


class OpenAIVehicleRecognizer(VehicleRecognizer):
    def __init__(self, api_key: str | None = None) -> None:
        settings = get_settings()
        key = api_key or settings.openai_api_key
        self._client = (
            AsyncOpenAI(api_key=key) if key else AsyncOpenAI()
        )
        self._model = settings.vehicle_recognition_model

    async def recognize(self, image_bytes: bytes, media_type: str) -> VehicleGuess:
        b64 = base64.standard_b64encode(image_bytes).decode("utf-8")
        data_uri = f"data:{media_type};base64,{b64}"

        response = await self._client.chat.completions.create(
            model=self._model,
            max_tokens=300,
            response_format={"type": "json_object"},
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": PROMPT},
                        {"type": "image_url", "image_url": {"url": data_uri}},
                    ],
                }
            ],
        )
        raw = response.choices[0].message.content or "{}"
        return VehicleGuess.model_validate(json.loads(raw))
