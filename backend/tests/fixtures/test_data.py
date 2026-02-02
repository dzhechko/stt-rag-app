"""
Test data generators and factory functions for STT backend testing.

This module provides reusable factory functions for creating test data,
including transcripts, summaries, RAG sessions, and API payloads.
All generators are designed to be flexible and customizable.
"""

import random
import string
from typing import Dict, Any, List, Optional, Union
from datetime import datetime, timedelta
from uuid import uuid4
import json


# =============================================================================
# Random Data Generators
# =============================================================================

def random_string(length: int = 10, prefix: str = "") -> str:
    """
    Generate a random string for testing.

    Args:
        length: Length of the random string (excluding prefix)
        prefix: Optional prefix to add to the random string

    Returns:
        Random string with optional prefix

    Example:
        >>> random_string(8, "test_")
        'test_a1B2c3D4'
    """
    chars = string.ascii_letters + string.digits
    random_part = ''.join(random.choices(chars, k=length))
    return f"{prefix}{random_part}" if prefix else random_part


def random_email(domain: str = "example.com") -> str:
    """
    Generate a random email address.

    Args:
        domain: Domain for the email address

    Returns:
        Random email address

    Example:
        >>> random_email()
        'user_abc123@example.com'
    """
    username = random_string(8, prefix="user_")
    return f"{username}@{domain}"


def random_filename(
    extension: str = "mp3",
    prefix: str = "audio_"
) -> str:
    """
    Generate a random filename with extension.

    Args:
        extension: File extension (without dot)
        prefix: Filename prefix

    Returns:
        Random filename

    Example:
        >>> random_filename("wav", "recording_")
        'recording_abc123.wav'
    """
    return f"{prefix}{random_string(8)}.{extension}"


def random_transcript_text(
    min_sentences: int = 3,
    max_sentences: int = 10,
    language: str = "en"
) -> str:
    """
    Generate random transcript text.

    Args:
        min_sentences: Minimum number of sentences
        max_sentences: Maximum number of sentences
        language: Language code for text generation

    Returns:
        Random transcript text

    Example:
        >>> random_transcript_text(2, 5)
        'This is sentence one. This is sentence two.'
    """
    if language == "ru":
        words = [
            "Привет", "мир", "это", "тест", "транскрипция",
            "запись", "встреча", "обсуждение", "проект", "задача"
        ]
        templates = [
            "{} {}, сказал он.",
            "Это {} {}.",
            "На встрече обсуждали {} {}.",
            "Главное - это {} {}.",
            "{} {} было важным моментом."
        ]
    else:
        words = [
            "hello", "world", "this", "is", "a", "test",
            "transcription", "meeting", "discussion", "project"
        ]
        templates = [
            "{} {}, he said.",
            "This is {} {}.",
            "The meeting discussed {} {}.",
            "The main point was {} {}.",
            "{} {} was an important topic."
        ]

    num_sentences = random.randint(min_sentences, max_sentences)
    sentences = []

    for _ in range(num_sentences):
        template = random.choice(templates)
        word1 = random.choice(words)
        word2 = random.choice(words)
        sentences.append(template.format(word1, word2))

    return " ".join(sentences)


def random_timestamp(
    start_date: Optional[datetime] = None,
    days_back: int = 30
) -> datetime:
    """
    Generate a random timestamp within a date range.

    Args:
        start_date: Start of date range (defaults to days_back ago)
        days_back: Number of days back from now if start_date not provided

    Returns:
        Random datetime

    Example:
        >>> dt = random_timestamp(days_back=7)
        >>> isinstance(dt, datetime)
        True
    """
    if start_date is None:
        start_date = datetime.now() - timedelta(days=days_back)

    end_date = datetime.now()
    time_between = end_date - start_date
    random_seconds = random.randint(0, int(time_between.total_seconds()))
    return start_date + timedelta(seconds=random_seconds)


def random_file_size(
    min_mb: float = 1.0,
    max_mb: float = 25.0
) -> int:
    """
    Generate a random file size in bytes.

    Args:
        min_mb: Minimum size in megabytes
        max_mb: Maximum size in megabytes

    Returns:
        File size in bytes

    Example:
        >>> size = random_file_size(5, 10)
        >>> size > 5 * 1024 * 1024 and size < 10 * 1024 * 1024
        True
    """
    size_mb = random.uniform(min_mb, max_mb)
    return int(size_mb * 1024 * 1024)


