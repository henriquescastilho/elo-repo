import logging
from typing import Dict

from backend.app.config import get_settings

_configured = False
_loggers: Dict[str, logging.Logger] = {}


def configure_logging() -> None:
    global _configured
    if _configured:
        return
    settings = get_settings()
    level = getattr(logging, settings.log_level.upper(), logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    _configured = True


def get_logger(name: str) -> logging.Logger:
    if name in _loggers:
        return _loggers[name]
    configure_logging()
    logger = logging.getLogger(name)
    _loggers[name] = logger
    return logger


configure_logging()
