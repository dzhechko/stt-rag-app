"""
Comprehensive integration tests for Transcript API endpoints.

Tests cover:
- POST /api/transcripts/upload - File upload with validation
- GET /api/transcripts - List with pagination and filtering
- GET /api/transcripts/{id} - Retrieve single transcript
- PUT /api/transcripts/{id} - Update transcript
- DELETE /api/transcripts/{id} - Delete transcript
- GET /api/transcripts/{id}/jobs - Get processing jobs
"""
import os
import pytest
from uuid import UUID, uuid4
from httpx import AsyncClient
from sqlalchemy.orm import Session

from app.database import Transcript, TranscriptStatus, ProcessingJob, JobType, JobStatus


class TestTranscriptUpload:
    """Test cases for transcript file upload endpoint."""

    @pytest.mark.asyncio
    async def test_upload_valid_audio_file(self, async_client: AsyncClient, sample_audio_file):
        """Test successful upload of a valid audio file."""
        with open(sample_audio_file, "rb") as f:
            response = await async_client.post(
                "/api/transcripts/upload",
                files={"file": ("test_audio.mp3", f, "audio/mpeg")}
            )

        assert response.status_code == 201
        data = response.json()

        # Verify response structure
        assert "id" in data
        assert "original_filename" in data
        assert data["original_filename"] == "test_audio.mp3"
        assert data["status"] == "pending"
        assert "file_size" in data
        assert "created_at" in data

        # Verify UUID format
        UUID(data["id"])

    @pytest.mark.asyncio
    async def test_upload_with_language_parameter(self, async_client: AsyncClient, sample_audio_file):
        """Test upload with explicit language parameter."""
        with open(sample_audio_file, "rb") as f:
            response = await async_client.post(
                "/api/transcripts/upload",
                files={"file": ("test_audio.mp3", f, "audio/mpeg")},
                data={"language": "ru"}
            )

        assert response.status_code == 201
        data = response.json()
        assert data["language"] == "ru"

    @pytest.mark.asyncio
    async def test_upload_with_language_variations(self, async_client: AsyncClient, sample_audio_file):
        """Test upload with different language parameter formats."""
        language_variations = [
            ("ru", "ru"),
            ("russian", "ru"),
            ("русский", "ru"),
            ("en", "en"),
            ("english", "en"),
        ]

        for input_lang, expected_lang in language_variations:
            with open(sample_audio_file, "rb") as f:
                response = await async_client.post(
                    "/api/transcripts/upload",
                    files={"file": (f"test_{input_lang}.mp3", f, "audio/mpeg")},
                    data={"language": input_lang}
                )

            assert response.status_code == 201
            data = response.json()
            assert data["language"] == expected_lang

    @pytest.mark.asyncio
    async def test_upload_unsupported_file_type(self, async_client: AsyncClient, invalid_files):
        """Test that unsupported file types are rejected."""
        for file_path, ext in invalid_files:
            with open(file_path, "rb") as f:
                response = await async_client.post(
                    "/api/transcripts/upload",
                    files={"file": (f"test{ext}", f, "application/octet-stream")}
                )

            assert response.status_code == 400
            assert "not supported" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_upload_missing_file(self, async_client: AsyncClient):
        """Test upload without a file parameter."""
        response = await async_client.post("/api/transcripts/upload")

        # FastAPI returns 422 for missing required parameters
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_upload_empty_file(self, async_client: AsyncClient, tmp_path):
        """Test upload of an empty file."""
        empty_file = tmp_path / "empty.mp3"
        empty_file.write_text("")

        with open(empty_file, "rb") as f:
            response = await async_client.post(
                "/api/transcripts/upload",
                files={"file": ("empty.mp3", f, "audio/mpeg")}
            )

        # Empty files should be accepted (size 0 is valid)
        assert response.status_code == 201
        data = response.json()
        assert data["file_size"] == 0

    @pytest.mark.asyncio
    async def test_upload_creates_processing_job(self, async_client: AsyncClient, sample_audio_file, db_session: Session):
        """Test that uploading creates a corresponding processing job."""
        with open(sample_audio_file, "rb") as f:
            response = await async_client.post(
                "/api/transcripts/upload",
                files={"file": ("test.mp3", f, "audio/mpeg")}
            )

        assert response.status_code == 201
        transcript_id = response.json()["id"]

        # Verify job was created
        jobs = db_session.query(ProcessingJob).filter(
            ProcessingJob.transcript_id == transcript_id
        ).all()

        assert len(jobs) == 1
        assert jobs[0].job_type == JobType.TRANSCRIPTION
        assert jobs[0].status == JobStatus.QUEUED


