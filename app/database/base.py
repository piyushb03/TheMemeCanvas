"""
TheMemeCanvas Automation Suite — Database Engine & Session Factory
==================================================================
SQLAlchemy async-capable setup with SQLite.
All ORM models import from this module.
"""

from __future__ import annotations

import logging
from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from contextlib import contextmanager
from typing import Generator

from app.config.settings import settings

logger = logging.getLogger("thememecanvas.database")

is_sqlite = settings.database_url.startswith("sqlite")

# ---------------------------------------------------------------------------
# Ensure data directory exists (SQLite only)
# ---------------------------------------------------------------------------

if is_sqlite:
    db_path = settings.database_url.replace("sqlite:///", "").replace("./", "")
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------

connect_args = {"check_same_thread": False} if is_sqlite else {}

engine = create_engine(
    settings.database_url,
    connect_args=connect_args,
    echo=False,  # Set to True for SQL query logging during dev
)


if is_sqlite:
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        """Enable WAL mode and foreign keys for SQLite."""
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


# ---------------------------------------------------------------------------
# Session Factory
# ---------------------------------------------------------------------------

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

# ---------------------------------------------------------------------------
# Base class for all ORM models
# ---------------------------------------------------------------------------

Base = declarative_base()


# ---------------------------------------------------------------------------
# Dependency injection helper (for FastAPI routes)
# ---------------------------------------------------------------------------

def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency that yields a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def db_session() -> Generator[Session, None, None]:
    """Context manager for use outside FastAPI (e.g., scheduler jobs)."""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def init_db() -> None:
    """Create all tables if they don't exist."""
    from app.models import upload, queue_item, notification_log  # noqa: F401 — ensure models are registered
    Base.metadata.create_all(bind=engine)
    logger.info("Database initialized successfully.")
