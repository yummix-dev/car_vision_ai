import asyncio
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.config import BASE_DIR, get_settings
from app.routers import (
    admin,
    cart,
    catalog,
    config,
    events,
    generation,
    photos,
    pricing,
    quota,
    referral,
    vehicle,
)
from app.services import cleanup
from app.services import photos as photo_service
from app.services.catalog_service import get_catalog

WEB_DIR = BASE_DIR / "web"


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Fail fast on a bad catalog rather than at checkout, and make sure the demo
    # funnel has an image to work with.
    get_catalog()
    photo_service.ensure_demo_photo()

    sweeper = asyncio.create_task(cleanup.run_forever())
    try:
        yield
    finally:
        sweeper.cancel()


def create_app() -> FastAPI:
    app = FastAPI(title="MyCar Vision AI", lifespan=lifespan)

    app.include_router(config.router)
    app.include_router(catalog.router)
    app.include_router(events.router)
    app.include_router(quota.router)
    app.include_router(referral.router)
    # An unset ADMIN_PASSWORD means the page does not exist, not that it is
    # open: the default deployment must not publish the shop's numbers.
    if get_settings().admin_password:
        app.include_router(admin.router)
    app.include_router(photos.router)
    app.include_router(vehicle.router)
    app.include_router(pricing.router)
    app.include_router(generation.router)
    app.include_router(cart.router)

    settings = get_settings()
    app.mount("/media", StaticFiles(directory=settings.media_path), name="media")
    app.mount("/", StaticFiles(directory=WEB_DIR, html=True), name="web")
    return app


app = create_app()