class TestListTranscripts:
    """Test cases for listing transcripts endpoint."""

    @pytest.mark.asyncio
    async def test_list_transcripts_empty(self, async_client: AsyncClient, db_session: Session):
        """Test listing transcripts when database is empty."""
        response = await async_client.get("/api/transcripts")

        assert response.status_code == 200
        data = response.json()
        assert "transcripts" in data
        assert "total" in data
        assert data["total"] == 0
        assert len(data["transcripts"]) == 0

    @pytest.mark.asyncio
    async def test_list_transcripts_with_data(self, async_client: AsyncClient, sample_transcripts):
        """Test listing transcripts with existing data."""
        response = await async_client.get("/api/transcripts")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 5
        assert len(data["transcripts"]) == 5

        # Verify transcript structure
        transcript = data["transcripts"][0]
        assert "id" in transcript
        assert "original_filename" in transcript
        assert "status" in transcript
        assert "created_at" in transcript

    @pytest.mark.asyncio
    async def test_list_transcripts_pagination(self, async_client: AsyncClient, sample_transcripts):
        """Test pagination of transcripts list."""
        # First page
        response = await async_client.get("/api/transcripts?skip=0&limit=2")
        assert response.status_code == 200
        data = response.json()
        assert len(data["transcripts"]) == 2
        assert data["total"] == 5

        # Second page
        response = await async_client.get("/api/transcripts?skip=2&limit=2")
        assert response.status_code == 200
        data = response.json()
        assert len(data["transcripts"]) == 2

    @pytest.mark.asyncio
    async def test_list_transcripts_filter_by_status(self, async_client: AsyncClient, sample_transcripts):
        """Test filtering transcripts by status."""
        # Filter by completed status
        response = await async_client.get("/api/transcripts?status=completed")
        assert response.status_code == 200
        data = response.json()
        assert all(t["status"] == "completed" for t in data["transcripts"])

        # Filter by pending status
        response = await async_client.get("/api/transcripts?status=pending")
        assert response.status_code == 200
        data = response.json()
        assert all(t["status"] == "pending" for t in data["transcripts"])

    @pytest.mark.asyncio
    async def test_list_transcripts_filter_by_language(self, async_client: AsyncClient, sample_transcripts):
        """Test filtering transcripts by language."""
        # Filter by English
        response = await async_client.get("/api/transcripts?language=en")
        assert response.status_code == 200
        data = response.json()
        assert all(t["language"] == "en" for t in data["transcripts"])

        # Filter by Russian
        response = await async_client.get("/api/transcripts?language=ru")
        assert response.status_code == 200
        data = response.json()
        assert all(t["language"] == "ru" for t in data["transcripts"])

    @pytest.mark.asyncio
    async def test_list_transcripts_invalid_status_filter(self, async_client: AsyncClient):
        """Test that invalid status filter returns 400."""
        response = await async_client.get("/api/transcripts?status=invalid_status")

        assert response.status_code == 400
        assert "invalid status" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_list_transcripts_empty_status_filter(self, async_client: AsyncClient, sample_transcripts):
        """Test that empty status filter is ignored."""
        # Empty string should be ignored
        response = await async_client.get("/api/transcripts?status=")
        assert response.status_code == 200
        data = response.json()
        # Should return all transcripts
        assert data["total"] == 5

    @pytest.mark.asyncio
    async def test_list_transcripts_combined_filters(self, async_client: AsyncClient, sample_transcripts):
        """Test combining multiple filters."""
        response = await async_client.get("/api/transcripts?status=completed&language=en")
        assert response.status_code == 200
        data = response.json()
        assert all(t["status"] == "completed" and t["language"] == "en" for t in data["transcripts"])

    @pytest.mark.asyncio
    async def test_list_transcripts_ordering(self, async_client: AsyncClient, sample_transcripts):
        """Test that transcripts are ordered by created_at descending."""
        response = await async_client.get("/api/transcripts")

        assert response.status_code == 200
        data = response.json()
        transcripts = data["transcripts"]

        # Verify ordering
        for i in range(len(transcripts) - 1):
            assert transcripts[i]["created_at"] >= transcripts[i+1]["created_at"]


