from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

from db.database import Base, Note, SessionLocal, Task, engine, init_db


@contextmanager
def get_session() -> Iterator:
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


__all__ = [
    "Base",
    "Task",
    "Note",
    "engine",
    "SessionLocal",
    "init_db",
    "get_session",
]
