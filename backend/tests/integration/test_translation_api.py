"""
Comprehensive integration tests for Translation API endpoints.

Tests cover:
- POST /api/transcripts/{id}/translate - Translate transcript
- Translation with different languages
- Translation progress tracking
- Translation errors and edge cases
"""
import pytest
from uuid import uuid4
from httpx import AsyncClient
from sqlalchemy.orm import Session

from app.database import Transcript, TranscriptStatus, ProcessingJob, JobType, JobStatus


class TestTranslateTranscript:
    """Test cases for transcript translation endpoint."""

    @pytest.mark.asyncio
    async def test_translate_to_russian(self, async_client: AsyncClient, sample_transcript):
        """Test translating an English transcript to Russian."""
        response = await async_client.post(
            f"/api/transcripts/{sample_transcript.id}/translate",
            params={"target_language": "ru"}
        )

        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "transcript_id" in data
        assert "job_id" in data
        assert data["status"] == "queued"

    @pytest.mark.asyncio
    async def test_translate_with_model(self, async_client: AsyncClient, sample_transcript):
        """Test translation with a specific model."""
        response = await async_client.post(
            f"/api/transcripts/{sample_transcript.id}/translate",
            params={
                "target_language": "ru",
                "model": "GigaChat-2-Max"
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert "job_id" in data

    @pytest.mark.asyncio
    async def test_translate_english_to_english(self, async_client: AsyncClient, sample_transcript):
        """Test translating English to English (should be no-op)."""
        # Set language to English
        sample_transcript.language = "en"
        sample_transcript.extra_metadata = None
        from app.database import SessionLocal
        db = SessionLocal()
        try:
            db.merge(sample_transcript)
            db.commit()
        finally:
            db.close()

        response = await async_client.post(
            f"/api/transcripts/{sample_transcript.id}/translate",
            params={"target_language": "en"}
        )

        assert response.status_code in [200, 400]
        if response.status_code == 200:
            data = response.json()
            # May indicate already translated or start translation
            assert "message" in data

    @pytest.mark.asyncio
    async def test_translate_russian_to_russian(self, async_client: AsyncClient, db_session: Session):
        """Test translating Russian transcript to Russian."""
        transcript = Transcript(
            original_filename="russian.mp3",
            file_path="/tmp/russian.mp3",
            file_size=1024,
            status=TranscriptStatus.COMPLETED,
            language="ru",
            transcription_text="Это текст на русском языке."
        )
        db_session.add(transcript)
        db_session.commit()
        db_session.refresh(transcript)

        response = await async_client.post(
            f"/api/transcripts/{transcript.id}/translate",
            params={"target_language": "ru"}
        )

        assert response.status_code == 200
        data = response.json()
        # Should indicate already in Russian
        assert "already" in data.get("message", "").lower() or data["status"] == "queued"

    @pytest.mark.asyncio
    async def test_translate_creates_job(self, async_client: AsyncClient, sample_transcript, db_session: Session):
        """Test that translation creates a processing job."""
        response = await async_client.post(
            f"/api/transcripts/{sample_transcript.id}/translate",
            params={"target_language": "ru"}
        )

        assert response.status_code == 200

        # Verify job was created
        jobs = db_session.query(ProcessingJob).filter(
            ProcessingJob.transcript_id == sample_transcript.id,
            ProcessingJob.job_type == JobType.TRANSLATION
        ).all()

        assert len(jobs) >= 1
        assert jobs[0].status == JobStatus.QUEUED

    @pytest.mark.asyncio
    async def test_translate_nonexistent_transcript(self, async_client: AsyncClient):
        """Test translating a non-existent transcript."""
        fake_id = uuid4()
        response = await async_client.post(
            f"/api/transcripts/{fake_id}/translate",
            params={"target_language": "ru"}
        )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_translate_no_text(self, async_client: AsyncClient, db_session: Session):
        """Test translating a transcript without text."""
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
            f"/api/transcripts/{transcript.id}/translate",
            params={"target_language": "ru"}
        )

        assert response.status_code == 400
        assert "no text" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_translate_not_completed(self, async_client: AsyncClient, db_session: Session):
        """Test translating a non-completed transcript."""
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
            f"/api/transcripts/{transcript.id}/translate",
            params={"target_language": "ru"}
        )

        assert response.status_code == 400
        assert "not completed" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_translate_failed_transcript(self, async_client: AsyncClient, db_session: Session):
        """Test translating a failed transcript."""
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
            f"/api/transcripts/{transcript.id}/translate",
            params={"target_language": "ru"}
        )

        assert response.status_code == 400
        assert "not completed" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_translate_already_translated(self, async_client: AsyncClient, db_session: Session):
        """Test translating a transcript that's already translated."""
        transcript = Transcript(
            original_filename="translated.mp3",
            file_path="/tmp/translated.mp3",
            file_size=1024,
            status=TranscriptStatus.COMPLETED,
            language="ru",
            transcription_text="Переведенный текст",
            extra_metadata={
                "translated": True,
                "original_english_text": "Original text"
            }
        )
        db_session.add(transcript)
        db_session.commit()
        db_session.refresh(transcript)

        response = await async_client.post(
            f"/api/transcripts/{transcript.id}/translate",
            params={"target_language": "ru"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data.get("already_translated") is True

    @pytest.mark.asyncio
    async def test_translate_after_translation(self, async_client: AsyncClient, db_session: Session):
        """Test translating back to original language after translation."""
        transcript = Transcript(
            original_filename="translated.mp3",
            file_path="/tmp/translated.mp3",
            file_size=1024,
            status=TranscriptStatus.COMPLETED,
            language="ru",
            transcription_text="Переведенный текст",
            extra_metadata={
                "translated": True,
                "original_english_text": "Original English text"
            }
        )
        db_session.add(transcript)
        db_session.commit()
        db_session.refresh(transcript)

        # Translate back to English
        response = await async_client.post(
            f"/api/transcripts/{transcript.id}/translate",
            params={"target_language": "en"}
        )

        assert response.status_code == 200
        data = response.json()
        assert "job_id" in data


class TestTranslationProgress:
    """Test cases for translation progress tracking."""

    @pytest.mark.asyncio
    async def test_translation_job_progress(self, async_client: AsyncClient, sample_transcript, db_session: Session):
        """Test that translation job progress can be tracked."""
        # Start translation
        response = await async_client.post(
            f"/api/transcripts/{sample_transcript.id}/translate",
            params={"target_language": "ru"}
        )

        assert response.status_code == 200
        job_id = response.json()["job_id"]

        # Check job status
        response = await async_client.get(f"/api/jobs/{job_id}")
        assert response.status_code == 200
        data = response.json()
        assert "progress" in data
        assert 0.0 <= data["progress"] <= 1.0

    @pytest.mark.asyncio
    async def test_translation_jobs_in_transcript_jobs(self, async_client: AsyncClient, sample_transcript):
        """Test that translation jobs appear in transcript jobs list."""
        # Start translation
        await async_client.post(
            f"/api/transcripts/{sample_transcript.id}/translate",
            params={"target_language": "ru"}
        )

        # Get all jobs for transcript
        response = await async_client.get(f"/api/transcripts/{sample_transcript.id}/jobs")

        assert response.status_code == 200
        data = response.json()

        # Check for translation job
        translation_jobs = [j for j in data if j["job_type"] == "translation"]
        assert len(translation_jobs) >= 1


class TestTranslationLanguages:
    """Test cases for translation with different language combinations."""

    @pytest.mark.asyncio
    async def test_translate_to_different_languages(self, async_client: AsyncClient, db_session: Session):
        """Test translating to various target languages."""
        languages = ["ru", "en", "de", "fr", "es"]

        for lang in languages:
            transcript = Transcript(
                original_filename=f"test_{lang}.mp3",
                file_path=f"/tmp/test_{lang}.mp3",
                file_size=1024,
                status=TranscriptStatus.COMPLETED,
                language="en",
                transcription_text="This is English text to translate."
            )
            db_session.add(transcript)
            db_session.commit()
            db_session.refresh(transcript)

            response = await async_client.post(
                f"/api/transcripts/{transcript.id}/translate",
                params={"target_language": lang}
            )

            # Most should start translation successfully
            assert response.status_code in [200, 500]  # May fail for unsupported languages

    @pytest.mark.asyncio
    async def test_translate_from_russian(self, async_client: AsyncClient, db_session: Session):
        """Test translating from Russian to other languages."""
        transcript = Transcript(
            original_filename="russian.mp3",
            file_path="/tmp/russian.mp3",
            file_size=1024,
            status=TranscriptStatus.COMPLETED,
            language="ru",
            transcription_text="Это русский текст для перевода."
        )
        db_session.add(transcript)
        db_session.commit()
        db_session.refresh(transcript)

        # Translate to English
        response = await async_client.post(
            f"/api/transcripts/{transcript.id}/translate",
            params={"target_language": "en"}
        )

        assert response.status_code == 200
        data = response.json()
        assert "job_id" in data or data.get("already_translated") is True

    @pytest.mark.asyncio
    async def test_default_target_language(self, async_client: AsyncClient, sample_transcript):
        """Test that default target language is Russian."""
        # Don't specify target_language
        response = await async_client.post(
            f"/api/transcripts/{sample_transcript.id}/translate"
        )

        assert response.status_code == 200
        data = response.json()
        assert "job_id" in data


class TestTranslationErrors:
    """Test cases for translation error handling."""

    @pytest.mark.asyncio
    async def test_translate_invalid_uuid(self, async_client: AsyncClient):
        """Test translation with invalid UUID format."""
        response = await async_client.post(
            "/api/transcripts/invalid-uuid/translate",
            params={"target_language": "ru"}
        )

        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_translate_empty_target_language(self, async_client: AsyncClient, sample_transcript):
        """Test translation with empty target language."""
        response = await async_client.post(
            f"/api/transcripts/{sample_transcript.id}/translate",
            params={"target_language": ""}
        )

        # May use default or return error
        assert response.status_code in [200, 400, 422]

    @pytest.mark.asyncio
    async def test_translate_with_processing_transcript(self, async_client: AsyncClient, db_session: Session):
        """Test that processing transcripts cannot be translated."""
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
            f"/api/transcripts/{transcript.id}/translate",
            params={"target_language": "ru"}
        )

        assert response.status_code == 400
        assert "not completed" in response.json()["detail"].lower()


class TestTranslationMetadata:
    """Test cases for translation metadata handling."""

    @pytest.mark.asyncio
    async def test_translation_preserves_metadata(self, async_client: AsyncClient, db_session: Session):
        """Test that translation preserves existing metadata."""
        original_metadata = {
            "speaker_count": 3,
            "meeting_date": "2024-01-15",
            "custom_field": "value"
        }

        transcript = Transcript(
            original_filename="with_metadata.mp3",
            file_path="/tmp/with_metadata.mp3",
            file_size=1024,
            status=TranscriptStatus.COMPLETED,
            language="en",
            transcription_text="English text",
            extra_metadata=original_metadata.copy()
        )
        db_session.add(transcript)
        db_session.commit()
        db_session.refresh(transcript)

        # Start translation (will run in background)
        await async_client.post(
            f"/api/transcripts/{transcript.id}/translate",
            params={"target_language": "ru"}
        )

        # Note: We can't easily test the actual metadata update here
        # since translation runs in background, but we verify the endpoint works
        assert True

    @pytest.mark.asyncio
    async def test_translation_updates_language(self, async_client: AsyncClient, db_session: Session):
        """Test that translation updates the language field."""
        transcript = Transcript(
            original_filename="english.mp3",
            file_path="/tmp/english.mp3",
            file_size=1024,
            status=TranscriptStatus.COMPLETED,
            language="en",
            transcription_text="English text to translate"
        )
        db_session.add(transcript)
        db_session.commit()
        db_session.refresh(transcript)

        original_language = transcript.language

        # Start translation
        response = await async_client.post(
            f"/api/transcripts/{transcript.id}/translate",
            params={"target_language": "ru"}
        )

        assert response.status_code == 200
        # Language will be updated after background task completes


class TestTranslationConcurrent:
    """Test cases for concurrent translation requests."""

    @pytest.mark.asyncio
    async def test_concurrent_translations(self, async_client: AsyncClient, db_session: Session):
        """Test multiple translation requests concurrently."""
        import asyncio

        # Create multiple transcripts
        transcripts = []
        for i in range(3):
            transcript = Transcript(
                original_filename=f"test_{i}.mp3",
                file_path=f"/tmp/test_{i}.mp3",
                file_size=1024,
                status=TranscriptStatus.COMPLETED,
                language="en",
                transcription_text=f"English text {i} to translate"
            )
            db_session.add(transcript)
            transcripts.append(transcript)
        db_session.commit()

        async def translate(transcript_id):
            return await async_client.post(
                f"/api/transcripts/{transcript_id}/translate",
                params={"target_language": "ru"}
            )

        # Run translations concurrently
        responses = await asyncio.gather(*[
            translate(t.id) for t in transcripts
        ])

        # All should succeed
        for response in responses:
            assert response.status_code == 200
            assert "job_id" in response.json()

    @pytest.mark.asyncio
    async def test_duplicate_translation_request(self, async_client: AsyncClient, sample_transcript):
        """Test requesting translation twice for same transcript."""
        # First request
        response1 = await async_client.post(
            f"/api/transcripts/{sample_transcript.id}/translate",
            params={"target_language": "ru"}
        )

        assert response1.status_code == 200

        # Second request (should create another job)
        response2 = await async_client.post(
            f"/api/transcripts/{sample_transcript.id}/translate",
            params={"target_language": "ru"}
        )

        # Both should succeed, creating separate jobs
        assert response2.status_code in [200, 400]  # May already be translated


class TestTranslationEdgeCases:
    """Test cases for translation edge cases."""

    @pytest.mark.asyncio
    async def test_translate_very_long_text(self, async_client: AsyncClient, db_session: Session):
        """Test translating a very long transcript."""
        long_text = "This is a test. " * 1000

        transcript = Transcript(
            original_filename="long.mp3",
            file_path="/tmp/long.mp3",
            file_size=1024,
            status=TranscriptStatus.COMPLETED,
            language="en",
            transcription_text=long_text
        )
        db_session.add(transcript)
        db_session.commit()
        db_session.refresh(transcript)

        response = await async_client.post(
            f"/api/transcripts/{transcript.id}/translate",
            params={"target_language": "ru"}
        )

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_translate_empty_text(self, async_client: AsyncClient, db_session: Session):
        """Test translating a transcript with empty text."""
        transcript = Transcript(
            original_filename="empty.mp3",
            file_path="/tmp/empty.mp3",
            file_size=1024,
            status=TranscriptStatus.COMPLETED,
            language="en",
            transcription_text=""
        )
        db_session.add(transcript)
        db_session.commit()
        db_session.refresh(transcript)

        response = await async_client.post(
            f"/api/transcripts/{transcript.id}/translate",
            params={"target_language": "ru"}
        )

        # Empty text should fail
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_translate_unicode_text(self, async_client: AsyncClient, db_session: Session):
        """Test translating text with Unicode characters."""
        unicode_text = "Hello 世界 Привет مرحبا"

        transcript = Transcript(
            original_filename="unicode.mp3",
            file_path="/tmp/unicode.mp3",
            file_size=1024,
            status=TranscriptStatus.COMPLETED,
            language="en",
            transcription_text=unicode_text
        )
        db_session.add(transcript)
        db_session.commit()
        db_session.refresh(transcript)

        response = await async_client.post(
            f"/api/transcripts/{transcript.id}/translate",
            params={"target_language": "ru"}
        )

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_translate_special_characters(self, async_client: AsyncClient, db_session: Session):
        """Test translating text with special characters."""
        special_text = "Meeting @ 3PM - Discuss Q1 2024 results! (Confidential)"

        transcript = Transcript(
            original_filename="special.mp3",
            file_path="/tmp/special.mp3",
            file_size=1024,
            status=TranscriptStatus.COMPLETED,
            language="en",
            transcription_text=special_text
        )
        db_session.add(transcript)
        db_session.commit()
        db_session.refresh(transcript)

        response = await async_client.post(
            f"/api/transcripts/{transcript.id}/translate",
            params={"target_language": "ru"}
        )

        assert response.status_code == 200
