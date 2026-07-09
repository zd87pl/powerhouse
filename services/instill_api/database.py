"""Database session management."""

import os
from pathlib import Path
from typing import Generator

from sqlalchemy.orm import Session

from .models import get_engine, init_db

# Anchor the default SQLite file to the repo root so it doesn't depend on the
# process working directory (which would silently create a second database).
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{_REPO_ROOT / 'instill.db'}")
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
