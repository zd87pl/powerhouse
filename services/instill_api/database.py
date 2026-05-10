"""Database session management."""

import os
from typing import Generator

from sqlalchemy.orm import Session

from .models import get_engine, init_db

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///instill.db")
_engine = None


def get_session() -> Generator[Session, None, None]:
    """FastAPI dependency: yields a database session."""
    global _engine
    if _engine is None:
        _engine = get_engine(DATABASE_URL)
        init_db(DATABASE_URL)
    session = Session(_engine)
    try:
        yield session
    finally:
        session.close()
