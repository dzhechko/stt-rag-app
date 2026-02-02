"""
Custom assertion helpers for STT backend testing.

This module provides specialized assertion functions that make tests
more readable and provide better error messages for common test scenarios.
"""

import json
from typing import Dict, Any, List, Optional, Union
from uuid import UUID
from datetime import datetime
import re


# =============================================================================
# Response Assertions
# =============================================================================

def assert_valid_response(
    response: Dict[str, Any],
    expected_keys: Optional[List[str]] = None,
    exclude_keys: Optional[List[str]] = None
) -> None:
    """
    Assert that a response dict is valid and contains expected keys.

    Args:
        response: Response dictionary to validate
        expected_keys: Keys that must be present
        exclude_keys: Keys that must NOT be present

    Raises:
        AssertionError: If validation fails

    Example:
        >>> response = {"id": "123", "name": "test"}
        >>> assert_valid_response(response, expected_keys=["id", "name"])
    """
    assert isinstance(response, dict), f"Response must be a dict, got {type(response)}"

    if expected_keys:
        missing_keys = set(expected_keys) - set(response.keys())
        assert not missing_keys, f"Missing required keys: {missing_keys}"

    if exclude_keys:
        present_keys = set(exclude_keys) & set(response.keys())
        assert not present_keys, f"Keys that should not be present: {present_keys}"


def assert_error_response(
    response: Dict[str, Any],
    expected_error: Optional[str] = None,
    expected_status: Optional[int] = None
) -> None:
    """
    Assert that a response is an error response.

    Args:
        response: Response dictionary
        expected_error: Expected error message (partial match allowed)
        expected_status: Expected HTTP status code (if in response)

    Raises:
        AssertionError: If not an error response or doesn't match expectations

    Example:
        >>> error = {"error": "Not found", "detail": "Resource does not exist"}
        >>> assert_error_response(error, expected_error="Not found")
    """
    assert "error" in response or "detail" in response, \
        "Response must contain 'error' or 'detail' field"

    if expected_error:
        error_text = response.get("error", "") + " " + response.get("detail", "")
        assert expected_error.lower() in error_text.lower(), \
            f"Expected error containing '{expected_error}', got: {error_text}"

    if expected_status:
        assert response.get("status") == expected_status or \
               response.get("code") == expected_status, \
            f"Expected status {expected_status}, got {response.get('status', response.get('code'))}"


# =============================================================================
# Transcript Assertions
# =============================================================================

def assert_transcript_response(
    response: Dict[str, Any],
    check_optional_fields: bool = False
) -> None:
    """
    Assert that a transcript response has the correct structure.

    Args:
        response: Transcript response dictionary
        check_optional_fields: Also validate optional fields are present

    Raises:
        AssertionError: If response structure is invalid

    Example:
        >>> response = {
        ...     "id": "123",
        ...     "original_filename": "test.mp3",
        ...     "status": "completed"
        ... }
        >>> assert_transcript_response(response)
    """
    required_fields = [
        "id", "original_filename", "file_path", "file_size",
        "status", "created_at", "updated_at"
    ]

    assert_valid_response(response, expected_keys=required_fields)

    # Validate field types
    assert_valid_uuid(response["id"])
    assert isinstance(response["original_filename"], str) and len(response["original_filename"]) > 0
    assert isinstance(response["file_path"], str) and len(response["file_path"]) > 0
    assert isinstance(response["file_size"], int) and response["file_size"] >= 0
    assert response["status"] in ["pending", "processing", "completed", "failed"]
    assert_valid_timestamp(response["created_at"])
    assert_valid_timestamp(response["updated_at"])

    # Optional fields
    if check_optional_fields:
        optional_fields = [
            "duration_seconds", "language", "transcription_text",
            "transcription_json", "transcription_srt", "tags", "category"
        ]
        # Just check they're the right type if present
        if "duration_seconds" in response:
            assert isinstance(response["duration_seconds"], (int, float))
        if "language" in response:
            assert isinstance(response["language"], str) and len(response["language"]) == 2
        if "tags" in response:
            assert isinstance(response["tags"], list)
        if "category" in response:
            assert isinstance(response["category"], (str, type(None)))


