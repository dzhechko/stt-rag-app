"""
Test fixtures package for STT backend testing.
"""

from .test_data import (
    # Random generators
    random_string,
    random_email,
    random_filename,
    random_transcript_text,
    random_timestamp,
    random_file_size,
    random_duration,
    random_language,

    # Factory functions
    transcript_factory,
    summary_factory,
    processing_job_factory,
    rag_session_factory,
    rag_message_factory,

    # API payloads
    transcript_create_payload,
    summary_create_payload,
    rag_session_create_payload,
    rag_question_payload,
    feedback_payload,

    # Edge cases
    edge_case_transcripts,
    edge_case_payloads,
    large_batch_data,

    # Scenarios
    build_test_scenario,

    # Mock builders
    mock_transcription_response,
    mock_llm_response,
    mock_vector_search_results,

    # Utilities
    apply_factory_overrides,
    serialize_for_json,
)

__all__ = [
    # Random generators
    "random_string",
    "random_email",
    "random_filename",
    "random_transcript_text",
    "random_timestamp",
    "random_file_size",
    "random_duration",
    "random_language",

    # Factory functions
    "transcript_factory",
    "summary_factory",
    "processing_job_factory",
    "rag_session_factory",
    "rag_message_factory",

    # API payloads
    "transcript_create_payload",
    "summary_create_payload",
    "rag_session_create_payload",
    "rag_question_payload",
    "feedback_payload",

    # Edge cases
    "edge_case_transcripts",
    "edge_case_payloads",
    "large_batch_data",

    # Scenarios
    "build_test_scenario",

    # Mock builders
    "mock_transcription_response",
    "mock_llm_response",
    "mock_vector_search_results",

    # Utilities
    "apply_factory_overrides",
    "serialize_for_json",
]
