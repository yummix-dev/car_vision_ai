"""Balance and ledger, read-only.

Nothing here accepts an amount from the client: every grant and spend is decided
on the server (§22 of the spec, and the only sane way to run a balance).
"""

import logging

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field

from app.i18n import lang_of, t
from app.routers.deps import current_user
from app.services import notifications, quota, reward_codes

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["quota"])


@router.get("/generation-balance")
def read_balance(
    category_id: str | None = None,
    user: dict | None = Depends(current_user),
) -> dict:
    if user is None:
        return quota.unmetered_snapshot(category_id)
    return quota.snapshot(user["id"], category_id)


@router.get("/generation-transactions")
def read_history(user: dict | None = Depends(current_user)) -> list[dict]:
    if user is None:
        return []
    return quota.history(user["id"])


class ActivateRequest(BaseModel):
    # Only the code. The amount it is worth is decided by the server — a client
    # that could name its own reward would not be a quota at all.
    code: str = Field(min_length=1, max_length=64)


@router.post("/reward-codes/activate")
def activate_code(
    req: ActivateRequest,
    user: dict | None = Depends(current_user),
    x_lang: str | None = Header(default=None),
) -> dict:
    if user is None:
        raise HTTPException(
            status_code=401, detail=t("err.no_telegram", lang_of(x_lang))
        )
    try:
        result = reward_codes.activate(user["id"], req.code)
    except reward_codes.CodeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001 - never leak internals to a customer
        log.exception("code activation failed for user %s", user["id"])
        raise HTTPException(
            status_code=500, detail=reward_codes.GENERIC
        ) from exc

    notifications.code_activated(
        user["id"], result["bonus_amount"], result["restored_free"]
    )
    if result.get("referred_client"):
        notifications.referred_client_rewarded(
            result["referred_client"]["inviter_id"],
            result["referred_client"]["amount"],
        )
    return result
