"""
Pytest configuration and shared fixtures for STT App API tests.
"""
import os
import sys
import asyncio
import tempfile
from pathlib import Path
from typing import AsyncGenerator, Generator
from uuid import uuid4

import pytest
try:
    from pytest_asyncio import is_async_test
except ImportError:
    # pytest-asyncio >= 0.17 doesn't have is_async_test
    def is_async_test(obj, name):
        return asyncio.iscoroutinefunction(getattr(obj, name, None))
from httpx import AsyncClient, ASGITransport
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.main import app
from app.database import Base, get_db, Transcript, TranscriptStatus, Summary, RAGSession, RAGMessage, ProcessingJob, JobType, JobStatus


# Test database URL (use SQLite for tests)
TEST_DATABASE_URL = "sqlite:///./test.db"


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    if sys.platform == "win32" and sys.version_info >= (3, 8):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="function")
def db_engine():
    """Create a test database engine."""
    engine = create_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False}  # Needed for SQLite
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)
    # Clean up test database file
    if os.path.exists("./test.db"):
        os.remove("./test.db")


@pytest.fixture(scope="function")
def db_session(db_engine) -> Generator[Session, None, None]:
    """Create a test database session."""
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)
    session = TestingSessionLocal()

    # Override the dependency
    def override_get_db():
        try:
            yield session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    yield session

    session.close()
    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
