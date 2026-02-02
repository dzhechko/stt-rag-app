"""
Unit tests for Pydantic models.

Tests model validation, serialization, and schema generation.
"""
import pytest
from uuid import uuid4
from datetime import datetime
from pydantic import ValidationError

from app.models import (
    TranscriptResponse,
    TranscriptListResponse,
    TranscriptCreate,
    TranscriptUpdate,
    SummaryCreate,
    SummaryResponse,
    RAGSessionCreate,
    RAGSessionResponse,
    RAGQuestionRequest,
    RAGAnswerResponse,
    RAGFeedbackRequest,
    ProcessingJobResponse
)


class TestTranscriptModels:
    """Test cases for transcript-related models."""

    def test_transcript_create_valid(self):
        """Test creating a valid TranscriptCreate model."""
        data = {
            "original_filename": "test.mp3",
            "language": "en"
        }
        model = TranscriptCreate(**data)

        assert model.original_filename == "test.mp3"
        assert model.language == "en"

    def test_transcript_create_without_language(self):
        """Test TranscriptCreate without language (auto-detect)."""
        data = {
            "original_filename": "test.mp3"
        }
        model = TranscriptCreate(**data)

        assert model.original_filename == "test.mp3"
        assert model.language is None

    def test_transcript_response_from_dict(self):
        """Test creating TranscriptResponse from dictionary."""
        data = {
            "id": uuid4(),
            "original_filename": "test.mp3",
            "file_path": "/tmp/test.mp3",
            "file_size": 1024,
            "duration_seconds": 120.5,
            "language": "en",
            "status": "completed",
            "transcription_text": "Sample text",
            "transcription_json": {},
            "transcription_srt": None,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "extra_metadata": {"key": "value"},
            "tags": ["test", "sample"],
            "category": "meeting"
        }

        model = TranscriptResponse(**data)

        assert model.original_filename == "test.mp3"
        assert model.language == "en"
        assert model.status == "completed"
        assert model.tags == ["test", "sample"]
        assert model.category == "meeting"

    def test_transcript_update_partial(self):
        """Test TranscriptUpdate with partial data."""
        data = {
            "transcription_text": "Updated text"
        }
        model = TranscriptUpdate(**data)

        assert model.transcription_text == "Updated text"
        assert model.tags is None
        assert model.category is None

    def test_transcript_update_all_fields(self):
        """Test TranscriptUpdate with all fields."""
        data = {
            "transcription_text": "Updated",
            "tags": ["updated"],
            "category": "lecture",
            "extra_metadata": {"new": "data"}
        }
        model = TranscriptUpdate(**data)

        assert model.transcription_text == "Updated"
        assert model.tags == ["updated"]
        assert model.category == "lecture"
        assert model.extra_metadata == {"new": "data"}

    def test_transcript_list_response(self):
        """Test TranscriptListResponse structure."""
        transcript_data = {
            "id": uuid4(),
            "original_filename": "test.mp3",
            "file_path": "/tmp/test.mp3",
            "file_size": 1024,
            "duration_seconds": None,
            "language": "en",
            "status": "pending",
            "transcription_text": None,
            "transcription_json": None,
            "transcription_srt": None,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "extra_metadata": None,
            "tags": None,
            "category": None
        }

        data = {
            "transcripts": [transcript_data],
            "total": 1
        }

        model = TranscriptListResponse(**data)

        assert len(model.transcripts) == 1
        assert model.total == 1


class TestSummaryModels:
    """Test cases for summary-related models."""

    def test_summary_create_minimal(self):
        """Test SummaryCreate with minimal data."""
        data = {
            "transcript_id": uuid4()
        }
        model = SummaryCreate(**data)

        assert model.transcript_id == data["transcript_id"]
        assert model.template is None
        assert model.custom_prompt is None

    def test_summary_create_full(self):
        """Test SummaryCreate with all parameters."""
        data = {
            "transcript_id": uuid4(),
            "template": "meeting",
            "custom_prompt": "Summarize key decisions",
            "fields_config": {
                "participants": True,
                "decisions": True,
                "deadlines": False
            },
            "model": "GigaChat-2-Max"
        }
        model = SummaryCreate(**data)

        assert model.template == "meeting"
        assert model.fields_config["participants"] is True
        assert model.model == "GigaChat-2-Max"

    def test_summary_response(self):
        """Test SummaryResponse structure."""
        data = {
            "id": uuid4(),
            "transcript_id": uuid4(),
            "summary_text": "This is a summary",
            "summary_template": "meeting",
            "summary_config": {"participants": True},
            "model_used": "GigaChat-2-Max",
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }

        model = SummaryResponse(**data)

        assert model.summary_text == "This is a summary"
        assert model.summary_template == "meeting"
        assert model.model_used == "GigaChat-2-Max"


