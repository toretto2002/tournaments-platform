"""Entry point FastAPI del servizio identity."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.jwks import router as jwks_router
from app.config import get_settings


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    # Nessuna risorsa da inizializzare/chiudere per ora. Predisposto per gli
    # step successivi (es. warm-up cache chiavi, consumer/producer Kafka).
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.APP_NAME, lifespan=lifespan)
    app.include_router(jwks_router)
    return app


app = create_app()