def random_duration(
    min_seconds: float = 30.0,
    max_seconds: float = 3600.0
) -> float:
    """
    Generate a random audio duration.

    Args:
        min_seconds: Minimum duration in seconds
        max_seconds: Maximum duration in seconds

    Returns:
        Random duration in seconds

    Example:
        >>> duration = random_duration(60, 300)
        >>> 60 <= duration <= 300
        True
    """
    return random.uniform(min_seconds, max_seconds)


def random_language(
    include_rare: bool = False
) -> str:
    """
    Generate a random ISO-639-1 language code.

    Args:
        include_rare: Include less common languages

    Returns:
        Language code

    Example:
        >>> random_language()
        'en'
    """
    common_languages = ["en", "ru", "es", "fr", "de", "it", "pt"]
    rare_languages = ["zh", "ja", "ko", "ar", "hi", "tr", "pl", "nl"]

    languages = common_languages + (rare_languages if include_rare else [])
    return random.choice(languages)


# =============================================================================
# Factory Functions for Database Models
# =============================================================================

def transcript_factory(
    **overrides
) -> Dict[str, Any]:
    """
    Create test data for a Transcript model.

    Generates realistic test data with optional overrides for specific fields.

    Args:
        **overrides: Field values to override defaults

    Returns:
        Dictionary with transcript data

    Example:
        >>> data = transcript_factory(
        ...     language="ru",
        ...     status="completed"
        ... )
        >>> data["language"]
        'ru'
    """
    return {
        "id": uuid4(),
        "original_filename": random_filename("mp3", "meeting_"),
        "file_path": f"/uploads/{random_filename('mp3')}",
        "file_size": random_file_size(2, 15),
        "duration_seconds": random_duration(60, 1800),
        "language": random_language(),
        "status": random.choice(["pending", "processing", "completed", "failed"]),
        "transcription_text": random_transcript_text() if random.random() > 0.3 else None,
        "transcription_json": {"words": [{"word": "test", "start": 0.0, "end": 0.5}]},
        "transcription_srt": "1\\n00:00:00,000 --> 00:00:00,500\\nTest",
        "created_at": random_timestamp(),
        "updated_at": datetime.now(),
        "extra_metadata": {"test": "data"},
        "tags": random.sample(["meeting", "interview", "lecture", "podcast", "call"], k=random.randint(1, 3)),
        "category": random.choice(["meeting", "interview", "lecture", "podcast", None]),
        **overrides
    }


def summary_factory(
    transcript_id: Optional[str] = None,
    **overrides
) -> Dict[str, Any]:
    """
    Create test data for a Summary model.

    Args:
        transcript_id: ID of the associated transcript
        **overrides: Field values to override defaults

    Returns:
        Dictionary with summary data

    Example:
        >>> data = summary_factory(
        ...     template="interview",
        ...     model_used="GigaChat-2-Max"
        ... )
    """
    templates = ["meeting", "interview", "lecture", "podcast", None]
    models = ["GigaChat", "GigaChat-2-Max", "Qwen3-235B", "Qwen3-235B-A22B-Instruct-2507"]

    return {
        "id": uuid4(),
        "transcript_id": transcript_id or str(uuid4()),
        "summary_text": f"Summary: {random_transcript_text(min_sentences=2, max_sentences=5)}",
        "summary_template": random.choice(templates),
        "summary_config": {
            "participants": random.choice([True, False]),
            "decisions": random.choice([True, False]),
            "deadlines": random.choice([True, False]),
            "topics": random.choice([True, False])
        },
        "model_used": random.choice(models),
        "created_at": datetime.now(),
        "updated_at": datetime.now(),
        **overrides
    }