def assert_transcript_list_response(
    response: Dict[str, Any],
    min_count: int = 0,
    max_count: Optional[int] = None
) -> None:
    """
    Assert that a transcript list response is valid.

    Args:
        response: List response dictionary
        min_count: Minimum expected number of transcripts
        max_count: Maximum expected number of transcripts

    Raises:
        AssertionError: If response structure is invalid

    Example:
        >>> response = {
        ...     "transcripts": [{"id": "123", ...}],
        ...     "total": 1
        ... }
        >>> assert_transcript_list_response(response, min_count=1)
    """
    assert_valid_response(response, expected_keys=["transcripts", "total"])

    assert isinstance(response["transcripts"], list)
    assert isinstance(response["total"], int)
    assert len(response["transcripts"]) == response["total"]

    assert len(response["transcripts"]) >= min_count, \
        f"Expected at least {min_count} transcripts, got {len(response['transcripts'])}"

    if max_count is not None:
        assert len(response["transcripts"]) <= max_count, \
            f"Expected at most {max_count} transcripts, got {len(response['transcripts'])}"

    # Validate each transcript
    for transcript in response["transcripts"]:
        assert_transcript_response(transcript)


def assert_transcript_status(
    response: Dict[str, Any],
    expected_status: str
) -> None:
    """
    Assert that a transcript has the expected status.

    Args:
        response: Transcript response
        expected_status: Expected status value

    Raises:
        AssertionError: If status doesn't match

    Example:
        >>> assert_transcript_status({"status": "completed"}, "completed")
    """
    valid_statuses = ["pending", "processing", "completed", "failed"]
    assert expected_status in valid_statuses, f"Invalid expected status: {expected_status}"
    assert response["status"] == expected_status, \
        f"Expected status '{expected_status}', got '{response['status']}'"


# =============================================================================
# Summary Assertions
# =============================================================================

def assert_summary_response(
    response: Dict[str, Any]
) -> None:
    """
    Assert that a summary response has the correct structure.

    Args:
        response: Summary response dictionary

    Raises:
        AssertionError: If response structure is invalid
    """
    required_fields = [
        "id", "transcript_id", "summary_text", "model_used",
        "created_at", "updated_at"
    ]

    assert_valid_response(response, expected_keys=required_fields)

    # Validate field types
    assert_valid_uuid(response["id"])
    assert_valid_uuid(response["transcript_id"])
    assert isinstance(response["summary_text"], str) and len(response["summary_text"]) > 0
    assert isinstance(response["model_used"], str) and len(response["model_used"]) > 0
    assert_valid_timestamp(response["created_at"])
    assert_valid_timestamp(response["updated_at"])


def assert_summary_contains(
    response: Dict[str, Any],
    keywords: List[str],
    case_sensitive: bool = False
) -> None:
    """
    Assert that a summary text contains certain keywords.

    Args:
        response: Summary response
        keywords: List of keywords to look for
        case_sensitive: Whether to match case

    Raises:
        AssertionError: If any keyword is missing

    Example:
        >>> summary = {"summary_text": "The meeting discussed project plans."}
        >>> assert_summary_contains(summary, ["meeting", "project"])
    """
    text = response["summary_text"]
    if not case_sensitive:
        text = text.lower()

    missing = []
    for keyword in keywords:
        search_keyword = keyword if case_sensitive else keyword.lower()
        if search_keyword not in text:
            missing.append(keyword)

    assert not missing, f"Summary missing keywords: {missing}"


# =============================================================================
# RAG Assertions
# =============================================================================

def assert_rag_session_response(
    response: Dict[str, Any]
) -> None:
    """
    Assert that a RAG session response has the correct structure.

    Args:
        response: RAG session response dictionary

    Raises:
        AssertionError: If response structure is invalid
    """
    required_fields = ["id", "created_at", "updated_at"]

    assert_valid_response(response, expected_keys=required_fields)

    assert_valid_uuid(response["id"])
    assert_valid_timestamp(response["created_at"])
    assert_valid_timestamp(response["updated_at"])

    # Validate optional fields
    if "session_name" in response:
        assert isinstance(response["session_name"], (str, type(None)))

    if "transcript_ids" in response:
        assert isinstance(response["transcript_ids"], list)
        for tid in response["transcript_ids"]:
            assert_valid_uuid(tid)


