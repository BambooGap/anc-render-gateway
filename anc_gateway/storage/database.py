from __future__ import annotations

import os
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from sqlalchemy import Engine, create_engine, text
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
    if engine.url.get_backend_name() == "sqlite":
        _ensure_sqlite_columns(engine)


def _ensure_sqlite_columns(engine: Engine) -> None:
    with engine.begin() as connection:
        case_columns = {
            row[1]
            for row in connection.execute(text("PRAGMA table_info(cases)")).fetchall()
        }
        if case_columns and "status" not in case_columns:
            connection.execute(
                text("ALTER TABLE cases ADD COLUMN status VARCHAR(64) DEFAULT 'ACTIVE'")
            )


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
