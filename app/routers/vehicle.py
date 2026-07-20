from fastapi import APIRouter, Depends, HTTPException

from app.models.vehicle import CarCorrection, RecognizeRequest, VehicleResponse
from app.routers.deps import current_user
from app.services import photos, users
from app.services.ai import get_vehicle_recognizer
from app.services.compatibility import car_label, compatible_categories

router = APIRouter(prefix="/api/vehicle", tags=["vehicle"])


@router.post("/recognize")
async def recognize(req: RecognizeRequest) -> VehicleResponse:
    try:
        image_bytes, media_type = photos.load_bytes(req.photo_id)
    except photos.PhotoError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    try:
        guess = await get_vehicle_recognizer().recognize(image_bytes, media_type)
    except Exception as exc:  # noqa: BLE001 - surface provider failures as 502
        raise HTTPException(
            status_code=502, detail="Не удалось распознать автомобиль"
        ) from exc

    return VehicleResponse(
        make=guess.make,
        model=guess.model,
        year=guess.year,
        confidence=guess.confidence,
        label=car_label(guess.make, guess.model, guess.year),
        compatible_categories=compatible_categories(
            guess.make, guess.model, guess.year
        ),
    )


@router.post("/confirm")
def confirm(
    req: CarCorrection, user: dict | None = Depends(current_user)
) -> VehicleResponse:
    """Accepting the recognised car. Recording it is what makes a referral
    qualify later — an invited person must have a car of their own, not just
    a click."""
    if user is not None:
        users.confirm_car(user["id"], req.make, req.model, req.year)
    return VehicleResponse(
        make=req.make,
        model=req.model,
        year=req.year,
        confidence=1.0,
        label=car_label(req.make, req.model, req.year),
        compatible_categories=compatible_categories(req.make, req.model, req.year),
    )


@router.post("/correct")
def correct(
    req: CarCorrection, user: dict | None = Depends(current_user)
) -> VehicleResponse:
    """Manual chip-editor path. Never calls the model — this is the recovery route
    for when recognition gets it wrong, and it must always stay available."""
    if user is not None:
        users.confirm_car(user["id"], req.make, req.model, req.year)
    return VehicleResponse(
        make=req.make,
        model=req.model,
        year=req.year,
        confidence=1.0,
        label=car_label(req.make, req.model, req.year),
        compatible_categories=compatible_categories(req.make, req.model, req.year),
    )