def assert_rag_response(
    response: Dict[str, Any],
    check_quality_metrics: bool = False
) -> None:
    """
    Assert that a RAG answer response has the correct structure.

    Args:
        response: RAG answer response dictionary
        check_quality_metrics: Also validate quality metrics if present

    Raises:
        AssertionError: If response structure is invalid
    """
    required_fields = ["answer", "sources", "quality_score", "retrieved_chunks"]

    assert_valid_response(response, expected_keys=required_fields)

    # Validate answer
    assert isinstance(response["answer"], str) and len(response["answer"]) > 0

    # Validate sources
    assert isinstance(response["sources"], list)
    for source in response["sources"]:
        assert isinstance(source, dict)

    # Validate quality score
    assert isinstance(response["quality_score"], (int, float))
    assert 0 <= response["quality_score"] <= 1, \
        f"Quality score must be between 0 and 1, got {response['quality_score']}"

    # Validate retrieved chunks
    assert isinstance(response["retrieved_chunks"], list)
    for chunk in response["retrieved_chunks"]:
        assert isinstance(chunk, dict)
        assert "content" in chunk or "text" in chunk

    # Optional: quality metrics
    if check_quality_metrics and "quality_metrics" in response:
        assert_quality_metrics(response["quality_metrics"])


def assert_rag_message_response(
    response: Dict[str, Any]
) -> None:
    """
    Assert that a RAG message response has the correct structure.

    Args:
        response: RAG message response dictionary

    Raises:
        AssertionError: If response structure is invalid
    """
    required_fields = [
        "id", "session_id", "question", "answer",
        "created_at"
    ]

    assert_valid_response(response, expected_keys=required_fields)

    assert_valid_uuid(response["id"])
    assert_valid_uuid(response["session_id"])
    assert isinstance(response["question"], str) and len(response["question"]) > 0
    assert isinstance(response["answer"], str) and len(response["answer"]) > 0
    assert_valid_timestamp(response["created_at"])

    # Optional fields
    if "quality_score" in response:
        assert isinstance(response["quality_score"], (int, float, type(None)))

    if "retrieved_documents" in response:
        assert isinstance(response["retrieved_documents"], list)


def assert_quality_metrics(
    metrics: Dict[str, Any]
) -> None:
    """
    Assert that quality metrics have valid values.

    Args:
        metrics: Quality metrics dictionary

    Raises:
        AssertionError: If metrics are invalid

    Example:
        >>> metrics = {
        ...     "groundedness": 0.9,
        ...     "completeness": 0.8,
        ...     "relevance": 0.85,
        ...     "overall_score": 4.2
        ... }
        >>> assert_quality_metrics(metrics)
    """
    required_fields = ["groundedness", "completeness", "relevance", "overall_score"]
    assert_valid_response(metrics, expected_keys=required_fields)

    # Check ranges
    assert 0 <= metrics["groundedness"] <= 1, "groundedness must be 0-1"
    assert 0 <= metrics["completeness"] <= 1, "completeness must be 0-1"
    assert 0 <= metrics["relevance"] <= 1, "relevance must be 0-1"
    assert 0 <= metrics["overall_score"] <= 5, "overall_score must be 0-5"


# =============================================================================
# Processing Job Assertions
# =============================================================================

def assert_processing_job_response(
    response: Dict[str, Any]
) -> None:
    """
    Assert that a processing job response has the correct structure.

    Args:
        response: Processing job response dictionary

    Raises:
        AssertionError: If response structure is invalid
    """
    required_fields = [
        "id", "transcript_id", "job_type", "status",
        "progress", "retry_count", "created_at", "updated_at"
    ]

    assert_valid_response(response, expected_keys=required_fields)

    assert_valid_uuid(response["id"])
    assert_valid_uuid(response["transcript_id"])
    assert response["job_type"] in ["transcription", "summarization", "translation", "indexing"]
    assert response["status"] in ["queued", "processing", "completed", "failed"]
    assert isinstance(response["progress"], (int, float))
    assert 0 <= response["progress"] <= 1, f"Progress must be 0-1, got {response['progress']}"
    assert isinstance(response["retry_count"], int) and response["retry_count"] >= 0
    assert_valid_timestamp(response["created_at"])
    assert_valid_timestamp(response["updated_at"])


