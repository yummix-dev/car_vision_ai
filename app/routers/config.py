from fastapi import APIRouter
from pydantic import BaseModel

from app.config import get_settings

router = APIRouter(prefix="/api", tags=["config"])


class ClientConfig(BaseModel):
    """Settings the SPA needs. Public values only — no token ever leaves here."""

    telegram_bot_username: str = ""


@router.get("/config")
def read_config() -> ClientConfig:
    return ClientConfig(telegram_bot_username=get_settings().telegram_bot_username)
