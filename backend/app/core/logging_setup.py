"""Logging of the application.

Without this, the `logger.info(...)` calls of the application went nowhere
under uvicorn, which only configures its own loggers. One console handler on
the root logger: the application's loggers (`app.*`) write from LOG_LEVEL up,
third-party libraries from WARNING up. Uvicorn's loggers keep their own
handlers and do not propagate, so nothing is written twice.

No personal data in the logs: identify a user by their id, never by their
e-mail address or name.
"""

import logging.config


def configure_logging(level: str) -> None:
    logging.config.dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "default": {"format": "%(asctime)s %(levelname)-8s %(name)s: %(message)s"},
            },
            "handlers": {
                "console": {"class": "logging.StreamHandler", "formatter": "default"},
            },
            "root": {"level": "WARNING", "handlers": ["console"]},
            "loggers": {"app": {"level": level}},
        }
    )
