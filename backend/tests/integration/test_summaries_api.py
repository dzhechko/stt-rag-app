"""
Comprehensive integration tests for Summary API endpoints.

Tests cover:
- POST /api/summaries - Create summary with templates
- GET /api/transcripts/{id}/summaries - Get all summaries for transcript
- GET /api/summaries/{id} - Get single summary
- DELETE /api/summaries/{id} - Delete summary (if implemented)
"""
import pytest
from uuid import uuid4
from httpx import AsyncClient
from sqlalchemy.orm import Session

from app.database import Transcript, TranscriptStatus, Summary, ProcessingJob, JobType, JobStatus


class TestCreateSummary:
    """Test cases for creating summaries."""

    @pytest.mark.asyncio
    async def test_create_summary_default_template(self, async_client: AsyncClient, sample_transcript):
        """Test creating a summary with default template."""
        response = await async_client.post(
            "/api/summaries",
            json={
                "transcript_id": str(sample_transcript.id)
            }
        )

        assert response.status_code == 201
        data = response.json()

        # Verify response structure
        assert "id" in data
        assert "transcript_id" in data
        assert data["transcript_id"] == str(sample_transcript.id)
        assert "summary_text" in data
        assert "model_used" in data
        assert "created_at" in data

    @pytest.mark.asyncio
    async def test_create_summary_with_template(self, async_client: AsyncClient, sample_transcript):
        """Test creating a summary with a specific template."""
        templates = ["meeting", "interview", "lecture", "podcast"]

        for template in templates:
            response = await async_client.post(
                "/api/summaries",
                json={
                    "transcript_id": str(sample_transcript.id),
                    "template": template
                }
            )

            assert response.status_code == 201
            data = response.json()
            assert data["summary_template"] == template

    @pytest.mark.asyncio
    async def test_create_summary_with_custom_prompt(self, async_client: AsyncClient, sample_transcript):
        """Test creating a summary with a custom prompt."""
        custom_prompt = "Summarize the key decisions made in this meeting."

        response = await async_client.post(
            "/api/summaries",
            json={
                "transcript_id": str(sample_transcript.id),
                "custom_prompt": custom_prompt
            }
        )

        assert response.status_code == 201
        data = response.json()
        assert data["id"] is not None

    @pytest.mark.asyncio
    async def test_create_summary_with_fields_config(self, async_client: AsyncClient, sample_transcript):
        """Test creating a summary with fields configuration."""
        fields_config = {
            "participants": True,
            "decisions": True,
            "deadlines": True,
            "topics": False
        }

        response = await async_client.post(
            "/api/summaries",
            json={
                "transcript_id": str(sample_transcript.id),
                "fields_config": fields_config
            }
        )

        assert response.status_code == 201
        data = response.json()
        assert data["summary_config"] is not None

    @pytest.mark.asyncio
    async def test_create_summary_with_model(self, async_client: AsyncClient, sample_transcript):
        """Test creating a summary with a specific model."""
        models = [
            "GigaChat-2-Max",
            "GigaChat-2",
            "Qwen3-235B-A22B-Instruct-2507"
        ]

        for model in models:
            response = await async_client.post(
                "/api/summaries",
                json={
                    "transcript_id": str(sample_transcript.id),
                    "model": model
                }
            )

            assert response.status_code == 201
            data = response.json()
            assert model in data["model_used"]

    @pytest.mark.asyncio
    async def test_create_summary_all_parameters(self, async_client: AsyncClient, sample_transcript):
        """Test creating a summary with all parameters."""
        summary_data = {
            "transcript_id": str(sample_transcript.id),
            "template": "meeting",
            "custom_prompt": "Focus on action items",
            "fields_config": {
                "participants": True,
                "decisions": True,
                "deadlines": True
            },
            "model": "GigaChat-2-Max"
        }

        response = await async_client.post(
            "/api/summaries",
            json=summary_data
        )

        assert response.status_code == 201
        data = response.json()
        assert data["transcript_id"] == str(sample_transcript.id)

    @pytest.mark.asyncio
    async def test_create_summary_nonexistent_transcript(self, async_client: AsyncClient):
        """Test creating a summary for non-existent transcript."""
        fake_id = uuid4()

        response = await async_client.post(
            "/api/summaries",
            json={
                "transcript_id": str(fake_id)
            }
        )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_create_summary_pending_transcript(self, async_client: AsyncClient, db_session: Session):
        """Test that summary creation fails for pending transcript."""
        # Create a pending transcript
        transcript = Transcript(
            original_filename="pending.mp3",
            file_path="/tmp/pending.mp3",
            file_size=1024,
            status=TranscriptStatus.PENDING,
            transcription_text=None
        )
        db_session.add(transcript)
        db_session.commit()
        db_session.refresh(transcript)

        response = await async_client.post(
            "/api/summaries",
            json={
                "transcript_id": str(transcript.id)
            }
        )

        assert response.status_code == 400
        assert "not completed" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_create_summary_transcript_no_text(self, async_client: AsyncClient, db_session: Session):
        """Test that summary creation fails for transcript without text."""
        # Create a completed transcript with no text
        transcript = Transcript(
            original_filename="no_text.mp3",
            file_path="/tmp/no_text.mp3",
            file_size=1024,
            status=TranscriptStatus.COMPLETED,
            transcription_text=None
        )
        db_session.add(transcript)
        db_session.commit()
        db_session.refresh(transcript)

        response = await async_client.post(
            "/api/summaries",
            json={
                "transcript_id": str(transcript.id)
            }
        )

        assert response.status_code == 400
        assert "no text" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_create_summary_creates_job(self, async_client: AsyncClient, sample_transcript, db_session: Session):
        """Test that creating a summary creates a processing job."""
        response = await async_client.post(
            "/api/summaries",
            json={
                "transcript_id": str(sample_transcript.id)
            }
        )

        assert response.status_code == 201

        # Verify job was created
        jobs = db_session.query(ProcessingJob).filter(
            ProcessingJob.transcript_id == sample_transcript.id,
            ProcessingJob.job_type == JobType.SUMMARIZATION
        ).all()

        assert len(jobs) >= 1
        assert jobs[0].status == JobStatus.QUEUED

    @pytest.mark.asyncio
    async def test_create_summary_invalid_uuid(self, async_client: AsyncClient):
        """Test creating summary with invalid UUID."""
        response = await async_client.post(
            "/api/summaries",
            json={
                "transcript_id": "invalid-uuid"
            }
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_create_summary_missing_transcript_id(self, async_client: AsyncClient):
        """Test creating summary without transcript_id."""
        response = await async_client.post(
            "/api/summaries",
            json={}
        )

        assert response.status_code == 422


class TestGetTranscriptSummaries:
    """Test cases for getting summaries for a transcript."""

    @pytest.mark.asyncio
    async def test_get_summaries_existing(self, async_client: AsyncClient, sample_transcript, sample_summaries):
        """Test getting summaries for a transcript."""
        response = await async_client.get(f"/api/transcripts/{sample_transcript.id}/summaries")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1

        summary = data[0]
        assert "id" in summary
        assert "transcript_id" in summary
        assert "summary_text" in summary
        assert "created_at" in summary

    @pytest.mark.asyncio
    async def test_get_summaries_empty(self, async_client: AsyncClient, sample_transcript):
        """Test getting summaries when none exist."""
        # Delete any existing summaries
        response = await async_client.get(f"/api/transcripts/{sample_transcript.id}/summaries")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_get_summaries_ordering(self, async_client: AsyncClient, sample_transcript, db_session: Session):
        """Test that summaries are ordered by created_at descending."""
        # Create multiple summaries
        for i in range(3):
            summary = Summary(
                transcript_id=sample_transcript.id,
                summary_text=f"Summary {i}",
                model_used="GigaChat-2-Max"
            )
            db_session.add(summary)
        db_session.commit()

        response = await async_client.get(f"/api/transcripts/{sample_transcript.id}/summaries")

        assert response.status_code == 200
        data = response.json()

        # Verify ordering (newest first)
        for i in range(len(data) - 1):
            assert data[i]["created_at"] >= data[i+1]["created_at"]

    @pytest.mark.asyncio
    async def test_get_summaries_nonexistent_transcript(self, async_client: AsyncClient):
        """Test getting summaries for non-existent transcript."""
        fake_id = uuid4()
        response = await async_client.get(f"/api/transcripts/{fake_id}/summaries")

        # Returns empty list instead of 404
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    @pytest.mark.asyncio
    async def test_get_summaries_invalid_uuid(self, async_client: AsyncClient):
        """Test getting summaries with invalid UUID."""
        response = await async_client.get("/api/transcripts/invalid-uuid/summaries")

        assert response.status_code == 422


class TestGetSingleSummary:
    """Test cases for getting a single summary."""

    @pytest.mark.asyncio
    async def test_get_summary_existing(self, async_client: AsyncClient, sample_summary):
        """Test retrieving an existing summary."""
        response = await async_client.get(f"/api/summaries/{sample_summary.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(sample_summary.id)
        assert data["transcript_id"] == str(sample_summary.transcript_id)
        assert "summary_text" in data
        assert "model_used" in data

    @pytest.mark.asyncio
    async def test_get_summary_with_all_fields(self, async_client: AsyncClient, sample_summary):
        """Test that all summary fields are returned."""
        response = await async_client.get(f"/api/summaries/{sample_summary.id}")

        assert response.status_code == 200
        data = response.json()

        # Verify all expected fields
        expected_fields = [
            "id", "transcript_id", "summary_text",
            "summary_template", "summary_config", "model_used",
            "created_at", "updated_at"
        ]

        for field in expected_fields:
            assert field in data

    @pytest.mark.asyncio
    async def test_get_summary_not_found(self, async_client: AsyncClient):
        """Test retrieving a non-existent summary."""
        fake_id = uuid4()
        response = await async_client.get(f"/api/summaries/{fake_id}")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_get_summary_invalid_uuid(self, async_client: AsyncClient):
        """Test retrieving with invalid UUID format."""
        response = await async_client.get("/api/summaries/invalid-uuid")

        assert response.status_code == 422


class TestSummaryValidation:
    """Edge case and validation tests for summaries."""

    @pytest.mark.asyncio
    async def test_create_multiple_summaries_same_transcript(self, async_client: AsyncClient, sample_transcript):
        """Test creating multiple summaries for the same transcript."""
        summaries_created = []

        for i in range(3):
            response = await async_client.post(
                "/api/summaries",
                json={
                    "transcript_id": str(sample_transcript.id),
                    "template": "meeting"
                }
            )

            assert response.status_code == 201
            summaries_created.append(response.json()["id"])

        # Verify all summaries exist
        response = await async_client.get(f"/api/transcripts/{sample_transcript.id}/summaries")
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 3

    @pytest.mark.asyncio
    async def test_create_summary_with_invalid_template(self, async_client: AsyncClient, sample_transcript):
        """Test creating summary with invalid template (should still work)."""
        response = await async_client.post(
            "/api/summaries",
            json={
                "transcript_id": str(sample_transcript.id),
                "template": "invalid_template"
            }
        )

        # Invalid template is passed through - service layer handles it
        assert response.status_code == 201

    @pytest.mark.asyncio
    async def test_create_summary_with_empty_fields_config(self, async_client: AsyncClient, sample_transcript):
        """Test creating summary with empty fields config."""
        response = await async_client.post(
            "/api/summaries",
            json={
                "transcript_id": str(sample_transcript.id),
                "fields_config": {}
            }
        )

        assert response.status_code == 201

    @pytest.mark.asyncio
    async def test_create_summary_with_null_parameters(self, async_client: AsyncClient, sample_transcript):
        """Test creating summary with null optional parameters."""
        response = await async_client.post(
            "/api/summaries",
            json={
                "transcript_id": str(sample_transcript.id),
                "template": None,
                "custom_prompt": None,
                "fields_config": None,
                "model": None
            }
        )

        assert response.status_code == 201

    @pytest.mark.asyncio
    async def test_summary_response_schema_validation(self, async_client: AsyncClient, sample_summary):
        """Test that summary response matches expected schema."""
        response = await async_client.get(f"/api/summaries/{sample_summary.id}")

        assert response.status_code == 200
        data = response.json()

        # Verify data types
        assert isinstance(data["id"], str)
        assert isinstance(data["transcript_id"], str)
        assert isinstance(data["summary_text"], str)
        assert isinstance(data["model_used"], str)
        assert data["summary_template"] is None or isinstance(data["summary_template"], str)
        assert data["summary_config"] is None or isinstance(data["summary_config"], dict)

    @pytest.mark.asyncio
    async def test_failed_transcript_cannot_summarize(self, async_client: AsyncClient, db_session: Session):
        """Test that failed transcripts cannot be summarized."""
        transcript = Transcript(
            original_filename="failed.mp3",
            file_path="/tmp/failed.mp3",
            file_size=1024,
            status=TranscriptStatus.FAILED,
            transcription_text=None
        )
        db_session.add(transcript)
        db_session.commit()
        db_session.refresh(transcript)

        response = await async_client.post(
            "/api/summaries",
            json={
                "transcript_id": str(transcript.id)
            }
        )

        assert response.status_code == 400
        assert "not completed" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_processing_transcript_cannot_summarize(self, async_client: AsyncClient, db_session: Session):
        """Test that processing transcripts cannot be summarized."""
        transcript = Transcript(
            original_filename="processing.mp3",
            file_path="/tmp/processing.mp3",
            file_size=1024,
            status=TranscriptStatus.PROCESSING,
            transcription_text=None
        )
        db_session.add(transcript)
        db_session.commit()
        db_session.refresh(transcript)

        response = await async_client.post(
            "/api/summaries",
            json={
                "transcript_id": str(transcript.id)
            }
        )

        assert response.status_code == 400
        assert "not completed" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_summary_from_translated_transcript(self, async_client: AsyncClient, db_session: Session):
        """Test creating summary from a translated transcript."""
        # Create a transcript with translation metadata
        transcript = Transcript(
            original_filename="translated.mp3",
            file_path="/tmp/translated.mp3",
            file_size=1024,
            status=TranscriptStatus.COMPLETED,
            language="ru",
            transcription_text="Переведенный текст транскрипции.",
            extra_metadata={
                "translated": True,
                "original_english_text": "Original English transcript text."
            }
        )
        db_session.add(transcript)
        db_session.commit()
        db_session.refresh(transcript)

        response = await async_client.post(
            "/api/summaries",
            json={
                "transcript_id": str(transcript.id),
                "template": "meeting"
            }
        )

        assert response.status_code == 201
        data = response.json()
        assert data["transcript_id"] == str(transcript.id)

    @pytest.mark.asyncio
    async def test_concurrent_summary_creation(self, async_client: AsyncClient, sample_transcript):
        """Test creating multiple summaries concurrently."""
        import asyncio

        async def create_summary(template):
            return await async_client.post(
                "/api/summaries",
                json={
                    "transcript_id": str(sample_transcript.id),
                    "template": template
                }
            )

        templates = ["meeting", "interview", "lecture"]
        responses = await asyncio.gather(*[create_summary(t) for t in templates])

        for response in responses:
            assert response.status_code == 201
