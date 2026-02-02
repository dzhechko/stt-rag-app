# Backend API Tests

This directory contains comprehensive integration tests for the STT App backend API.

## Test Structure

```
tests/
├── conftest.py                      # Shared fixtures and configuration
├── integration/
│   ├── test_transcripts_api.py      # Transcript CRUD endpoints
│   ├── test_summaries_api.py        # Summary endpoints
│   ├── test_rag_api.py              # RAG/QA endpoints
│   └── test_translation_api.py      # Translation endpoints
└── README.md                        # This file
```

## Running Tests

### Install Test Dependencies

```bash
cd backend
pip install -r requirements-test.txt
```

### Run All Tests

```bash
pytest
```

### Run Specific Test File

```bash
pytest tests/integration/test_transcripts_api.py
```

### Run Specific Test Class

```bash
pytest tests/integration/test_transcripts_api.py::TestTranscriptUpload
```

### Run Specific Test

```bash
pytest tests/integration/test_transcripts_api.py::TestTranscriptUpload::test_upload_valid_audio_file
```

### Run with Coverage

```bash
pytest --cov=app --cov-report=html
```

### Run Only Marked Tests

```bash
# Run only integration tests
pytest -m integration

# Run only async tests
pytest -m asyncio
```

### Verbose Output

```bash
pytest -v
```

## Test Configuration

Tests are configured in:
- `pytest.ini` - Main pytest configuration
- `pyproject.toml` - Alternative pytest configuration
- `conftest.py` - Shared fixtures and test configuration

## Fixtures

### Database Fixtures

- `db_engine` - Creates test database engine
- `db_session` - Provides database session for tests

### Client Fixtures

- `async_client` - Async HTTP client for testing API endpoints

### Data Fixtures

- `sample_audio_file` - Creates a temporary audio file for upload
- `sample_audio_files` - Creates multiple audio files
- `invalid_files` - Creates files with invalid extensions
- `sample_transcript` - Creates a single transcript in DB
- `sample_transcripts` - Creates multiple transcripts
- `sample_summary` - Creates a single summary
- `sample_summaries` - Creates multiple summaries
- `sample_rag_session` - Creates a RAG session
- `sample_rag_sessions` - Creates multiple RAG sessions
- `sample_processing_job` - Creates a processing job

### Helper Fixtures

- `create_transcript_helper` - Function to create transcripts
- `create_summary_helper` - Function to create summaries
- `create_rag_session_helper` - Function to create RAG sessions

## Test Coverage

### Transcripts API (`test_transcripts_api.py`)

**Upload Endpoint:**
- Valid audio files (MP3, WAV, M4A, WebM)
- File validation (extension checking)
- Language parameter handling
- Multiple simultaneous uploads
- Special characters and Unicode filenames
- Empty files
- Processing job creation

**List Transcripts:**
- Pagination (skip/limit)
- Filtering by status
- Filtering by language
- Combined filters
- Ordering
- Empty results

**Get Transcript:**
- Existing transcripts
- Not found cases
- Invalid UUID format
- All fields validation

**Update Transcript:**
- Update text
- Update tags
- Update category
- Update metadata
- Multiple fields
- Not found cases

**Delete Transcript:**
- Successful deletion
- Cascade to jobs
- Not found cases

### Summaries API (`test_summaries_api.py`)

**Create Summary:**
- Default template
- Custom templates (meeting, interview, lecture, podcast)
- Custom prompts
- Fields configuration
- Model selection
- All parameters
- Non-existent transcript
- Pending/transcripts without text
- Processing job creation

**Get Summaries:**
- List for transcript
- Empty results
- Ordering
- Non-existent transcript

**Get Single Summary:**
- Existing summary
- All fields
- Not found cases

**Validation:**
- Multiple summaries per transcript
- Invalid templates
- Empty/null parameters
- Schema validation
- Translated transcripts

### RAG API (`test_rag_api.py`)

**Sessions:**
- Create with minimal data
- Create with name
- Create with transcript IDs
- List sessions
- Get single session
- Delete with cascade
- Unicode names

**Questions:**
- Ask without session
- Ask in session
- Transcript filter
- All parameters (top_k, temperature, reranking, etc.)
- Missing question
- Creates temporary session
- Creates messages

**Messages:**
- Get session messages
- Empty sessions
- Ordering

**Feedback:**
- Positive/negative feedback
- With/without comments
- Invalid types
- Non-existent messages

**Indexing:**
- Index status check
- Reindex transcript
- No text/not completed errors
- Job creation

**System Status:**
- RAG system status
- Structure validation

### Translation API (`test_translation_api.py`)

**Translation:**
- English to Russian
- Russian to English
- Default language
- Model selection
- Already translated
- Language detection

**Progress:**
- Job creation
- Progress tracking
- Job in transcript list

**Languages:**
- Multiple target languages
- Different source languages
- Default target language

**Errors:**
- Non-existent transcript
- No text
- Not completed status
- Invalid UUID

**Metadata:**
- Preserves existing metadata
- Updates language field

**Edge Cases:**
- Very long text
- Empty text
- Unicode text
- Special characters
- Concurrent translations

## Notes

- Tests use SQLite in-memory database for speed and isolation
- External services (Qdrant, Evolution Cloud) may cause some tests to fail if not configured
- Async tests use pytest-asyncio with auto mode
- Each test function gets a fresh database session
- Files created during tests are automatically cleaned up

## Troubleshooting

### Tests Fail with "Table not found"

Ensure database tables are created. The `db_engine` fixture should handle this automatically.

### Async Tests Fail to Run

Make sure `pytest-asyncio` is installed:
```bash
pip install pytest-asyncio>=0.21.0
```

### Import Errors

Run tests from the `backend` directory:
```bash
cd backend
pytest
```

Or add backend to PYTHONPATH:
```bash
export PYTHONPATH="${PYTHONPATH}:/path/to/backend"
pytest
```

### External Service Errors

Some tests may fail if:
- Qdrant is not running (RAG tests)
- Evolution Cloud API is not accessible (Translation tests)

These tests are designed to handle such cases gracefully by accepting multiple status codes.
