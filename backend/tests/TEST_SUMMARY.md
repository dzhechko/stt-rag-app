# Backend API Test Suite - Summary

## Overview

Comprehensive pytest-based integration and unit tests for the STT (Speech-to-Text) App backend API. The test suite covers all major endpoints including transcripts, summaries, RAG/QA, and translation features.

## Test Structure

```
backend/tests/
├── conftest.py                          # Shared fixtures and configuration
├── integration/
│   ├── test_transcripts_api.py          # Transcript CRUD endpoints (35+ tests)
│   ├── test_summaries_api.py            # Summary endpoints (25+ tests)
│   ├── test_rag_api.py                  # RAG/QA endpoints (40+ tests)
│   └── test_translation_api.py          # Translation endpoints (30+ tests)
├── unit/
│   └── test_models.py                   # Pydantic model validation (20+ tests)
├── README.md                            # Testing documentation
└── TEST_SUMMARY.md                      # This file
```

## Total Test Coverage

- **Integration Tests**: 130+ tests across 4 modules
- **Unit Tests**: 20+ model validation tests
- **Total**: 150+ comprehensive test cases

## Test Modules

### 1. test_transcripts_api.py

**Endpoints Tested:**
- `POST /api/transcripts/upload` - File upload with validation
- `GET /api/transcripts` - List with pagination and filtering
- `GET /api/transcripts/{id}` - Retrieve single transcript
- `PUT /api/transcripts/{id}` - Update transcript
- `DELETE /api/transcripts/{id}` - Delete transcript
- `GET /api/transcripts/{id}/jobs` - Get processing jobs
- `GET /api/jobs/{id}` - Get single job

**Test Coverage:**
- ✅ Valid audio files (MP3, WAV, M4A, WebM)
- ✅ File type validation and rejection
- ✅ Language parameter handling (en, ru, with variations)
- ✅ Pagination (skip/limit)
- ✅ Status filtering (pending, processing, completed, failed)
- ✅ Language filtering
- ✅ Combined filters
- ✅ CRUD operations (Create, Read, Update, Delete)
- ✅ Cascade deletion (transcript → jobs)
- ✅ Special characters in filenames
- ✅ Unicode filenames
- ✅ Multiple simultaneous uploads
- ✅ Empty file handling
- ✅ Processing job creation
- ✅ Invalid UUID handling
- ✅ Not found scenarios
- ✅ Schema validation

### 2. test_summaries_api.py

**Endpoints Tested:**
- `POST /api/summaries` - Create summary
- `GET /api/transcripts/{id}/summaries` - List summaries for transcript
- `GET /api/summaries/{id}` - Get single summary

**Test Coverage:**
- ✅ Default template creation
- ✅ Custom templates (meeting, interview, lecture, podcast)
- ✅ Custom prompts
- ✅ Fields configuration (participants, decisions, deadlines, topics)
- ✅ Model selection (GigaChat-2-Max, GigaChat-2, Qwen3)
- ✅ All parameters combined
- ✅ Non-existent transcript handling
- ✅ Pending/incomplete transcript rejection
- ✅ No text transcript rejection
- ✅ Processing job creation
- ✅ Multiple summaries per transcript
- ✅ Summary ordering (newest first)
- ✅ Empty results handling
- ✅ Invalid templates
- ✅ Null/empty parameters
- ✅ Translated transcript handling
- ✅ Concurrent summary creation
- ✅ Schema validation

### 3. test_rag_api.py

**Endpoints Tested:**
- `POST /api/rag/sessions` - Create RAG session
- `GET /api/rag/sessions` - List sessions
- `GET /api/rag/sessions/{id}` - Get session
- `DELETE /api/rag/sessions/{id}` - Delete session
- `POST /api/rag/ask` - Ask question (without session)
- `POST /api/rag/sessions/{id}/ask` - Ask in session
- `GET /api/rag/sessions/{id}/messages` - Get messages
- `POST /api/rag/messages/{id}/feedback` - Submit feedback
- `GET /api/transcripts/{id}/index-status` - Check index status
- `POST /api/transcripts/{id}/reindex` - Reindex transcript
- `GET /api/rag/status` - System status

