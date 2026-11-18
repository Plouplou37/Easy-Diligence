"""Engine and sessions.

Transactions are real: nothing is written until the session commits, and a
rollback undoes everything since the last commit. (The MySQL era forced
autocommit at the driver level, so every statement was kept at once and
rollbacks did nothing.)

The schema is not created here: Alembic owns it (`uv run alembic upgrade head`).
"""

from collections.abc import Iterator
from typing import Any

from sqlalchemy import create_engine
from sqlalchemy.engine import URL, make_url
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings


def _engine_options(url: URL) -> dict[str, Any]:
    if url.get_backend_name() == "sqlite":  # the test suite
        return {"connect_args": {"check_same_thread": False}}
    return {
        "pool_size": 10,
        "max_overflow": 20,
        "pool_pre_ping": True,  # check a pooled connection before using it
        "pool_recycle": 3600,  # renew connections after an hour
        "connect_args": {"connect_timeout": 10},
    }


_url = make_url(settings.sqlalchemy_database_url)
engine = create_engine(_url, echo=settings.debug, **_engine_options(_url))

SessionLocal = sessionmaker(bind=engine, autoflush=False)


def get_db() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