def processing_job_factory(
    transcript_id: Optional[str] = None,
    **overrides
) -> Dict[str, Any]:
    """
    Create test data for a ProcessingJob model.

    Args:
        transcript_id: ID of the associated transcript
        **overrides: Field values to override defaults

    Returns:
        Dictionary with processing job data
    """
    job_types = ["transcription", "summarization", "translation", "indexing"]
    statuses = ["queued", "processing", "completed", "failed"]

    status = random.choice(statuses)
    progress = {
        "queued": 0.0,
        "processing": random.uniform(0.1, 0.9),
        "completed": 1.0,
        "failed": random.uniform(0.0, 0.5)
    }[status]

    return {
        "id": uuid4(),
        "transcript_id": transcript_id or str(uuid4()),
        "job_type": random.choice(job_types),
        "status": status,
        "progress": progress,
        "error_message": "Error message" if status == "failed" else None,
        "retry_count": random.randint(0, 3),
        "created_at": random_timestamp(),
        "updated_at": datetime.now(),
        **overrides
    }


def rag_session_factory(
    **overrides
) -> Dict[str, Any]:
    """
    Create test data for a RAGSession model.

    Args:
        **overrides: Field values to override defaults

    Returns:
        Dictionary with RAG session data
    """
    return {
        "id": uuid4(),
        "session_name": f"Session {random_string(6)}",
        "transcript_ids": [str(uuid4()) for _ in range(random.randint(1, 5))],
        "created_at": datetime.now(),
        "updated_at": datetime.now(),
        **overrides
    }


def rag_message_factory(
    session_id: Optional[str] = None,
    **overrides
) -> Dict[str, Any]:
    """
    Create test data for a RAGMessage model.

    Args:
        session_id: ID of the associated session
        **overrides: Field values to override defaults

    Returns:
        Dictionary with RAG message data
    """
    questions = [
        "What was discussed in the meeting?",
        "What are the main topics?",
        "What decisions were made?",
        "Who participated?",
        "What is the timeline for the project?"
    ]

    return {
        "id": uuid4(),
        "session_id": session_id or str(uuid4()),
        "question": random.choice(questions),
        "answer": f"Based on the transcript: {random_transcript_text(2, 4)}",
        "quality_score": random.uniform(0.5, 1.0),
        "retrieved_documents": [
            {
                "content": random_transcript_text(1, 2),
                "score": random.uniform(0.7, 0.99),
                "metadata": {"source": random_filename("mp3")}
            }
            for _ in range(random.randint(1, 5))
        ],
        "created_at": datetime.now(),
        **overrides
    }


# =============================================================================
# API Payload Builders
# =============================================================================

def transcript_create_payload(
    filename: Optional[str] = None,
    language: Optional[str] = None
) -> Dict[str, Any]:
    """
    Build a payload for creating a transcript.

    Args:
        filename: Optional filename override
        language: Optional language code override

    Returns:
        API request payload

    Example:
        >>> payload = transcript_create_payload("test.mp3", "en")
        >>> payload["original_filename"]
        'test.mp3'
    """
    return {
        "original_filename": filename or random_filename("mp3"),
        "language": language or random_language()
    }


def summary_create_payload(
    transcript_id: Optional[str] = None,
    template: Optional[str] = None,
    custom_prompt: Optional[str] = None,
    model: Optional[str] = None
) -> Dict[str, Any]:
    """
    Build a payload for creating a summary.

    Args:
        transcript_id: ID of the transcript to summarize
        template: Summary template (meeting, interview, etc.)
        custom_prompt: Optional custom prompt
        model: Model to use for summarization

    Returns:
        API request payload
    """
    return {
        "transcript_id": transcript_id or str(uuid4()),
        "template": template or random.choice(["meeting", "interview", "lecture", "podcast"]),
        "custom_prompt": custom_prompt,
        "fields_config": {
            "participants": True,
            "decisions": True,
            "deadlines": random.choice([True, False]),
            "topics": True
        },
        "model": model or "GigaChat-2-Max"
    }