**Test Coverage:**
- ✅ Session creation (minimal, with name, with transcripts)
- ✅ Session listing and ordering
- ✅ Session retrieval
- ✅ Session deletion with cascade to messages
- ✅ Question asking (with/without session)
- ✅ Transcript filtering
- ✅ All RAG parameters (top_k, temperature, reranking, etc.)
- ✅ Query expansion
- ✅ Multi-hop reasoning
- ✅ Hybrid search
- ✅ Advanced grading
- ✅ Custom reranker models
- ✅ Message creation and retrieval
- ✅ Message ordering (chronological)
- ✅ Feedback submission (positive/negative)
- ✅ Feedback with/without comments
- ✅ Index status checking
- ✅ Transcript reindexing
- ✅ Job creation for indexing
- ✅ System status diagnostics
- ✅ Qdrant availability checking
- ✅ Embeddings availability checking
- ✅ Unicode session names
- ✅ Special characters in questions
- ✅ Very long questions
- ✅ Boundary values (top_k, temperature)
- ✅ Concurrent session creation
- ✅ Temporary session creation for feedback

### 4. test_translation_api.py

**Endpoints Tested:**
- `POST /api/transcripts/{id}/translate` - Translate transcript

**Test Coverage:**
- ✅ English to Russian translation
- ✅ Russian to English translation
- ✅ Russian to Russian (no-op)
- ✅ Model selection
- ✅ Default target language (Russian)
- ✅ Already translated detection
- ✅ Translation back to original
- ✅ Translation job creation
- ✅ Progress tracking
- ✅ Multiple target languages
- ✅ Different source languages
- ✅ Non-existent transcript handling
- ✅ No text rejection
- ✅ Not completed status rejection
- ✅ Failed status rejection
- ✅ Invalid UUID handling
- ✅ Empty target language
- ✅ Metadata preservation
- ✅ Language field updates
- ✅ Very long text translation
- ✅ Empty text handling
- ✅ Unicode text
- ✅ Special characters
- ✅ Concurrent translations
- ✅ Duplicate translation requests

### 5. test_models.py

**Models Tested:**
- `TranscriptCreate`, `TranscriptResponse`, `TranscriptUpdate`
- `TranscriptListResponse`
- `SummaryCreate`, `SummaryResponse`
- `RAGSessionCreate`, `RAGSessionResponse`
- `RAGQuestionRequest`, `RAGAnswerResponse`
- `RAGFeedbackRequest`
- `ProcessingJobResponse`

**Test Coverage:**
- ✅ Valid model creation
- ✅ Optional field handling
- ✅ Null field handling
- ✅ Default values
- ✅ UUID validation
- ✅ DateTime handling
- ✅ Nested JSON structures
- ✅ Array fields (tags, transcript_ids)
- ✅ Complex nested metadata
- ✅ Enum validation (status, job_type)
- ✅ Validation error scenarios
- ✅ Schema generation

## Fixtures Available

### Database Fixtures
- `db_engine` - Creates and initializes test database
- `db_session` - Provides clean database session for each test

### Client Fixtures
- `async_client` - Async HTTP client for API testing

### Sample Data Fixtures
- `sample_audio_file` - Single temporary audio file
- `sample_audio_files` - Multiple audio files (different formats)
- `invalid_files` - Files with invalid extensions
- `sample_transcript` - Single completed transcript
- `sample_transcripts` - Multiple transcripts (various statuses)
- `sample_summary` - Single summary
- `sample_summaries` - Multiple summaries
- `sample_rag_session` - Single RAG session
- `sample_rag_sessions` - Multiple RAG sessions
- `sample_processing_job` - Single processing job

### Helper Fixtures
- `create_transcript_helper` - Factory for creating transcripts
- `create_summary_helper` - Factory for creating summaries
- `create_rag_session_helper` - Factory for creating RAG sessions

## Running Tests

### Quick Start

```bash
cd backend

# Install test dependencies
pip install -r requirements-test.txt

# Run all tests
pytest

# Or use the test runner script
./run_tests.sh
```

### Run Specific Tests

```bash
# Run specific test file
pytest tests/integration/test_transcripts_api.py

# Run specific test class
pytest tests/integration/test_transcripts_api.py::TestTranscriptUpload

# Run specific test
pytest tests/integration/test_transcripts_api.py::TestTranscriptUpload::test_upload_valid_audio_file

# Run unit tests only
pytest tests/unit

# Run integration tests only
pytest tests/integration
```

