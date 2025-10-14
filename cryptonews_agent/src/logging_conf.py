from __future__ import annotations

import logging
from logging.config import dictConfig


LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json": {
            "()": "pythonjsonlogger.jsonlogger.JsonFormatter",
            "fmt": "%(asctime)s %(name)s %(levelname)s %(message)s",
        }
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "json",
            "level": "INFO",
        }
    },
    "root": {"level": "INFO", "handlers": ["console"]},
}


def configure_logging() -> None:
    dictConfig(LOGGING_CONFIG)
    logging.getLogger(__name__).debug("Logging configured", extra={"component": "logging"})