class TestGetTranscript:
    """Test cases for getting a single transcript."""

    @pytest.mark.asyncio
    async def test_get_existing_transcript(self, async_client: AsyncClient, sample_transcript):
        """Test retrieving an existing transcript."""
        response = await async_client.get(f"/api/transcripts/{sample_transcript.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(sample_transcript.id)
        assert data["original_filename"] == sample_transcript.original_filename
        assert data["status"] == sample_transcript.status.value

    @pytest.mark.asyncio
    async def test_get_transcript_with_all_fields(self, async_client: AsyncClient, sample_transcript):
        """Test that all transcript fields are returned."""
        response = await async_client.get(f"/api/transcripts/{sample_transcript.id}")

        assert response.status_code == 200
        data = response.json()

        # Verify all expected fields
        expected_fields = [
            "id", "original_filename", "file_path", "file_size",
            "duration_seconds", "language", "status", "transcription_text",
            "transcription_json", "transcription_srt", "created_at",
            "updated_at", "extra_metadata", "tags", "category"
        ]

        for field in expected_fields:
            assert field in data

    @pytest.mark.asyncio
    async def test_get_transcript_not_found(self, async_client: AsyncClient):
        """Test retrieving a non-existent transcript."""
        fake_id = uuid4()
        response = await async_client.get(f"/api/transcripts/{fake_id}")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_get_transcript_invalid_uuid(self, async_client: AsyncClient):
        """Test retrieving with invalid UUID format."""
        response = await async_client.get("/api/transcripts/invalid-uuid")

        # FastAPI validates UUID format and returns 422
        assert response.status_code == 422


class TestUpdateTranscript:
    """Test cases for updating transcript endpoint."""

    @pytest.mark.asyncio
    async def test_update_transcript_text(self, async_client: AsyncClient, sample_transcript):
        """Test updating transcript text."""
        new_text = "Updated transcription text"
        response = await async_client.put(
            f"/api/transcripts/{sample_transcript.id}",
            json={"transcription_text": new_text}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["transcription_text"] == new_text

    @pytest.mark.asyncio
    async def test_update_transcript_tags(self, async_client: AsyncClient, sample_transcript):
        """Test updating transcript tags."""
        new_tags = ["updated", "test", "tags"]
        response = await async_client.put(
            f"/api/transcripts/{sample_transcript.id}",
            json={"tags": new_tags}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["tags"] == new_tags

    @pytest.mark.asyncio
    async def test_update_transcript_category(self, async_client: AsyncClient, sample_transcript):
        """Test updating transcript category."""
        new_category = "interview"
        response = await async_client.put(
            f"/api/transcripts/{sample_transcript.id}",
            json={"category": new_category}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["category"] == new_category

    @pytest.mark.asyncio
    async def test_update_transcript_metadata(self, async_client: AsyncClient, sample_transcript):
        """Test updating transcript metadata."""
        new_metadata = {"speaker_count": 3, "meeting_date": "2024-01-15"}
        response = await async_client.put(
            f"/api/transcripts/{sample_transcript.id}",
            json={"extra_metadata": new_metadata}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["extra_metadata"] == new_metadata

    @pytest.mark.asyncio
    async def test_update_multiple_fields(self, async_client: AsyncClient, sample_transcript):
        """Test updating multiple fields at once."""
        update_data = {
            "transcription_text": "New text",
            "tags": ["tag1", "tag2"],
            "category": "lecture"
        }
        response = await async_client.put(
            f"/api/transcripts/{sample_transcript.id}",
            json=update_data
        )

        assert response.status_code == 200
        data = response.json()
        assert data["transcription_text"] == "New text"
        assert data["tags"] == ["tag1", "tag2"]
        assert data["category"] == "lecture"

    @pytest.mark.asyncio
    async def test_update_transcript_not_found(self, async_client: AsyncClient):
        """Test updating a non-existent transcript."""
        fake_id = uuid4()
        response = await async_client.put(
            f"/api/transcripts/{fake_id}",
            json={"transcription_text": "test"}
        )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_update_with_empty_data(self, async_client: AsyncClient, sample_transcript):
        """Test update with empty JSON (no fields to update)."""
        response = await async_client.put(
            f"/api/transcripts/{sample_transcript.id}",
            json={}
        )

        # Should succeed but not change anything
        assert response.status_code == 200


class TestDeleteTranscript:
    """Test cases for deleting transcript endpoint."""

    @pytest.mark.asyncio
    async def test_delete_existing_transcript(self, async_client: AsyncClient, sample_transcript, db_session: Session):
        """Test successful deletion of a transcript."""
        transcript_id = sample_transcript.id

        response = await async_client.delete(f"/api/transcripts/{transcript_id}")

        assert response.status_code == 204

        # Verify deletion in database
        transcript = db_session.query(Transcript).filter(Transcript.id == transcript_id).first()
        assert transcript is None

    @pytest.mark.asyncio
    async def test_delete_transcript_not_found(self, async_client: AsyncClient):
        """Test deleting a non-existent transcript."""
        fake_id = uuid4()
        response = await async_client.delete(f"/api/transcripts/{fake_id}")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_delete_transcript_cascades_to_jobs(self, async_client: AsyncClient, db_session: Session):
        """Test that deleting a transcript cascades to processing jobs."""
        # Create transcript with job
        transcript = Transcript(
            original_filename="test.mp3",
            file_path="/tmp/test.mp3",
            file_size=1024,
            status=TranscriptStatus.COMPLETED
        )
        db_session.add(transcript)
        db_session.commit()

        job = ProcessingJob(
            transcript_id=transcript.id,
            job_type=JobType.TRANSCRIPTION,
            status=JobStatus.COMPLETED
        )
        db_session.add(job)
        db_session.commit()

        transcript_id = transcript.id

        # Delete transcript
        response = await async_client.delete(f"/api/transcripts/{transcript_id}")
        assert response.status_code == 204

        # Verify job was also deleted (cascade)
        jobs = db_session.query(ProcessingJob).filter(
            ProcessingJob.transcript_id == transcript_id
        ).all()
        assert len(jobs) == 0


class TestTranscriptJobs:
    """Test cases for transcript processing jobs endpoint."""

    @pytest.mark.asyncio
    async def test_get_transcript_jobs(self, async_client: AsyncClient, sample_transcript, sample_processing_job):
        """Test retrieving jobs for a transcript."""
        response = await async_client.get(f"/api/transcripts/{sample_transcript.id}/jobs")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1

        job = data[0]
        assert "id" in job
        assert "job_type" in job
        assert "status" in job
        assert "progress" in job

    @pytest.mark.asyncio
    async def test_get_transcript_jobs_empty(self, async_client: AsyncClient, sample_transcript):
        """Test retrieving jobs for transcript with no jobs."""
        # Delete any existing jobs
        response = await async_client.get(f"/api/transcripts/{sample_transcript.id}/jobs")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_get_jobs_for_nonexistent_transcript(self, async_client: AsyncClient):
        """Test retrieving jobs for non-existent transcript."""
        fake_id = uuid4()
        response = await async_client.get(f"/api/transcripts/{fake_id}/jobs")

        # Returns empty list instead of 404
        assert response.status_code == 200
        assert isinstance(response.json(), list)


class TestGetJob:
    """Test cases for getting a single processing job."""

    @pytest.mark.asyncio
    async def test_get_existing_job(self, async_client: AsyncClient, sample_processing_job):
        """Test retrieving an existing job."""
        response = await async_client.get(f"/api/jobs/{sample_processing_job.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(sample_processing_job.id)
        assert data["job_type"] == sample_processing_job.job_type.value
        assert data["status"] == sample_processing_job.status.value

    @pytest.mark.asyncio
    async def test_get_job_not_found(self, async_client: AsyncClient):
        """Test retrieving a non-existent job."""
        fake_id = uuid4()
        response = await async_client.get(f"/api/jobs/{fake_id}")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()


class TestTranscriptValidation:
    """Edge case and validation tests."""

    @pytest.mark.asyncio
    async def test_multiple_simultaneous_uploads(self, async_client: AsyncClient, sample_audio_files):
        """Test uploading multiple files simultaneously."""
        import asyncio

        async def upload_file(file_path):
            with open(file_path, "rb") as f:
                return await async_client.post(
                    "/api/transcripts/upload",
                    files={"file": (os.path.basename(file_path), f, "audio/mpeg")}
                )

        # Upload all files concurrently
        responses = await asyncio.gather(*[upload_file(f) for f in sample_audio_files])

        # All should succeed
        for response in responses:
            assert response.status_code == 201

    @pytest.mark.asyncio
    async def test_upload_file_with_special_characters(self, async_client: AsyncClient, sample_audio_file):
        """Test uploading file with special characters in name."""
        import shutil

        # Create file with special characters
        special_name = "test file (1) [special].mp3"
        special_file = f"/tmp/{special_name}"
        shutil.copy(sample_audio_file, special_file)

        try:
            with open(special_file, "rb") as f:
                response = await async_client.post(
                    "/api/transcripts/upload",
                    files={"file": (special_name, f, "audio/mpeg")}
                )

            assert response.status_code == 201
            data = response.json()
            assert data["original_filename"] == special_name
        finally:
            if os.path.exists(special_file):
                os.remove(special_file)

    @pytest.mark.asyncio
    async def test_upload_file_with_unicode_name(self, async_client: AsyncClient, sample_audio_file):
        """Test uploading file with Unicode characters in name."""
        import shutil

        unicode_name = "тестовый файл.mp3"
        unicode_file = f"/tmp/{unicode_name}"
        shutil.copy(sample_audio_file, unicode_file)

        try:
            with open(unicode_file, "rb") as f:
                response = await async_client.post(
                    "/api/transcripts/upload",
                    files={"file": (unicode_name, f, "audio/mpeg")}
                )

            assert response.status_code == 201
            data = response.json()
            assert data["original_filename"] == unicode_name
        finally:
            if os.path.exists(unicode_file):
                os.remove(unicode_file)