async def async_client(db_session) -> AsyncGenerator[AsyncClient, None]:
    """Create an async test client."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as client:
        yield client


@pytest.fixture
def sample_audio_file():
    """Create a sample audio file for testing."""
    # Create a temporary file with minimal audio data
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
        # Write some minimal MP3 header data (not a valid MP3, but enough for type checking)
        f.write(b"ID3\x04\x00\x00\x00\x00\x00\x00")
        f.write(b"TEST MP3 AUDIO DATA")
        temp_path = f.name

    yield temp_path

    # Cleanup
    if os.path.exists(temp_path):
        os.remove(temp_path)


@pytest.fixture
def sample_audio_files():
    """Create multiple sample audio files for testing."""
    files = []
    extensions = [".mp3", ".wav", ".m4a", ".webm"]

    for ext in extensions:
        with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as f:
            # Write minimal header data
            if ext == ".mp3":
                f.write(b"ID3\x04\x00\x00\x00\x00\x00\x00")
            elif ext == ".wav":
                f.write(b"RIFF\x24\x00\x00\x00WAVE")
            f.write(b"TEST AUDIO DATA")
            files.append(f.name)

    yield files

    # Cleanup
    for file_path in files:
        if os.path.exists(file_path):
            os.remove(file_path)


@pytest.fixture
def invalid_files():
    """Create invalid files for testing file validation."""
    files = []

    # Create files with invalid extensions
    for ext in [".txt", ".pdf", ".doc", ".exe", ".jpg"]:
        with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as f:
            f.write(b"INVALID FILE CONTENT")
            files.append((f.name, ext))

    yield files

    # Cleanup
    for file_path, _ in files:
        if os.path.exists(file_path):
            os.remove(file_path)


@pytest.fixture
def sample_transcript(db_session):
    """Create a sample transcript in the database."""
    transcript = Transcript(
        original_filename="test_audio.mp3",
        file_path="/tmp/test_audio.mp3",
        file_size=1024,
        language="en",
        status=TranscriptStatus.COMPLETED,
        transcription_text="This is a sample transcription text for testing purposes.",
        transcription_json={"text": "This is a sample transcription text for testing purposes.", "segments": []},
        tags=["test", "sample"],
        category="meeting"
    )
    db_session.add(transcript)
    db_session.commit()
    db_session.refresh(transcript)
    return transcript


@pytest.fixture
def sample_transcripts(db_session):
    """Create multiple sample transcripts in the database."""
    transcripts = []

    # Completed transcript in English
    t1 = Transcript(
        original_filename="meeting1.mp3",
        file_path="/tmp/meeting1.mp3",
        file_size=2048,
        language="en",
        status=TranscriptStatus.COMPLETED,
        transcription_text="First meeting transcript about project planning.",
        tags=["meeting", "planning"],
        category="meeting"
    )
    transcripts.append(t1)

    # Completed transcript in Russian
    t2 = Transcript(
        original_filename="interview1.mp3",
        file_path="/tmp/interview1.mp3",
        file_size=3072,
        language="ru",
        status=TranscriptStatus.COMPLETED,
        transcription_text="Транскрипция интервью на русском языке.",
        tags=["interview", "russian"],
        category="interview"
    )
    transcripts.append(t2)

    # Pending transcript
    t3 = Transcript(
        original_filename="pending.mp3",
        file_path="/tmp/pending.mp3",
        file_size=1024,
        language="en",
        status=TranscriptStatus.PENDING,
        transcription_text=None
    )
    transcripts.append(t3)

    # Failed transcript
    t4 = Transcript(
        original_filename="failed.mp3",
        file_path="/tmp/failed.mp3",
        file_size=512,
        language="en",
        status=TranscriptStatus.FAILED,
        transcription_text=None
    )
    transcripts.append(t4)

    # Processing transcript
    t5 = Transcript(
        original_filename="processing.mp3",
        file_path="/tmp/processing.mp3",
        file_size=4096,
        language="en",
        status=TranscriptStatus.PROCESSING,
        transcription_text=None
    )
    transcripts.append(t5)

    db_session.add_all(transcripts)
    db_session.commit()

    for t in transcripts:
        db_session.refresh(t)

    return transcripts


@pytest.fixture
def sample_summary(db_session, sample_transcript):
    """Create a sample summary in the database."""
    summary = Summary(
        transcript_id=sample_transcript.id,
        summary_text="This is a sample summary of the transcript.",
        summary_template="meeting",
        summary_config={"participants": True, "decisions": True},
        model_used="GigaChat-2-Max"
    )
    db_session.add(summary)
    db_session.commit()
    db_session.refresh(summary)
    return summary


@pytest.fixture
def sample_summaries(db_session, sample_transcripts):
    """Create multiple sample summaries."""
    summaries = []

    for i, transcript in enumerate(sample_transcripts[:2]):
        if transcript.status == TranscriptStatus.COMPLETED:
            summary = Summary(
                transcript_id=transcript.id,
                summary_text=f"Summary {i+1} for transcript {transcript.original_filename}",
                summary_template="meeting",
                model_used="GigaChat-2-Max"
            )
            summaries.append(summary)

    db_session.add_all(summaries)
    db_session.commit()

    for s in summaries:
        db_session.refresh(s)

    return summaries


@pytest.fixture
def sample_rag_session(db_session):
    """Create a sample RAG session."""
    session = RAGSession(
        session_name="Test Session",
        transcript_ids=["uuid1", "uuid2"]
    )
    db_session.add(session)
    db_session.commit()
    db_session.refresh(session)
    return session


@pytest.fixture
def sample_rag_sessions(db_session):
    """Create multiple sample RAG sessions."""
    sessions = []

    for i in range(3):
        session = RAGSession(
            session_name=f"Session {i+1}",
            transcript_ids=[f"uuid{i}1", f"uuid{i}2"]
        )
        sessions.append(session)

    db_session.add_all(sessions)
    db_session.commit()

    for s in sessions:
        db_session.refresh(s)

    return sessions


@pytest.fixture
def sample_processing_job(db_session, sample_transcript):
    """Create a sample processing job."""
    job = ProcessingJob(
        transcript_id=sample_transcript.id,
        job_type=JobType.TRANSCRIPTION,
        status=JobStatus.COMPLETED,
        progress=1.0
    )
    db_session.add(job)
    db_session.commit()
    db_session.refresh(job)
    return job


@pytest.fixture
def auth_headers():
    """Return sample authentication headers."""
    # Note: Implement actual auth when authentication is added
    return {"Authorization": "Bearer test_token"}


# Helper functions for tests
@pytest.fixture
def create_transcript_helper(db_session):
    """Helper function to create transcripts."""
    def _create(**kwargs):
        defaults = {
            "original_filename": "test.mp3",
            "file_path": "/tmp/test.mp3",
            "file_size": 1024,
            "language": "en",
            "status": TranscriptStatus.COMPLETED,
            "transcription_text": "Test transcription"
        }
        defaults.update(kwargs)

        transcript = Transcript(**defaults)
        db_session.add(transcript)
        db_session.commit()
        db_session.refresh(transcript)
        return transcript

    return _create


@pytest.fixture
def create_summary_helper(db_session):
    """Helper function to create summaries."""
    def _create(transcript_id, **kwargs):
        defaults = {
            "transcript_id": transcript_id,
            "summary_text": "Test summary",
            "summary_template": "meeting",
            "model_used": "GigaChat-2-Max"
        }
        defaults.update(kwargs)

        summary = Summary(**defaults)
        db_session.add(summary)
        db_session.commit()
        db_session.refresh(summary)
        return summary

    return _create


@pytest.fixture
def create_rag_session_helper(db_session):
    """Helper function to create RAG sessions."""
    def _create(**kwargs):
        defaults = {
            "session_name": "Test Session",
            "transcript_ids": []
        }
        defaults.update(kwargs)

        session = RAGSession(**defaults)
        db_session.add(session)
        db_session.commit()
        db_session.refresh(session)
        return session

    return _create


def pytest_configure(config):
    """Configure pytest to recognize async tests."""
    config.addinivalue_line(
        "markers", "asyncio: mark test as an asyncio test"
    )


def pytest_collection_modifyitems(items):
    """Modify collected test items to run async tests properly."""
    pytest_asyncio_tests = (item for item in items if is_async_test(item))
    session_scope_marker = pytest.mark.asyncio(loop_scope="session")
    for async_test in pytest_asyncio_tests:
        async_test.add_marker(session_scope_marker)
