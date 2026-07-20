"""Event ingestion.

Deliberately open: events are needed in a plain browser and before any Telegram
login, so there is no initData requirement here. That makes this the one
unauthenticated write path in the app, which is why every field is bounded and
the event name must come from a closed vocabulary.
"""

import time

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.models.telegram import TelegramUser
from app.routers.deps import telegram_user
from app.services import analytics

router = APIRouter(prefix="/api", tags=["analytics"])

# Per-session ceiling. Without it this endpoint is an open write into the shop's
# database; a real session emits a couple of events per screen.
RATE_WINDOW_SECONDS = 60
RATE_MAX_EVENTS = 120
_recent: dict[str, list[float]] = {}


class EventIn(BaseModel):
    name: str
    screen: str | None = None
    category_id: str | None = None
    product_id: str | None = None
    payload: dict | None = None


class EventBatch(BaseModel):
    session_id: str = Field(min_length=1, max_length=64)
    events: list[EventIn] = Field(min_length=1, max_length=analytics.MAX_BATCH)


class EventResponse(BaseModel):
    stored: int


def _rate_limited(session_id: str, count: int) -> bool:
    now = time.monotonic()
    seen = [t for t in _recent.get(session_id, []) if now - t < RATE_WINDOW_SECONDS]
    if len(seen) + count > RATE_MAX_EVENTS:
        _recent[session_id] = seen
        return True
    seen.extend([now] * count)
    _recent[session_id] = seen
    return False


@router.post("/events")
async def ingest(
    batch: EventBatch,
    user: TelegramUser | None = Depends(telegram_user),
) -> EventResponse:
    for event in batch.events:
        if event.name not in analytics.EVENT_NAMES:
            raise HTTPException(status_code=400, detail=f"Unknown event: {event.name}")
        if (
            event.payload is not None
            and len(str(event.payload)) > analytics.MAX_PAYLOAD_CHARS
        ):
            raise HTTPException(status_code=400, detail="Payload too large")

    if _rate_limited(batch.session_id, len(batch.events)):
        raise HTTPException(status_code=429, detail="Too many events")

    stored = await analytics.record(
        [{"session_id": batch.session_id, **e.model_dump()} for e in batch.events],
        user_id=user.id if user else None,
    )
    return EventResponse(stored=stored)
