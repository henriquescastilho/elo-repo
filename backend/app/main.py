from fastapi import FastAPI

from backend.app.core import logging  # noqa: F401 ensures logging config is applied
from backend.app.config import get_settings
from backend.app.routes import debug, health, whatsapp_webhook, telegram_webhook
import sentry_sdk

settings = get_settings()
if settings.sentry_dsn:
    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        traces_sample_rate=1.0,
        profiles_sample_rate=1.0,
    )

app = FastAPI(title="ELO Assistente Cidadão", version="0.1.0")

from fastapi.staticfiles import StaticFiles
import os

app.include_router(health.router)
app.include_router(whatsapp_webhook.router)
app.include_router(telegram_webhook.router)
app.include_router(debug.router)

# Mount media directory for static access (TTS, etc)
media_path = os.path.join(os.getcwd(), "media")
os.makedirs(media_path, exist_ok=True)
app.mount("/media", StaticFiles(directory=media_path), name="media")
