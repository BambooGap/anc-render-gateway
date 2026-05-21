from __future__ import annotations

import os
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from anc_gateway.storage.models import Base

DEFAULT_DB_PATH = Path(".anc_gateway") / "anc_gateway.db"


def get_database_url() -> str:
    return os.environ.get("ANC_GATEWAY_DB_URL", f"sqlite:///{DEFAULT_DB_PATH}")


def create_engine_from_url(database_url: str) -> Engine:
    if database_url.startswith("sqlite:///"):
        db_path = database_url.removeprefix("sqlite:///")
        if db_path and db_path != ":memory:":
            Path(db_path).expanduser().parent.mkdir(parents=True, exist_ok=True)

    connect_args = {"check_same_thread": False} if database_url.startswith("sqlite") else {}
    return create_engine(database_url, connect_args=connect_args)


def init_db(engine: Engine) -> None:
    Base.metadata.create_all(engine)


@contextmanager
def get_session(database_url: str | None = None) -> Iterator[Session]:
    engine = create_engine_from_url(database_url or get_database_url())
    init_db(engine)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    session = session_factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