def rag_session_create_payload(
    session_name: Optional[str] = None,
    transcript_ids: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Build a payload for creating a RAG session.

    Args:
        session_name: Optional session name
        transcript_ids: Optional list of transcript IDs to include

    Returns:
        API request payload
    """
    return {
        "session_name": session_name or f"Test Session {random_string(4)}",
        "transcript_ids": transcript_ids or [str(uuid4()) for _ in range(2)]
    }


def rag_question_payload(
    question: Optional[str] = None,
    transcript_ids: Optional[List[str]] = None,
    top_k: int = 5,
    model: Optional[str] = None,
    **options
) -> Dict[str, Any]:
    """
    Build a payload for asking a RAG question.

    Args:
        question: Question to ask
        transcript_ids: Optional list of transcript IDs to search
        top_k: Number of chunks to retrieve
        model: Model to use for answer generation
        **options: Additional RAG options (temperature, use_reranking, etc.)

    Returns:
        API request payload

    Example:
        >>> payload = rag_question_payload(
        ...     question="What was discussed?",
        ...     use_reranking=True
        ... )
    """
    questions = [
        "What were the main topics discussed?",
        "What decisions were made?",
        "Who were the participants?",
        "What is the timeline?"
    ]

    return {
        "question": question or random.choice(questions),
        "transcript_ids": transcript_ids,
        "top_k": top_k,
        "model": model or "GigaChat-2-Max",
        "temperature": options.get("temperature", 0.3),
        "use_reranking": options.get("use_reranking", True),
        "use_query_expansion": options.get("use_query_expansion", True),
        "use_multi_hop": options.get("use_multi_hop", False),
        "use_hybrid_search": options.get("use_hybrid_search", False),
        "use_advanced_grading": options.get("use_advanced_grading", False),
        "reranker_model": options.get("reranker_model", "ms-marco-MiniLM-L-6-v2")
    }


def feedback_payload(
    feedback_type: str = "positive",
    comment: Optional[str] = None
) -> Dict[str, Any]:
    """
    Build a payload for submitting feedback.

    Args:
        feedback_type: Type of feedback ("positive" or "negative")
        comment: Optional comment

    Returns:
        API request payload
    """
    return {
        "feedback_type": feedback_type,
        "comment": comment or random_transcript_text(1, 2)
    }


# =============================================================================
# Edge Case Data Generators
# =============================================================================

def edge_case_transcripts() -> List[Dict[str, Any]]:
    """
    Generate transcript edge cases for testing.

    Returns a list of transcript data representing edge cases like
    very long filenames, special characters, empty fields, etc.

    Returns:
        List of edge case transcript dictionaries

    Example:
        >>> cases = edge_case_transcripts()
        >>> len(cases) > 0
        True
    """
    return [
        # Very long filename
        transcript_factory(
            original_filename="a" * 255 + ".mp3"
        ),
        # Special characters in filename
        transcript_factory(
            original_filename="тест файл (2024) [копия].mp3"
        ),
        # Empty transcription text
        transcript_factory(
            transcription_text="",
            status="completed"
        ),
        # Very long transcription text
        transcript_factory(
            transcription_text=random_transcript_text(50, 100)
        ),
        # Maximum file size
        transcript_factory(
            file_size=25 * 1024 * 1024
        ),
        # Very short duration
        transcript_factory(
            duration_seconds=0.5
        ),
        # Unknown language
        transcript_factory(
            language="unknown"
        ),
        # Unicode characters
        transcript_factory(
            original_filename="🎵 audio 🎙️.mp3",
            transcription_text="Text with emoji 🚀 and unicode: 日本語"
        ),
        # Null/None values
        transcript_factory(
            language=None,
            tags=None,
            category=None
        )
    ]


def edge_case_payloads() -> Dict[str, List[Dict[str, Any]]]:
    """
    Generate edge case payloads for API testing.

    Returns various malformed, empty, and boundary payloads for
    testing API validation and error handling.

    Returns:
        Dictionary mapping endpoint names to lists of edge case payloads

    Example:
        >>> payloads = edge_case_payloads()
        >>> "transcript_create" in payloads
        True
    """
    return {
        "transcript_create": [
            {"original_filename": ""},  # Empty filename
            {"original_filename": "no_extension"},  # No extension
            {"original_filename": "script.sh"},  # Invalid extension
            {"original_filename": "a" * 300 + ".mp3"},  # Too long
            {"language": "invalid_code"},  # Invalid language code
            {"original_filename": None},  # Null filename
            {},  # Empty payload
        ],
        "summary_create": [
            {"transcript_id": ""},  # Empty transcript ID
            {"transcript_id": "invalid-uuid"},  # Invalid UUID
            {"transcript_id": None},  # Null transcript ID
            {"template": "invalid_template"},  # Invalid template
            {
                "transcript_id": str(uuid4()),
                "fields_config": "not_a_dict"  # Invalid type
            },
        ],
        "rag_question": [
            {"question": ""},  # Empty question
            {"question": "a"},  # Too short
            {"question": "a" * 10000},  # Too long
            {"top_k": -1},  # Negative top_k
            {"top_k": 1000},  # Too large top_k
            {"temperature": -0.5},  # Negative temperature
            {"temperature": 2.5},  # Temperature > 2
            {"question": None},  # Null question
        ]
    }


def large_batch_data(
    count: int = 100,
    model_type: str = "transcript"
) -> List[Dict[str, Any]]:
    """
    Generate a large batch of test data.

    Useful for testing pagination, performance, and batch operations.

    Args:
        count: Number of items to generate
        model_type: Type of model data to generate

    Returns:
        List of model data dictionaries

    Example:
        >>> batch = large_batch_data(50, "transcript")
        >>> len(batch)
        50
    """
    factories = {
        "transcript": transcript_factory,
        "summary": summary_factory,
        "rag_session": rag_session_factory,
        "rag_message": rag_message_factory,
        "processing_job": processing_job_factory
    }

    factory = factories.get(model_type, transcript_factory)
    return [factory() for _ in range(count)]


# =============================================================================
# Test Scenario Builders
# =============================================================================

def build_test_scenario(
    scenario: str
) -> Dict[str, Any]:
    """
    Build a complete test scenario with multiple related entities.

    Creates realistic test data for common testing scenarios.

    Args:
        scenario: Type of scenario to build
            - "simple_transcription": Basic transcription workflow
            - "meeting_with_summary": Meeting transcript with summary
            - "multi_language": Transcripts in multiple languages
            - "rag_workflow": Complete RAG workflow with session and messages
            - "failed_job": Failed processing job scenario
            - "batch_processing": Multiple transcripts for batch testing

    Returns:
        Dictionary with scenario data including all entities

    Example:
        >>> scenario = build_test_scenario("meeting_with_summary")
        >>> "transcript" in scenario and "summary" in scenario
        True
    """
    scenarios = {
        "simple_transcription": lambda: {
            "transcript": transcript_factory(status="completed"),
            "processing_job": processing_job_factory(
                job_type="transcription",
                status="completed",
                progress=1.0
            )
        },
        "meeting_with_summary": lambda: {
            "transcript": transcript_factory(
                category="meeting",
                tags=["meeting", "planning"],
                status="completed"
            ),
            "summary": summary_factory(
                template="meeting",
                summary_config={
                    "participants": True,
                    "decisions": True,
                    "deadlines": True,
                    "topics": True
                }
            ),
            "processing_job": processing_job_factory(
                job_type="transcription",
                status="completed"
            )
        },
        "multi_language": lambda: {
            "transcripts": [
                transcript_factory(language="en", status="completed"),
                transcript_factory(language="ru", status="completed"),
                transcript_factory(language="es", status="completed"),
            ],
            "summaries": [
                summary_factory(template="meeting"),
                summary_factory(template="interview"),
                summary_factory(template="lecture")
            ]
        },
        "rag_workflow": lambda: {
            "transcripts": [
                transcript_factory(status="completed"),
                transcript_factory(status="completed")
            ],
            "rag_session": rag_session_factory(
                transcript_ids=[str(uuid4()), str(uuid4())]
            ),
            "rag_messages": [
                rag_message_factory(),
                rag_message_factory(),
                rag_message_factory()
            ]
        },
        "failed_job": lambda: {
            "transcript": transcript_factory(status="failed"),
            "processing_job": processing_job_factory(
                status="failed",
                progress=0.3,
                error_message="Transcription failed: audio format not supported",
                retry_count=3
            )
        },
        "batch_processing": lambda: {
            "transcripts": [transcript_factory() for _ in range(10)],
            "processing_jobs": [
                processing_job_factory(
                    job_type="transcription",
                    status=random.choice(["queued", "processing", "completed"])
                )
                for _ in range(10)
            ]
        }
    }

    if scenario not in scenarios:
        available = ", ".join(scenarios.keys())
        raise ValueError(
            f"Unknown scenario: {scenario}. "
            f"Available scenarios: {available}"
        )

    return scenarios[scenario]()


# =============================================================================
# Response Mock Builders
# =============================================================================

def mock_transcription_response(
    text: Optional[str] = None,
    include_timestamps: bool = True
) -> Dict[str, Any]:
    """
    Build a mock transcription API response.

    Args:
        text: Transcription text (auto-generated if None)
        include_timestamps: Include verbose_json with timestamps

    Returns:
        Mock API response

    Example:
        >>> response = mock_transcription_response()
        >>> "text" in response
        True
    """
    if text is None:
        text = random_transcript_text()

    response = {
        "text": text,
        "language": "english"
    }

    if include_timestamps:
        words = []
        for i, word in enumerate(text.split()[:20]):  # Limit to 20 words
            words.append({
                "word": word,
                "start": i * 0.5,
                "end": (i + 1) * 0.5,
                "confidence": random.uniform(0.9, 1.0)
            })

        response["verbose_json"] = {
            "language": "english",
            "duration": len(text.split()) * 0.5,
            "words": words
        }
        response["srt"] = "\\n".join([
            f"{i+1}\\n00:00:{start:06.2f} --> 00:00:{end:06.2f}\\n{word['word']}"
            for i, word in enumerate(words)
        ])

    return response


def mock_llm_response(
    text: Optional[str] = None,
    model: str = "GigaChat-2-Max",
    tokens_used: int = 150
) -> Dict[str, Any]:
    """
    Build a mock LLM API response.

    Args:
        text: Response text (auto-generated if None)
        model: Model name
        tokens_used: Number of tokens used

    Returns:
        Mock API response
    """
    if text is None:
        text = f"Summary: {random_transcript_text(3, 6)}"

    return {
        "text": text,
        "model": model,
        "usage": {
            "prompt_tokens": tokens_used // 2,
            "completion_tokens": tokens_used // 2,
            "total_tokens": tokens_used
        }
    }


def mock_vector_search_results(
    count: int = 5,
    min_score: float = 0.7,
    max_score: float = 0.99
) -> List[Dict[str, Any]]:
    """
    Build mock vector search results.

    Args:
        count: Number of results
        min_score: Minimum similarity score
        max_score: Maximum similarity score

    Returns:
        List of mock search results
    """
    return [
        {
            "id": str(uuid4()),
            "score": random.uniform(min_score, max_score),
            "payload": {
                "text": random_transcript_text(1, 2),
                "transcript_id": str(uuid4()),
                "metadata": {
                    "start_time": random.uniform(0, 100),
                    "end_time": random.uniform(100, 200)
                }
            }
        }
        for _ in range(count)
    ]


# =============================================================================
# Utility Functions
# =============================================================================

def apply_factory_overrides(
    base_data: Dict[str, Any],
    **overrides
) -> Dict[str, Any]:
    """
    Apply overrides to base data with deep merge for nested dicts.

    Args:
        base_data: Base data dictionary
        **overrides: Fields to override

    Returns:
        Merged dictionary

    Example:
        >>> data = {"config": {"a": 1, "b": 2}}
        >>> result = apply_factory_overrides(data, config={"b": 3})
        >>> result["config"]
        {'a': 1, 'b': 3}
    """
    result = base_data.copy()

    for key, value in overrides.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = {**result[key], **value}
        else:
            result[key] = value

    return result


def serialize_for_json(
    data: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Convert data to JSON-serializable format.

    Converts UUID, datetime, and other non-serializable types to strings.

    Args:
        data: Data dictionary

    Returns:
        JSON-serializable dictionary
    """
    from uuid import UUID
    from datetime import datetime

    def convert_value(value):
        if isinstance(value, UUID):
            return str(value)
        elif isinstance(value, datetime):
            return value.isoformat()
        elif isinstance(value, dict):
            return {k: convert_value(v) for k, v in value.items()}
        elif isinstance(value, list):
            return [convert_item(item) for item in value]
        else:
            return value

    def convert_item(item):
        if isinstance(item, UUID):
            return str(item)
        elif isinstance(item, datetime):
            return item.isoformat()
        elif isinstance(item, dict):
            return {k: convert_value(v) for k, v in item.items()}
        elif isinstance(item, list):
            return [convert_item(i) for i in item]
        else:
            return item

    return convert_value(data)
