"""
Test helpers package for STT backend testing.
"""

from .assertions import (
    # Response assertions
    "assert_valid_response",
    "assert_error_response",

    # Transcript assertions
    "assert_transcript_response",
    "assert_transcript_list_response",
    "assert_transcript_status",

    # Summary assertions
    "assert_summary_response",
    "assert_summary_contains",

    # RAG assertions
    "assert_rag_session_response",
    "assert_rag_response",
    "assert_rag_message_response",
    "assert_quality_metrics",

    # Processing job assertions
    "assert_processing_job_response",
    "assert_progress_schema",

    # File assertions
    "assert_file_metadata",
    "assert_valid_audio_format",

    # Type validation
    "assert_valid_uuid",
    "assert_valid_timestamp",
    "assert_valid_iso8601",
    "assert_valid_email",
    "assert_valid_url",

    # Pagination and comparison
    "assert_paginated_response",
    "assert_objects_equal",
    "assert_list_contains",

    # HTTP assertions
    "assert_http_success",
    "assert_http_error",
    "assert_content_type",
)

from .mocks import (
    # Mock classes
    "MockEvolutionAPI",
    "MockOpenAI",
    "MockQdrantClient",
    "MockFileStorage",
    "MockDatabaseSession",

    # Mock helpers
    "create_async_mock",
    "create_mock_context_manager",
    "configure_transcription_success",
    "configure_transcription_failure",
    "configure_llm_success",
    "configure_llm_rate_limit",
    "configure_vector_search_success",
)

__all__ = [
    # Response assertions
    "assert_valid_response",
    "assert_error_response",

    # Transcript assertions
    "assert_transcript_response",
    "assert_transcript_list_response",
    "assert_transcript_status",

    # Summary assertions
    "assert_summary_response",
    "assert_summary_contains",

    # RAG assertions
    "assert_rag_session_response",
    "assert_rag_response",
    "assert_rag_message_response",
    "assert_quality_metrics",

    # Processing job assertions
    "assert_processing_job_response",
    "assert_progress_schema",

    # File assertions
    "assert_file_metadata",
    "assert_valid_audio_format",

    # Type validation
    "assert_valid_uuid",
    "assert_valid_timestamp",
    "assert_valid_iso8601",
    "assert_valid_email",
    "assert_valid_url",

    # Pagination and comparison
    "assert_paginated_response",
    "assert_objects_equal",
    "assert_list_contains",

    # HTTP assertions
    "assert_http_success",
    "assert_http_error",
    "assert_content_type",

    # Mock classes
    "MockEvolutionAPI",
    "MockOpenAI",
    "MockQdrantClient",
    "MockFileStorage",
    "MockDatabaseSession",

    # Mock helpers
    "create_async_mock",
    "create_mock_context_manager",
    "configure_transcription_success",
    "configure_transcription_failure",
    "configure_llm_success",
    "configure_llm_rate_limit",
    "configure_vector_search_success",
]