def assert_progress_schema(
    progress: Union[float, Dict[str, Any]],
    check_job_status: bool = False
) -> None:
    """
    Assert that progress data follows the expected schema.

    Args:
        progress: Progress value (0-1) or progress dict
        check_job_status: Also check if job status is valid

    Raises:
        AssertionError: If progress is invalid

    Example:
        >>> assert_progress_schema(0.5)
        >>> assert_progress_schema({"progress": 0.75, "status": "processing"})
    """
    if isinstance(progress, (int, float)):
        assert 0 <= progress <= 1, f"Progress must be 0-1, got {progress}"
    elif isinstance(progress, dict):
        assert "progress" in progress, "Progress dict must have 'progress' key"
        assert 0 <= progress["progress"] <= 1, \
            f"Progress must be 0-1, got {progress['progress']}"

        if check_job_status and "status" in progress:
            valid_statuses = ["queued", "processing", "completed", "failed"]
            assert progress["status"] in valid_statuses, \
                f"Invalid status: {progress['status']}"


# =============================================================================
# File and Upload Assertions
# =============================================================================

def assert_file_metadata(
    metadata: Dict[str, Any],
    expected_fields: Optional[List[str]] = None
) -> None:
    """
    Assert that file metadata is valid.

    Args:
        metadata: File metadata dictionary
        expected_fields: Additional expected fields

    Raises:
        AssertionError: If metadata is invalid
    """
    base_fields = ["filename", "size", "content_type"]
    fields = base_fields + (expected_fields or [])

    assert_valid_response(metadata, expected_keys=fields)

    assert isinstance(metadata["filename"], str) and len(metadata["filename"]) > 0
    assert isinstance(metadata["size"], int) and metadata["size"] >= 0
    assert isinstance(metadata["content_type"], str) and len(metadata["content_type"]) > 0


def assert_valid_audio_format(
    filename: str,
    allowed_formats: Optional[List[str]] = None
) -> None:
    """
    Assert that a filename has a valid audio format.

    Args:
        filename: Filename to check
        allowed_formats: List of allowed extensions (without dot)

    Raises:
        AssertionError: If format is invalid

    Example:
        >>> assert_valid_audio_format("test.mp3")
        >>> assert_valid_audio_format("test.wav", ["mp3", "wav"])
    """
    if allowed_formats is None:
        allowed_formats = ["mp3", "wav", "m4a", "webm", "mp4", "m4a"]

    assert "." in filename, f"Filename must have an extension: {filename}"

    ext = filename.rsplit(".", 1)[-1].lower()
    assert ext in allowed_formats, \
        f"Invalid audio format: {ext}. Allowed: {allowed_formats}"


# =============================================================================
# Type Validation Helpers
# =============================================================================

def assert_valid_uuid(
    value: Any,
    version: int = 4
) -> None:
    """
    Assert that a value is a valid UUID.

    Args:
        value: Value to check
        version: UUID version (default: 4)

    Raises:
        AssertionError: If value is not a valid UUID

    Example:
        >>> assert_valid_uuid("123e4567-e89b-12d3-a456-426614174000")
    """
    try:
        if isinstance(value, UUID):
            uuid_obj = value
        else:
            uuid_obj = UUID(value)

        assert uuid_obj.version == version, \
            f"UUID must be version {version}, got version {uuid_obj.version}"
    except (ValueError, AttributeError) as e:
        raise AssertionError(f"Invalid UUID v{version}: {value}") from e