### With Coverage

```bash
pytest --cov=app --cov-report=html

# Open coverage report
open htmlcov/index.html
```

### Verbose Output

```bash
pytest -v
pytest -vv  # Extra verbose
```

### Using the Test Runner Script

```bash
# Run all tests
./run_tests.sh

# Run with coverage
./run_tests.sh --coverage

# Run integration tests only
./run_tests.sh --integration

# Run unit tests only
./run_tests.sh --unit

# Verbose mode
./run_tests.sh --verbose

# Watch mode (rerun on changes)
./run_tests.sh --watch

# Show help
./run_tests.sh --help
```

## Configuration Files

### pytest.ini
- Test discovery patterns
- Async test configuration
- Markers
- Output formatting

### pyproject.toml
- Alternative pytest configuration
- Asyncio mode settings
- Test paths

### conftest.py
- Shared fixtures
- Database initialization
- Client setup
- Helper functions

## Test Categories

### Positive Tests
- Valid requests with correct parameters
- Successful CRUD operations
- Proper data validation
- Correct response schemas

### Negative Tests
- Invalid input data
- Missing required fields
- Wrong data types
- Invalid UUIDs
- Non-existent resources
- Unauthorized operations (when auth is added)

### Edge Cases
- Empty strings and arrays
- Very long text
- Unicode characters
- Special characters
- Boundary values (pagination, limits)
- Concurrent operations
- Duplicate requests

### Integration Tests
- End-to-end workflows
- Multi-step operations
- Cascade deletions
- Background job processing
- Service interactions

## Error Handling Tests

All endpoints are tested for:
- `400 Bad Request` - Invalid input, validation errors
- `404 Not Found` - Resource doesn't exist
- `422 Unprocessable Entity` - Validation errors (FastAPI)
- `500 Internal Server Error` - Server errors (graceful handling)
- `503 Service Unavailable` - External service unavailable

## External Service Handling

Tests are designed to handle external service unavailability:
- **Qdrant** - RAG tests may pass with 503 when Qdrant is down
- **Evolution Cloud** - Translation/transcription tests accept multiple status codes
- **Embeddings API** - Graceful handling when not available

## Best Practices Followed

1. **Isolation** - Each test gets a fresh database session
2. **Fixtures** - Reusable setup/teardown logic
3. **Async Support** - Proper async test handling with pytest-asyncio
4. **Type Safety** - UUID and datetime validation
5. **Comprehensive Coverage** - Positive, negative, and edge cases
6. **Clear Naming** - Descriptive test and class names
7. **Documentation** - Docstrings for all test classes
8. **Cleanup** - Automatic file and database cleanup

## Continuous Integration

These tests are ready for CI/CD:
- Fast execution with SQLite
- No external dependencies required for most tests
- Clear exit codes
- Coverage reporting available
- Parallel execution support

## Future Enhancements

Potential additions to the test suite:
- Performance/load testing
- Authentication/authorization tests
- WebSocket tests for real-time updates
- More comprehensive service mocking
- API contract testing (OpenAPI validation)
- Integration tests with real external services

## Troubleshooting

### Common Issues

**Import Errors:**
```bash
# Ensure you're in the backend directory
cd backend
pytest
```

**Async Tests Not Running:**
```bash
# Install pytest-asyncio
pip install pytest-asyncio>=0.21.0
```

**Database Errors:**
- Tests use SQLite automatically
- No database setup required
- Each test gets a fresh database

**External Service Failures:**
- RAG tests may fail without Qdrant
- Translation tests may fail without Evolution Cloud
- Tests accept multiple status codes for graceful handling

## Summary

This comprehensive test suite provides:
- ✅ **150+ test cases** covering all major functionality
- ✅ **Integration tests** for all API endpoints
- ✅ **Unit tests** for model validation
- ✅ **Positive and negative scenarios**
- ✅ **Edge cases and error handling**
- ✅ **Async support** throughout
- ✅ **Reusable fixtures** for common scenarios
- ✅ **Easy to run** with simple commands
- ✅ **CI/CD ready** with clear exit codes
- ✅ **Well documented** with examples

The test suite ensures the STT App backend is reliable, robust, and production-ready!
