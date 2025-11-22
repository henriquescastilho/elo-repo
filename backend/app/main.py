from fastapi import FastAPI

from backend.app.core import logging  # noqa: F401 ensures logging config is applied
from backend.app.routes import debug, health, whatsapp_webhook

app = FastAPI(title="ELO Assistente Cidadão", version="0.1.0")

app.include_router(health.router)
app.include_router(whatsapp_webhook.router)
app.include_router(debug.router)