def assert_valid_timestamp(
    value: Any,
    allow_string: bool = True
) -> None:
    """
    Assert that a value is a valid timestamp.

    Args:
        value: Value to check (datetime, ISO string, or timestamp)
        allow_string: Allow ISO format strings

    Raises:
        AssertionError: If value is not a valid timestamp

    Example:
        >>> assert_valid_timestamp("2024-01-01T12:00:00")
        >>> assert_valid_timestamp(datetime.now())
    """
    if isinstance(value, datetime):
        return

    if allow_string and isinstance(value, str):
        try:
            datetime.fromisoformat(value.replace("Z", "+00:00"))
            return
        except ValueError:
            pass

    raise AssertionError(f"Invalid timestamp: {value}")


def assert_valid_iso8601(
    value: str
) -> None:
    """
    Assert that a string is a valid ISO 8601 datetime.

    Args:
        value: String to validate

    Raises:
        AssertionError: If string is not valid ISO 8601

    Example:
        >>> assert_valid_iso8601("2024-01-01T12:00:00Z")
    """
    iso_pattern = r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?(Z|[+-]\d{2}:\d{2})?$'
    assert re.match(iso_pattern, value), f"Invalid ISO 8601 format: {value}"


def assert_valid_email(
    value: str
) -> None:
    """
    Assert that a string is a valid email address.

    Args:
        value: Email string to validate

    Raises:
        AssertionError: If string is not a valid email

    Example:
        >>> assert_valid_email("user@example.com")
    """
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    assert re.match(email_pattern, value), f"Invalid email address: {value}"


def assert_valid_url(
    value: str,
    allowed_schemes: Optional[List[str]] = None
) -> None:
    """
    Assert that a string is a valid URL.

    Args:
        value: URL string to validate
        allowed_schemes: List of allowed URL schemes (default: http, https)

    Raises:
        AssertionError: If string is not a valid URL

    Example:
        >>> assert_valid_url("https://example.com")
        >>> assert_valid_url("ftp://files.com", ["ftp", "http", "https"])
    """
    if allowed_schemes is None:
        allowed_schemes = ["http", "https"]

    url_pattern = r'^[a-zA-Z][a-zA-Z0-9+.-]*://'
    assert re.match(url_pattern, value), f"Invalid URL: {value}"

    scheme = value.split("://")[0].lower()
    assert scheme in allowed_schemes, \
        f"URL scheme '{scheme}' not in allowed schemes: {allowed_schemes}"


# =============================================================================
# Pagination and Filtering Assertions
# =============================================================================

def assert_paginated_response(
    response: Dict[str, Any],
    page: Optional[int] = None,
    page_size: Optional[int] = None
) -> None:
    """
    Assert that a paginated response has the correct structure.

    Args:
        response: Paginated response dictionary
        page: Expected page number (optional)
        page_size: Expected page size (optional)

    Raises:
        AssertionError: If response structure is invalid

    Example:
        >>> response = {
        ...     "items": [...],
        ...     "total": 100,
        ...     "page": 1,
        ...     "page_size": 10
        ... }
        >>> assert_paginated_response(response, page=1, page_size=10)
    """
    expected_keys = ["items", "total"]
    assert_valid_response(response, expected_keys=expected_keys)

    assert isinstance(response["items"], list)
    assert isinstance(response["total"], int) and response["total"] >= 0

    if page is not None:
        assert response.get("page") == page, f"Expected page {page}, got {response.get('page')}"

    if page_size is not None:
        assert response.get("page_size") == page_size, \
            f"Expected page_size {page_size}, got {response.get('page_size')}"

    # Validate that we don't have more items than total
    assert len(response["items"]) <= response["total"], \
        "More items in page than total count"

    # Validate that we don't have more items than page_size
    if "page_size" in response:
        assert len(response["items"]) <= response["page_size"], \
            "More items in page than page_size"


# =============================================================================
# Comparison Assertions
# =============================================================================

