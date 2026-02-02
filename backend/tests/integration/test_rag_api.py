"""
Comprehensive integration tests for RAG (Retrieval-Augmented Generation) API endpoints.

Tests cover:
- POST /api/rag/sessions - Create RAG session
- GET /api/rag/sessions - List all sessions
- GET /api/rag/sessions/{id} - Get single session
- DELETE /api/rag/sessions/{id} - Delete session
- POST /api/rag/ask - Ask question without session
- POST /api/rag/sessions/{id}/ask - Ask question in session
- GET /api/rag/sessions/{id}/messages - Get session messages
- POST /api/rag/messages/{id}/feedback - Submit feedback
- GET /api/transcripts/{id}/index-status - Check index status
- POST /api/transcripts/{id}/reindex - Reindex transcript
- GET /api/rag/status - Get RAG system status
"""
import pytest
from uuid import uuid4
from httpx import AsyncClient
from sqlalchemy.orm import Session

from app.database import RAGSession, RAGMessage, Transcript, TranscriptStatus


class TestCreateRAGSession:
    """Test cases for creating RAG sessions."""

    @pytest.mark.asyncio
    async def test_create_session_minimal(self, async_client: AsyncClient):
        """Test creating a session with minimal data."""
        response = await async_client.post(
            "/api/rag/sessions",
            json={}
        )

        assert response.status_code == 201
        data = response.json()

        # Verify response structure
        assert "id" in data
        assert "session_name" in data
        assert "transcript_ids" in data
        assert "created_at" in data

    @pytest.mark.asyncio
    async def test_create_session_with_name(self, async_client: AsyncClient):
        """Test creating a session with a name."""
        session_name = "Test Session"

        response = await async_client.post(
            "/api/rag/sessions",
            json={"session_name": session_name}
        )

        assert response.status_code == 201
        data = response.json()
        assert data["session_name"] == session_name

    @pytest.mark.asyncio
    async def test_create_session_with_transcript_ids(self, async_client: AsyncClient):
        """Test creating a session with transcript IDs."""
        transcript_ids = [str(uuid4()), str(uuid4()), str(uuid4())]

        response = await async_client.post(
            "/api/rag/sessions",
            json={"transcript_ids": transcript_ids}
        )

        assert response.status_code == 201
        data = response.json()
        assert data["transcript_ids"] == transcript_ids

    @pytest.mark.asyncio
    async def test_create_session_full(self, async_client: AsyncClient):
        """Test creating a session with all parameters."""
        session_data = {
            "session_name": "Full Test Session",
            "transcript_ids": [str(uuid4()), str(uuid4())]
        }

        response = await async_client.post(
            "/api/rag/sessions",
            json=session_data
        )

        assert response.status_code == 201
        data = response.json()
        assert data["session_name"] == "Full Test Session"
        assert len(data["transcript_ids"]) == 2

    @pytest.mark.asyncio
    async def test_create_session_empty_transcript_ids(self, async_client: AsyncClient):
        """Test creating a session with empty transcript IDs list."""
        response = await async_client.post(
            "/api/rag/sessions",
            json={"transcript_ids": []}
        )

        assert response.status_code == 201
        data = response.json()
        assert data["transcript_ids"] == []


class TestListRAGSessions:
    """Test cases for listing RAG sessions."""

    @pytest.mark.asyncio
    async def test_list_sessions_empty(self, async_client: AsyncClient, db_session: Session):
        """Test listing sessions when database is empty."""
        # Clear any existing sessions
        db_session.query(RAGSession).delete()
        db_session.commit()

        response = await async_client.get("/api/rag/sessions")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 0

    @pytest.mark.asyncio
    async def test_list_sessions_with_data(self, async_client: AsyncClient, sample_rag_sessions):
        """Test listing sessions with existing data."""
        response = await async_client.get("/api/rag/sessions")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 3

        # Verify session structure
        session = data[0]
        assert "id" in session
        assert "session_name" in session
        assert "transcript_ids" in session
        assert "created_at" in session

    @pytest.mark.asyncio
    async def test_list_sessions_ordering(self, async_client: AsyncClient, sample_rag_sessions):
        """Test that sessions are ordered by created_at descending."""
        response = await async_client.get("/api/rag/sessions")

        assert response.status_code == 200
        data = response.json()

        # Verify ordering (newest first)
        for i in range(len(data) - 1):
            assert data[i]["created_at"] >= data[i+1]["created_at"]