class TestRAGModels:
    """Test cases for RAG-related models."""

    def test_rag_session_create_minimal(self):
        """Test RAGSessionCreate with minimal data."""
        data = {}
        model = RAGSessionCreate(**data)

        assert model.session_name is None
        assert model.transcript_ids is None

    def test_rag_session_create_full(self):
        """Test RAGSessionCreate with all parameters."""
        data = {
            "session_name": "Test Session",
            "transcript_ids": ["uuid1", "uuid2", "uuid3"]
        }
        model = RAGSessionCreate(**data)

        assert model.session_name == "Test Session"
        assert len(model.transcript_ids) == 3

    def test_rag_question_request_minimal(self):
        """Test RAGQuestionRequest with minimal data."""
        data = {
            "question": "What is discussed?"
        }
        model = RAGQuestionRequest(**data)

        assert model.question == "What is discussed?"
        assert model.transcript_ids is None
        assert model.top_k is None

    def test_rag_question_request_full(self):
        """Test RAGQuestionRequest with all parameters."""
        data = {
            "question": "Summarize the meeting",
            "transcript_ids": ["uuid1"],
            "top_k": 10,
            "model": "GigaChat-2-Max",
            "temperature": 0.5,
            "use_reranking": True,
            "use_query_expansion": False,
            "use_multi_hop": True,
            "use_hybrid_search": True,
            "use_advanced_grading": False,
            "reranker_model": "ms-marco-MiniLM-L-6-v2"
        }
        model = RAGQuestionRequest(**data)

        assert model.question == "Summarize the meeting"
        assert model.top_k == 10
        assert model.temperature == 0.5
        assert model.use_multi_hop is True
        assert model.use_hybrid_search is True

    def test_rag_answer_response(self):
        """Test RAGAnswerResponse structure."""
        data = {
            "answer": "The meeting discussed project planning.",
            "sources": [
                {"transcript_id": "uuid1", "content": "...", "score": 0.9}
            ],
            "quality_score": 0.85,
            "retrieved_chunks": [
                {"text": "...", "metadata": {}}
            ]
        }

        model = RAGAnswerResponse(**data)

        assert model.answer == "The meeting discussed project planning."
        assert len(model.sources) == 1
        assert model.quality_score == 0.85
        assert model.message_id is None

    def test_rag_feedback_request_positive(self):
        """Test RAGFeedbackRequest with positive feedback."""
        data = {
            "feedback_type": "positive",
            "comment": "Very helpful"
        }
        model = RAGFeedbackRequest(**data)

        assert model.feedback_type == "positive"
        assert model.comment == "Very helpful"

    def test_rag_feedback_request_negative(self):
        """Test RAGFeedbackRequest with negative feedback."""
        data = {
            "feedback_type": "negative",
            "comment": "Not accurate"
        }
        model = RAGFeedbackRequest(**data)

        assert model.feedback_type == "negative"

    def test_rag_feedback_request_no_comment(self):
        """Test RAGFeedbackRequest without comment."""
        data = {
            "feedback_type": "positive"
        }
        model = RAGFeedbackRequest(**data)

        assert model.feedback_type == "positive"
        assert model.comment is None


class TestValidation:
    """Test model validation edge cases."""

    def test_invalid_uuid_raises_error(self):
        """Test that invalid UUID raises ValidationError."""
        data = {
            "id": "not-a-uuid",
            "original_filename": "test.mp3",
            "file_path": "/tmp/test.mp3",
            "file_size": 1024,
            "language": "en",
            "status": "completed",
            "transcription_text": "Text",
            "transcription_json": None,
            "transcription_srt": None,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "extra_metadata": None,
            "tags": None,
            "category": None
        }

        with pytest.raises(ValidationError):
            TranscriptResponse(**data)

    def test_empty_tags_list(self):
        """Test model with empty tags list."""
        data = {
            "id": uuid4(),
            "original_filename": "test.mp3",
            "file_path": "/tmp/test.mp3",
            "file_size": 1024,
            "language": "en",
            "status": "completed",
            "transcription_text": "Text",
            "transcription_json": None,
            "transcription_srt": None,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "extra_metadata": None,
            "tags": [],
            "category": None
        }

        model = TranscriptResponse(**data)
        assert model.tags == []

    def test_none_optional_fields(self):
        """Test model with all optional fields as None."""
        data = {
            "id": uuid4(),
            "original_filename": "test.mp3",
            "file_path": "/tmp/test.mp3",
            "file_size": 1024,
            "duration_seconds": None,
            "language": None,
            "status": "pending",
            "transcription_text": None,
            "transcription_json": None,
            "transcription_srt": None,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "extra_metadata": None,
            "tags": None,
            "category": None
        }

        model = TranscriptResponse(**data)
        assert model.duration_seconds is None
        assert model.language is None

    def test_complex_metadata(self):
        """Test model with complex nested metadata."""
        complex_metadata = {
            "nested": {
                "level1": {
                    "level2": {
                        "value": "deep"
                    }
                }
            },
            "array": [1, 2, 3],
            "mixed": [
                {"key": "value"},
                ["nested", "array"]
            ]
        }

        data = {
            "id": uuid4(),
            "original_filename": "test.mp3",
            "file_path": "/tmp/test.mp3",
            "file_size": 1024,
            "language": "en",
            "status": "completed",
            "transcription_text": "Text",
            "transcription_json": None,
            "transcription_srt": None,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "extra_metadata": complex_metadata,
            "tags": None,
            "category": None
        }

        model = TranscriptResponse(**data)
        assert model.extra_metadata == complex_metadata