def assert_objects_equal(
    obj1: Dict[str, Any],
    obj2: Dict[str, Any],
    ignore_fields: Optional[List[str]] = None,
    timestamp_tolerance: Optional[float] = None
) -> None:
    """
    Assert that two objects (dicts) are equal, ignoring specified fields.

    Args:
        obj1: First object
        obj2: Second object
        ignore_fields: Fields to ignore in comparison
        timestamp_tolerance: Tolerance for timestamp comparison (seconds)

    Raises:
        AssertionError: If objects differ

    Example:
        >>> obj1 = {"id": "123", "name": "test", "updated_at": "2024-01-01T12:00:00"}
        >>> obj2 = {"id": "456", "name": "test", "updated_at": "2024-01-01T12:00:05"}
        >>> assert_objects_equal(obj1, obj2, ignore_fields=["id", "updated_at"])
    """
    ignore_fields = ignore_fields or []

    # Filter out ignored fields
    filtered1 = {k: v for k, v in obj1.items() if k not in ignore_fields}
    filtered2 = {k: v for k, v in obj2.items() if k not in ignore_fields}

    # Compare keys
    assert set(filtered1.keys()) == set(filtered2.keys()), \
        f"Keys differ: {set(filtered1.keys()) ^ set(filtered2.keys())}"

    # Compare values
    for key in filtered1.keys():
        val1 = filtered1[key]
        val2 = filtered2[key]

        # Handle timestamp comparison with tolerance
        if timestamp_tolerance and key in ["created_at", "updated_at"]:
            try:
                dt1 = datetime.fromisoformat(val1.replace("Z", "+00:00"))
                dt2 = datetime.fromisoformat(val2.replace("Z", "+00:00"))
                diff = abs((dt1 - dt2).total_seconds())
                assert diff <= timestamp_tolerance, \
                    f"Timestamps differ by {diff}s (max {timestamp_tolerance}s)"
                continue
            except (ValueError, AttributeError):
                pass

        assert val1 == val2, f"Field '{key}' differs: {val1} != {val2}"


def assert_list_contains(
    items: List[Any],
    expected_item: Any,
    key_field: Optional[str] = None
) -> None:
    """
    Assert that a list contains an expected item.

    Args:
        items: List to search
        expected_item: Item to look for
        key_field: If specified, compare only this field

    Raises:
        AssertionError: If item not found

    Example:
        >>> items = [{"id": "1", "name": "test"}, {"id": "2", "name": "demo"}]
        >>> assert_list_contains(items, {"id": "1"}, key_field="id")
    """
    if key_field:
        key_value = expected_item.get(key_field)
        assert key_value is not None, f"expected_item must have '{key_field}' field"

        found = any(item.get(key_field) == key_value for item in items)
        assert found, f"No item with {key_field}={key_value} found in list"
    else:
        assert expected_item in items, f"Item {expected_item} not found in list"


# =============================================================================
# HTTP and API Assertions
# =============================================================================

def assert_http_success(
    status_code: int,
    message: Optional[str] = None
) -> None:
    """
    Assert that an HTTP status code indicates success.

    Args:
        status_code: HTTP status code
        message: Optional message for assertion error

    Raises:
        AssertionError: If status code is not a success code

    Example:
        >>> assert_http_success(200)
        >>> assert_http_success(204)
    """
    assert 200 <= status_code < 300, \
        message or f"Expected success status code (2xx), got {status_code}"


def assert_http_error(
    status_code: int,
    expected_code: Optional[int] = None,
    message: Optional[str] = None
) -> None:
    """
    Assert that an HTTP status code indicates an error.

    Args:
        status_code: HTTP status code
        expected_code: Specific error code expected
        message: Optional message for assertion error

    Raises:
        AssertionError: If status code is not an error code

    Example:
        >>> assert_http_error(404)
        >>> assert_http_error(400, expected_code=400)
    """
    assert 400 <= status_code < 600, \
        message or f"Expected error status code (4xx or 5xx), got {status_code}"

    if expected_code is not None:
        assert status_code == expected_code, \
            message or f"Expected status code {expected_code}, got {status_code}"


def assert_content_type(
    response_headers: Dict[str, str],
    expected_type: str = "application/json"
) -> None:
    """
    Assert that response has the expected content type.

    Args:
        response_headers: Response headers dictionary
        expected_type: Expected content type (partial match allowed)

    Raises:
        AssertionError: If content type doesn't match

    Example:
        >>> headers = {"content-type": "application/json; charset=utf-8"}
        >>> assert_content_type(headers)
    """
    content_type = response_headers.get("content-type", "")
    assert expected_type in content_type.lower(), \
        f"Expected content-type to contain '{expected_type}', got '{content_type}'"