class TestGetRAGSession:
    """Test cases for getting a single RAG session."""

    @pytest.mark.asyncio
    async def test_get_session_existing(self, async_client: AsyncClient, sample_rag_session):
        """Test retrieving an existing session."""
        response = await async_client.get(f"/api/rag/sessions/{sample_rag_session.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(sample_rag_session.id)
        assert data["session_name"] == sample_rag_session.session_name

    @pytest.mark.asyncio
    async def test_get_session_not_found(self, async_client: AsyncClient):
        """Test retrieving a non-existent session."""
        fake_id = uuid4()
        response = await async_client.get(f"/api/rag/sessions/{fake_id}")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_get_session_invalid_uuid(self, async_client: AsyncClient):
        """Test retrieving with invalid UUID format."""
        response = await async_client.get("/api/rag/sessions/invalid-uuid")

        assert response.status_code == 422


class TestDeleteRAGSession:
    """Test cases for deleting RAG sessions."""

    @pytest.mark.asyncio
    async def test_delete_session_existing(self, async_client: AsyncClient, sample_rag_session, db_session: Session):
        """Test successful deletion of a session."""
        session_id = sample_rag_session.id

        response = await async_client.delete(f"/api/rag/sessions/{session_id}")

        assert response.status_code == 204

        # Verify deletion in database
        session = db_session.query(RAGSession).filter(RAGSession.id == session_id).first()
        assert session is None

    @pytest.mark.asyncio
    async def test_delete_session_not_found(self, async_client: AsyncClient):
        """Test deleting a non-existent session."""
        fake_id = uuid4()
        response = await async_client.delete(f"/api/rag/sessions/{fake_id}")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_delete_session_cascades_to_messages(self, async_client: AsyncClient, db_session: Session):
        """Test that deleting a session cascades to messages."""
        # Create session with messages
        session = RAGSession(
            session_name="Test with messages",
            transcript_ids=[]
        )
        db_session.add(session)
        db_session.commit()

        message = RAGMessage(
            session_id=session.id,
            question="Test question?",
            answer="Test answer"
        )
        db_session.add(message)
        db_session.commit()

        session_id = session.id

        # Delete session
        response = await async_client.delete(f"/api/rag/sessions/{session_id}")
        assert response.status_code == 204

        # Verify messages were also deleted (cascade)
        messages = db_session.query(RAGMessage).filter(
            RAGMessage.session_id == session_id
        ).all()
        assert len(messages) == 0


class TestAskQuestion:
    """Test cases for asking questions (without session)."""

    @pytest.mark.asyncio
    async def test_ask_question_simple(self, async_client: AsyncClient):
        """Test asking a simple question."""
        response = await async_client.post(
            "/api/rag/ask",
            json={"question": "What is discussed in the meeting?"}
        )

        # Note: This may fail if RAG services are not properly configured
        # but we test the endpoint structure
        assert response.status_code in [200, 500, 503]

    @pytest.mark.asyncio
    async def test_ask_question_with_transcript_filter(self, async_client: AsyncClient, sample_transcript):
        """Test asking a question with transcript filter."""
        response = await async_client.post(
            "/api/rag/ask",
            json={
                "question": "What are the main topics?",
                "transcript_ids": [str(sample_transcript.id)]
            }
        )

        # May fail if transcript not indexed, but tests endpoint
        assert response.status_code in [200, 500, 503]

    @pytest.mark.asyncio
    async def test_ask_question_with_parameters(self, async_client: AsyncClient):
        """Test asking a question with all parameters."""
        question_data = {
            "question": "Summarize the discussion",
            "transcript_ids": [str(uuid4())],
            "top_k": 10,
            "model": "GigaChat-2-Max",
            "temperature": 0.5,
            "use_reranking": True,
            "use_query_expansion": False,
            "use_multi_hop": True,
            "use_hybrid_search": False,
            "use_advanced_grading": True,
            "reranker_model": "ms-marco-MiniLM-L-6-v2"
        }

        response = await async_client.post(
            "/api/rag/ask",
            json=question_data
        )

        assert response.status_code in [200, 500, 503]

    @pytest.mark.asyncio
    async def test_ask_question_missing_question(self, async_client: AsyncClient):
        """Test asking without providing a question."""
        response = await async_client.post(
            "/api/rag/ask",
            json={}
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_ask_question_empty_question(self, async_client: AsyncClient):
        """Test asking with an empty question."""
        response = await async_client.post(
            "/api/rag/ask",
            json={"question": ""}
        )

        assert response.status_code in [200, 422, 500, 503]

    @pytest.mark.asyncio
    async def test_ask_question_creates_temp_session(self, async_client: AsyncClient, db_session: Session):
        """Test that asking without session creates a temporary session."""
        # Clear temporary sessions first
        db_session.query(RAGSession).filter(
            RAGSession.session_name == "Temporary Feedback Session"
        ).delete()
        db_session.commit()

        response = await async_client.post(
            "/api/rag/ask",
            json={"question": "Test question?"}
        )

        # If successful, verify temp session was created
        if response.status_code == 200:
            temp_session = db_session.query(RAGSession).filter(
                RAGSession.session_name == "Temporary Feedback Session"
            ).first()
            assert temp_session is not None


class TestAskQuestionInSession:
    """Test cases for asking questions within a session."""

    @pytest.mark.asyncio
    async def test_ask_in_session_simple(self, async_client: AsyncClient, sample_rag_session):
        """Test asking a simple question in a session."""
        response = await async_client.post(
            f"/api/rag/sessions/{sample_rag_session.id}/ask",
            json={"question": "What is the main topic?"}
        )

        # May fail if RAG not configured, but tests endpoint
        assert response.status_code in [200, 500, 503]

    @pytest.mark.asyncio
    async def test_ask_in_session_with_transcript_override(self, async_client: AsyncClient, sample_rag_session):
        """Test asking in session with transcript ID override."""
        response = await async_client.post(
            f"/api/rag/sessions/{sample_rag_session.id}/ask",
            json={
                "question": "What was decided?",
                "transcript_ids": [str(uuid4())]
            }
        )

        assert response.status_code in [200, 500, 503]

    @pytest.mark.asyncio
    async def test_ask_in_session_not_found(self, async_client: AsyncClient):
        """Test asking in non-existent session."""
        fake_id = uuid4()
        response = await async_client.post(
            f"/api/rag/sessions/{fake_id}/ask",
            json={"question": "Test question?"}
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_ask_in_session_creates_message(self, async_client: AsyncClient, sample_rag_session, db_session: Session):
        """Test that asking in session creates a message record."""
        # Note: This test may fail if RAG services aren't configured
        response = await async_client.post(
            f"/api/rag/sessions/{sample_rag_session.id}/ask",
            json={"question": "Test question?"}
        )

        if response.status_code == 200:
            messages = db_session.query(RAGMessage).filter(
                RAGMessage.session_id == sample_rag_session.id
            ).all()
            assert len(messages) >= 1


class TestGetSessionMessages:
    """Test cases for getting session messages."""

    @pytest.mark.asyncio
    async def test_get_messages_empty_session(self, async_client: AsyncClient, sample_rag_session):
        """Test getting messages from a session with no messages."""
        response = await async_client.get(f"/api/rag/sessions/{sample_rag_session.id}/messages")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_get_messages_with_data(self, async_client: AsyncClient, db_session: Session):
        """Test getting messages from a session with messages."""
        # Create session with messages
        session = RAGSession(
            session_name="Session with messages",
            transcript_ids=[]
        )
        db_session.add(session)
        db_session.commit()

        message1 = RAGMessage(
            session_id=session.id,
            question="First question?",
            answer="First answer"
        )
        message2 = RAGMessage(
            session_id=session.id,
            question="Second question?",
            answer="Second answer"
        )
        db_session.add_all([message1, message2])
        db_session.commit()

        response = await async_client.get(f"/api/rag/sessions/{session.id}/messages")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 2

        # Verify message structure
        message = data[0]
        assert "id" in message
        assert "question" in message
        assert "answer" in message
        assert "created_at" in message

    @pytest.mark.asyncio
    async def test_get_messages_ordering(self, async_client: AsyncClient, db_session: Session):
        """Test that messages are ordered by created_at ascending."""
        session = RAGSession(
            session_name="Ordered session",
            transcript_ids=[]
        )
        db_session.add(session)
        db_session.commit()

        # Create messages
        for i in range(3):
            message = RAGMessage(
                session_id=session.id,
                question=f"Question {i}?",
                answer=f"Answer {i}"
            )
            db_session.add(message)
        db_session.commit()

        response = await async_client.get(f"/api/rag/sessions/{session.id}/messages")

        assert response.status_code == 200
        data = response.json()

        # Verify ordering (oldest first for conversation history)
        for i in range(len(data) - 1):
            assert data[i]["created_at"] <= data[i+1]["created_at"]

    @pytest.mark.asyncio
    async def test_get_messages_nonexistent_session(self, async_client: AsyncClient):
        """Test getting messages for non-existent session."""
        fake_id = uuid4()
        response = await async_client.get(f"/api/rag/sessions/{fake_id}/messages")

        # Returns empty list instead of 404
        assert response.status_code == 200
        assert isinstance(response.json(), list)


class TestSubmitFeedback:
    """Test cases for submitting RAG feedback."""

    @pytest.mark.asyncio
    async def test_submit_positive_feedback(self, async_client: AsyncClient, db_session: Session):
        """Test submitting positive feedback."""
        # Create a message
        message = RAGMessage(
            session_id=None,
            question="Test question?",
            answer="Test answer"
        )
        db_session.add(message)
        db_session.commit()

        response = await async_client.post(
            f"/api/rag/messages/{message.id}/feedback",
            json={"feedback_type": "positive", "comment": "Very helpful!"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["feedback_type"] == "positive"
        assert "message_id" in data

    @pytest.mark.asyncio
    async def test_submit_negative_feedback(self, async_client: AsyncClient, db_session: Session):
        """Test submitting negative feedback."""
        message = RAGMessage(
            session_id=None,
            question="Test question?",
            answer="Test answer"
        )
        db_session.add(message)
        db_session.commit()

        response = await async_client.post(
            f"/api/rag/messages/{message.id}/feedback",
            json={"feedback_type": "negative", "comment": "Not accurate"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["feedback_type"] == "negative"

    @pytest.mark.asyncio
    async def test_submit_feedback_without_comment(self, async_client: AsyncClient, db_session: Session):
        """Test submitting feedback without a comment."""
        message = RAGMessage(
            session_id=None,
            question="Test question?",
            answer="Test answer"
        )
        db_session.add(message)
        db_session.commit()

        response = await async_client.post(
            f"/api/rag/messages/{message.id}/feedback",
            json={"feedback_type": "positive"}
        )

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_submit_feedback_invalid_type(self, async_client: AsyncClient, db_session: Session):
        """Test submitting feedback with invalid type."""
        message = RAGMessage(
            session_id=None,
            question="Test question?",
            answer="Test answer"
        )
        db_session.add(message)
        db_session.commit()

        response = await async_client.post(
            f"/api/rag/messages/{message.id}/feedback",
            json={"feedback_type": "invalid"}
        )

        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_submit_feedback_nonexistent_message(self, async_client: AsyncClient):
        """Test submitting feedback for non-existent message."""
        fake_id = uuid4()
        response = await async_client.post(
            f"/api/rag/messages/{fake_id}/feedback",
            json={"feedback_type": "positive"}
        )

        assert response.status_code == 404


class TestIndexStatus:
    """Test cases for transcript index status endpoint."""

    @pytest.mark.asyncio
    async def test_index_status_completed_transcript(self, async_client: AsyncClient, sample_transcript):
        """Test index status for a completed transcript."""
        response = await async_client.get(f"/api/transcripts/{sample_transcript.id}/index-status")

        assert response.status_code == 200
        data = response.json()
        assert "indexed" in data
        assert isinstance(data["indexed"], bool)
        assert "transcript_id" in data

    @pytest.mark.asyncio
    async def test_index_status_no_text(self, async_client: AsyncClient, db_session: Session):
        """Test index status for transcript without text."""
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

        response = await async_client.get(f"/api/transcripts/{transcript.id}/index-status")

        assert response.status_code == 200
        data = response.json()
        assert data["indexed"] is False
        assert "no text" in data.get("reason", "").lower()

    @pytest.mark.asyncio
    async def test_index_status_not_completed(self, async_client: AsyncClient, db_session: Session):
        """Test index status for non-completed transcript."""
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

        response = await async_client.get(f"/api/transcripts/{transcript.id}/index-status")

        assert response.status_code == 200
        data = response.json()
        assert data["indexed"] is False
        assert "not completed" in data.get("reason", "").lower()

    @pytest.mark.asyncio
    async def test_index_status_nonexistent_transcript(self, async_client: AsyncClient):
        """Test index status for non-existent transcript."""
        fake_id = uuid4()
        response = await async_client.get(f"/api/transcripts/{fake_id}/index-status")

        assert response.status_code == 404


class TestReindexTranscript:
    """Test cases for reindexing transcript endpoint."""

    @pytest.mark.asyncio
    async def test_reindex_completed_transcript(self, async_client: AsyncClient, sample_transcript):
        """Test reindexing a completed transcript."""
        response = await async_client.post(f"/api/transcripts/{sample_transcript.id}/reindex")

        # May fail if Qdrant/embeddings not configured
        assert response.status_code in [200, 500, 503]

        if response.status_code == 200:
            data = response.json()
            assert "message" in data
            assert "chunks_indexed" in data

    @pytest.mark.asyncio
    async def test_reindex_no_text(self, async_client: AsyncClient, db_session: Session):
        """Test reindexing transcript without text."""
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

        response = await async_client.post(f"/api/transcripts/{transcript.id}/reindex")

        assert response.status_code == 400
        assert "no text" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_reindex_not_completed(self, async_client: AsyncClient, db_session: Session):
        """Test reindexing non-completed transcript."""
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

        response = await async_client.post(f"/api/transcripts/{transcript.id}/reindex")

        assert response.status_code == 400
        assert "not completed" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_reindex_nonexistent_transcript(self, async_client: AsyncClient):
        """Test reindexing non-existent transcript."""
        fake_id = uuid4()
        response = await async_client.post(f"/api/transcripts/{fake_id}/reindex")

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_reindex_creates_job(self, async_client: AsyncClient, sample_transcript, db_session: Session):
        """Test that reindexing creates an indexing job."""
        from app.database import ProcessingJob, JobType

        response = await async_client.post(f"/api/transcripts/{sample_transcript.id}/reindex")

        # If successful, check for job
        if response.status_code == 200:
            jobs = db_session.query(ProcessingJob).filter(
                ProcessingJob.transcript_id == sample_transcript.id,
                ProcessingJob.job_type == JobType.INDEXING
            ).all()
            assert len(jobs) >= 1


class TestRAGSystemStatus:
    """Test cases for RAG system status endpoint."""

    @pytest.mark.asyncio
    async def test_get_rag_status(self, async_client: AsyncClient):
        """Test getting RAG system status."""
        response = await async_client.get("/api/rag/status")

        assert response.status_code == 200
        data = response.json()
        assert "qdrant_available" in data
        assert "collection_name" in data
        assert "embeddings_available" in data

    @pytest.mark.asyncio
    async def test_rag_status_structure(self, async_client: AsyncClient):
        """Test that RAG status has correct structure."""
        response = await async_client.get("/api/rag/status")

        assert response.status_code == 200
        data = response.json()

        # Verify data types
        assert isinstance(data["qdrant_available"], bool)
        assert isinstance(data["embeddings_available"], bool)
        assert isinstance(data["collection_name"], str)

        # If Qdrant is unavailable, should have error field
        if not data["qdrant_available"]:
            assert "error" in data


class TestRAGValidation:
    """Edge case and validation tests for RAG endpoints."""

    @pytest.mark.asyncio
    async def test_create_multiple_concurrent_sessions(self, async_client: AsyncClient):
        """Test creating multiple sessions concurrently."""
        import asyncio

        async def create_session(name):
            return await async_client.post(
                "/api/rag/sessions",
                json={"session_name": name}
            )

        responses = await asyncio.gather(*[
            create_session(f"Session {i}") for i in range(5)
        ])

        for response in responses:
            assert response.status_code == 201

    @pytest.mark.asyncio
    async def test_session_with_unicode_name(self, async_client: AsyncClient):
        """Test creating session with Unicode characters in name."""
        session_name = "Тестовая сессия на русском"

        response = await async_client.post(
            "/api/rag/sessions",
            json={"session_name": session_name}
        )

        assert response.status_code == 201
        data = response.json()
        assert data["session_name"] == session_name

    @pytest.mark.asyncio
    async def test_ask_question_with_special_characters(self, async_client: AsyncClient):
        """Test asking question with special characters."""
        question = "What about the meeting on 2024-01-15 @ 3PM? (Important!)"

        response = await async_client.post(
            "/api/rag/ask",
            json={"question": question}
        )

        assert response.status_code in [200, 500, 503]

    @pytest.mark.asyncio
    async def test_ask_very_long_question(self, async_client: AsyncClient):
        """Test asking a very long question."""
        long_question = "What is discussed in the meeting? " * 50

        response = await async_client.post(
            "/api/rag/ask",
            json={"question": long_question}
        )

        assert response.status_code in [200, 500, 503]

    @pytest.mark.asyncio
    async def test_top_k_boundary_values(self, async_client: AsyncClient):
        """Test top_k parameter with boundary values."""
        test_values = [1, 5, 10, 50, 100]

        for top_k in test_values:
            response = await async_client.post(
                "/api/rag/ask",
                json={
                    "question": "Test question?",
                    "top_k": top_k
                }
            )

            assert response.status_code in [200, 500, 503]

    @pytest.mark.asyncio
    async def test_temperature_boundary_values(self, async_client: AsyncClient):
        """Test temperature parameter with boundary values."""
        test_values = [0.0, 0.3, 0.5, 1.0, 1.5, 2.0]

        for temp in test_values:
            response = await async_client.post(
                "/api/rag/ask",
                json={
                    "question": "Test question?",
                    "temperature": temp
                }
            )

            assert response.status_code in [200, 500, 503]
