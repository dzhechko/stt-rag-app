# Backend Unit Tests

This directory contains comprehensive unit tests for the backend services.

## Test Structure

```
tests/
├── __init__.py
├── conftest.py
├── README_TESTS.md
└── unit/
    ├── __init__.py
    ├── test_transcription_service.py
    ├── test_summarization_service.py
    ├── test_rag_service.py
    └── test_file_service.py
```

## Test Coverage

### 1. test_transcription_service.py
Tests for the TranscriptionService class covering:

- **Initialization**
  - Valid configuration setup
  - Missing/invalid base URL handling
  - Malformed base URL cleaning
  - HTTP client configuration

- **MP4 to MP3 Conversion**
  - Supported audio formats (no conversion needed)
  - Video format conversion triggering
  - FFmpeg successful conversion
  - FFmpeg failure fallback
  - FFmpeg timeout handling
  - Exception handling during conversion

- **File Size Validation**
  - Max file size calculation
  - Files under limit processing
  - Files over limit chunking

- **Chunk Splitting for Large Files**
  - Chunk size calculation (90% of max)
  - Large file transcription with pydub
  - Large file handling without pydub
  - Progress callback during chunking

- **API Retry Logic**
  - Successful transcription on first attempt
  - Retry on failure with exponential backoff
  - Max retries exceeded handling

- **Error Handling**
  - FileNotFoundError for missing files
  - Network error handling
  - Temporary file cleanup on error

- **Language Parameter Handling**
  - Language parameter passed to API
  - Language parameter stripped of whitespace
  - Auto-detection when language is None/empty

- **Response Formats**
  - JSON format handling
  - Text format handling
  - SRT format handling
  - VTT format handling

### 2. test_summarization_service.py
Tests for the SummarizationService class covering:

- **Initialization**
  - Valid configuration setup
  - Missing/invalid base URL handling

- **Template Types**
  - Meeting template prompt construction
  - Interview template prompt construction
  - Lecture template prompt construction
  - Podcast template prompt construction
  - Unknown template defaults to meeting
  - Template with fields configuration

- **LLM Prompt Construction**
  - Default prompt construction
  - Custom prompt construction
  - Empty fields config handling

- **Token Limit Handling**
  - Small text no chunking
  - Large text triggers chunking
  - Chunk size calculation
  - Large text chunk summarization

- **Async Processing (via Callbacks)**
  - Translation with progress callback
  - Large text translation with progress updates
  - Progress callback error handling

- **Translation Functionality**
  - English to Russian translation
  - Custom model usage
  - Different language pairs
  - Large text splitting for translation

- **Summarization Functionality**
  - Summarization with template
  - Summarization with custom prompt
  - Summarization with custom model
  - Summarization with fields config

- **Large Text Handling**
  - Large text delegation to chunking
  - Chunk summarization logic

- **Error Handling**
  - Summarize API error
  - Translation API error
  - Large text chunk error handling

- **Temperature and Max Tokens**
  - Summarize temperature setting
  - Summarize max tokens setting
  - Translate temperature setting
  - Translate max tokens setting

### 3. test_rag_service.py
Tests for the RAGService class covering:

- **Initialization**
  - Successful Qdrant connection
  - Qdrant connection failure
  - Embeddings 404 fallback to local embeddings

- **Qdrant Integration**
  - Collection creation when not exists
  - Existing collection handling
  - Transcript index deletion
  - Deletion with no client

- **Vector Embedding Generation**
  - Embeddings using Evolution Cloud.ru API
  - Embeddings API failure handling
  - Embeddings dimension check

- **Similarity Search**
  - Vector search only
  - Vector search with transcript filter
  - Vector search with no client
  - Hybrid search (vector + BM25)
  - Main search method

- **Context Window Management**
  - Text splitter initialization
  - Text splitting during indexing

- **Index Transcript**
  - Successful transcript indexing
  - Indexing with progress callback
  - Indexing with metadata
  - Indexing with no Qdrant

- **BM25 Integration**
  - BM25 search with results
  - BM25 search with transcript filter
  - BM25 unavailable handling

- **Error Handling**
  - Search exception handling
  - Index transcript exception handling

### 4. test_file_service.py
Tests for the FileService class covering:

- **Initialization**
  - Directory creation
  - Configuration storage

- **File Validation**
  - Save file with correct extension
  - Unique filename generation with UUID
  - Extension preservation
  - No extension handling
  - Multiple extensions handling

- **Secure Filename Generation**
  - UUID usage for filename
  - Different UUIDs for different files

- **File Storage Operations**
  - File content writing
  - Transcript text file saving
  - Transcript JSON file saving
  - Transcript SRT file saving
  - Transcript directory creation

- **Cleanup Logic**
  - Successful file deletion
  - Non-existent file deletion
  - File deletion with exception
  - Transcript directory deletion
  - Original file cleanup when keep_original is False
  - No cleanup when keep_original is True

- **Transcript Directory Structure**
  - Separate directories for different transcripts

- **Edge Cases**
  - Empty file saving
  - Large file saving
  - File deletion with special characters
  - Unicode content in transcripts

## Running Tests

### Run All Tests
```bash
cd backend
python -m pytest tests/ -v
```

### Run Specific Test File
```bash
python -m pytest tests/unit/test_transcription_service.py -v
```

### Run Specific Test Class
```bash
python -m pytest tests/unit/test_transcription_service.py::TestTranscriptionServiceInitialization -v
```

### Run Specific Test Method
```bash
python -m pytest tests/unit/test_transcription_service.py::TestTranscriptionServiceInitialization::test_initialization_with_valid_config -v
```

### Run with Coverage
```bash
python -m pytest tests/ --cov=app/services --cov-report=html --cov-report=term
```

### Run Tests Matching Pattern
```bash
# Run all tests matching "error" in name
python -m pytest tests/ -k error -v

# Run all tests matching "conversion" in name
python -m pytest tests/ -k conversion -v
```

## Test Dependencies

Tests use `unittest` and `unittest.mock` which are part of the Python standard library. No additional test dependencies are required beyond the main project dependencies.

To run tests with coverage reporting:
```bash
pip install pytest-cov
```

## Mocking Strategy

Tests extensively use `unittest.mock` to external dependencies:

- **Qdrant Client**: Mocked for vector database operations
- **OpenAI Client**: Mocked for API calls (transcription, embeddings, chat)
- **HTTPX Client**: Mocked for HTTP requests
- **File System**: Mocked file operations where appropriate
- **Subprocess**: Mocked FFmpeg calls
- **Configuration**: Mocked settings for test isolation

## Test Principles

1. **Isolation**: Each test is independent and doesn't rely on other tests
2. **Fast**: Tests use mocks to avoid slow I/O operations
3. **Deterministic**: Tests produce consistent results
4. **Comprehensive**: Tests cover success paths, error paths, and edge cases
5. **Maintainable**: Tests are well-organized and documented

## Adding New Tests

When adding new functionality:

1. Create test methods following the `test_` naming convention
2. Use descriptive test method names that describe what is being tested
3. Arrange-Act-Assert pattern:
   - **Arrange**: Set up the test data and mocks
   - **Act**: Call the method being tested
   - **Assert**: Verify the expected behavior
4. Add tests for both success and failure scenarios
5. Test edge cases and boundary conditions

Example:
```python
def test_feature_with_valid_input(self):
    """Test that feature works correctly with valid input"""
    # Arrange
    mock_dependency.return_value = expected_value
    input_data = "valid input"

    # Act
    result = self.service.feature(input_data)

    # Assert
    self.assertEqual(result, expected_result)
    mock_dependency.assert_called_once()
```

## Continuous Integration

These tests are designed to run in CI/CD pipelines:

```yaml
# Example GitHub Actions workflow
- name: Run backend tests
  run: |
    cd backend
    python -m pytest tests/ --cov=app/services --cov-report=xml
```

## Troubleshooting

### Import Errors
If you encounter import errors, ensure the backend directory is in your Python path:
```bash
export PYTHONPATH="${PYTHONPATH}:/path/to/backend"
```

### Mock Configuration
Tests mock the `app.config.settings` module. If tests fail due to configuration issues, check `conftest.py` for mock setup.

### Test Isolation
Each test should clean up after itself. If tests interfere with each other, check for shared state or side effects.
