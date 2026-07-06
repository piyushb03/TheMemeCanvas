"""
Test configuration and fixtures for TheMemeCanvas test suite.
"""
import pytest
import tempfile
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


@pytest.fixture(scope="function")
def test_db():
    """Create an in-memory SQLite database for testing."""
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})

    from app.database.base import Base
    from app.models import Upload, QueueItem, NotificationLog  # Register models
    Base.metadata.create_all(bind=engine)

    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()

    yield session

    session.close()
    engine.dispose()


@pytest.fixture(scope="function")
def temp_video():
    """Create a temporary fake video file for testing."""
    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as f:
        f.write(b"FAKE_VIDEO_CONTENT_FOR_TESTING" * 100)
        path = Path(f.name)

    yield path

    if path.exists():
        path.unlink()
