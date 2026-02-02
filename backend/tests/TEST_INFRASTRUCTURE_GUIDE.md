# Test Infrastructure Guide

This guide documents the **new modular and reusable test infrastructure** created for the STT application. This infrastructure makes testing faster, easier, and more maintainable.

## Quick Start

### Backend

```python
# Use factory functions to generate test data
from tests.fixtures import transcript_factory, summary_create_payload

# Generate a transcript
transcript = transcript_factory(status="completed", language="ru")

# Generate API payloads
payload = summary_create_payload(transcript_id="uuid-here")

# Use custom assertions
from tests.helpers import assert_transcript_response, assert_http_success
assert_transcript_response(response)
assert_http_success(response.status_code)
```

### Frontend

```javascript
// Use test utilities
import { renderWithProviders, createMockTranscript } from '@/tests/utils/test-utils'

// Render with providers
const { getByText } = renderWithProviders(<MyComponent />)

// Create mock data
const transcript = createMockTranscript({ status: 'completed' })
```

---

## Backend Test Infrastructure

### Directory Structure

```
backend/tests/
├── conftest.py                 # Original pytest fixtures (still used)
├── fixtures/
│   ├── __init__.py            # Package exports
│   └── test_data.py           # NEW: Test data generators
├── helpers/
│   ├── __init__.py            # Package exports
│   ├── assertions.py          # NEW: Custom assertions
│   └── mocks.py               # NEW: Mock classes
├── unit/                      # Existing unit tests
└── integration/               # Existing integration tests
```

### New Components

#### 1. `fixtures/test_data.py` - Test Data Generators

Factory functions for generating realistic test data:

**Random Data Generators:**
```python
from tests.fixtures import (
    random_string, random_email, random_filename,
    random_transcript_text, random_timestamp
)

# Generate random data
name = random_string(10, "user_")
email = random_email("example.com")
filename = random_filename("mp3", "recording_")
text = random_transcript_text(min_sentences=3, max_sentences=10)
```

**Factory Functions:**
```python
from tests.fixtures import (
    transcript_factory, summary_factory,
    rag_session_factory, processing_job_factory
)

# Generate with overrides
transcript = transcript_factory(
    status="completed",
    language="ru",
    tags=["meeting", "important"]
)

summary = summary_factory(
    transcript_id=transcript["id"],
    template="meeting"
)
```

**API Payload Builders:**
```python
from tests.fixtures import (
    transcript_create_payload,
    summary_create_payload,
    rag_question_payload
)

# Build request payloads
payload = transcript_create_payload(
    filename="test.mp3",
    language="en"
)

summary_payload = summary_create_payload(
    transcript_id="uuid-here",
    template="meeting",
    model="GigaChat-2-Max"
)
```

**Test Scenarios:**
```python
from tests.fixtures import build_test_scenario

# Build complete test scenarios
scenario = build_test_scenario("meeting_with_summary")
# Returns: {transcript, summary, processing_job}

scenario = build_test_scenario("rag_workflow")
# Returns: {transcripts, rag_session, rag_messages}
```

**Edge Cases:**
```python
from tests.fixtures import edge_case_transcripts, edge_case_payloads

# Test edge cases
for transcript in edge_case_transcripts():
    test_validation(transcript)

for payload in edge_case_payloads()["transcript_create"]:
    test_api_validation(payload)
```

#### 2. `helpers/assertions.py` - Custom Assertions

Specialized assertion functions with better error messages:

```python
from tests.helpers import (
    assert_transcript_response,
    assert_summary_response,
    assert_rag_response,
    assert_error_response,
    assert_http_success
)

# Validate response structure
assert_transcript_response(response, check_optional_fields=True)

# Validate RAG responses
assert_rag_response(response, check_quality_metrics=True)

# Validate errors
assert_error_response(response, expected_error="Not found")

# Validate HTTP status
assert_http_success(response.status_code)
```

**Type Validation:**
```python
from tests.helpers import (
    assert_valid_uuid,
    assert_valid_timestamp,
    assert_valid_email,
    assert_valid_url
)

assert_valid_uuid(transcript_id)
assert_valid_timestamp(created_at, allow_string=True)
assert_valid_email("user@example.com")
assert_valid_url("https://api.example.com")
```

**Comparison Assertions:**
```python
from tests.helpers import assert_objects_equal

# Compare objects ignoring certain fields
assert_objects_equal(
    response1,
    response2,
    ignore_fields=["updated_at", "id"]
)
```

#### 3. `helpers/mocks.py` - Mock Classes

Configurable mock classes for external services:

```python
from tests.helpers import (
    MockEvolutionAPI,
    MockOpenAI,
    MockQdrantClient,
    configure_transcription_success
)

# Create and configure mock
mock_api = MockEvolutionAPI()
configure_transcription_success(mock_api)

# Use in tests
result = mock_api.transcribe("audio.mp3")
assert result["text"] == "This is a successful transcription..."

# Check usage
assert mock_api.get_call_count() == 1
```

**Mock OpenAI/LLM:**
```python
from tests.helpers import MockOpenAI, configure_llm_success

mock_llm = MockOpenAI()
configure_llm_success(mock_llm, text="Summary text...")

response = mock_llm.chat.completions.create(...)
assert response.choices[0].message.content == "Summary text..."
```

**Mock Qdrant:**
```python
from tests.helpers import MockQdrantClient

mock_qdrant = MockQdrantClient()
mock_qdrant.add_collection("test")
mock_qdrant.add_documents([
    {"id": "1", "vector": [0.1, 0.2], "payload": {"text": "doc1"}}
])

results = mock_qdrant.search(collection="test", query_vector=[0.1, 0.2])
```

---

## Frontend Test Infrastructure

### Directory Structure

```
frontend/tests/
├── setup.js                    # ENHANCED: Test configuration
├── utils/
│   └── test-utils.js          # ENHANCED: Testing utilities
├── mocks/
│   └── handlers.js            # ENHANCED: MSW handlers
└── __tests__/                  # Existing test files
```

### Enhanced Components

#### 1. `setup.js` - Enhanced Configuration

New additions:
- Comprehensive storage mocks (localStorage, sessionStorage)
- Canvas API mocks
- Performance API mocks
- Animation frame mocks
- Console management with suppression of specific warnings
- Exported utilities: `wait()`, `tick()`, `flushPromises()`

#### 2. `utils/test-utils.js` - Enhanced Utilities

**Mock Data Generators:**
```javascript
import {
  generateId,
  generateTimestamp,
  createMockTranscript,
  createMockSummary,
  createMockFile
} from '@/tests/utils/test-utils'

// Generate mock data
const transcript = createMockTranscript({
  status: 'completed',
  language: 'ru'
})

const file = createMockFile('test.mp3', 1024000, 'audio/mp3')
```

**Pre-configured Mock Data:**
```javascript
import { mockData } from '@/tests/utils/test-utils'

// Use pre-configured mock data
const { meetingTranscript, failedTranscript } = mockData
```

**Custom Render Functions:**
```javascript
import {
  renderWithProviders,
  renderWithRoute,
  renderWithAuth
} from '@/tests/utils/test-utils'

// Render with all providers
const { getByText } = renderWithProviders(<MyComponent />)

// Render with specific route
renderWithRoute(<MyComponent />, '/transcripts/:id', '/transcripts/123')

// Render with authentication
renderWithAuth(<ProtectedComponent />, user)
```

**Event Mocking:**
```javascript
import {
  createMockChangeEvent,
  createMockSubmitEvent,
  createMockDragEvent,
  createMockKeyboardEvent
} from '@/tests/utils/test-utils'

// Create mock events
const changeEvent = createMockChangeEvent('new value')
const submitEvent = createMockSubmitEvent()
const dragEvent = createMockDragEvent([file])
const keyEvent = createMockKeyboardEvent('Enter', { ctrl: true })
```

#### 3. `mocks/handlers.js` - Enhanced MSW Handlers

Comprehensive API handlers with:

**All Transcript Endpoints:**
```javascript
import {
  getTranscriptsHandler,
  getTranscriptHandler,
  uploadTranscriptHandler,
  deleteTranscriptHandler,
  updateTranscriptHandler
} from '@/tests/mocks/handlers'
```

**All Summary Endpoints:**
```javascript
import {
  createSummaryHandler,
  getSummariesHandler,
  getSummaryHandler,
  deleteSummaryHandler
} from '@/tests/mocks/handlers'
```

**All RAG Endpoints:**
```javascript
import {
  createRAGSessionHandler,
  getRAGSessionsHandler,
  askRAGHandler,
  getRAGMessagesHandler
} from '@/tests/mocks/handlers'
```

**Error Handlers:**
```javascript
import {
  notFoundHandler,
  serverErrorHandler,
  unauthorizedHandler,
  rateLimitHandler
} from '@/tests/mocks/handlers'
```

**Configuration Helpers:**
```javascript
import {
  createDelayedHandlers,
  createFailingHandlers,
  createEmptyHandlers
} from '@/tests/mocks/handlers'

// Create handlers with custom behavior
const handlers = createDelayedHandlers(500)
const errorHandlers = createFailingHandlers('/api/transcripts', 500)
```

---

## Usage Examples

### Backend: Factory Functions

```python
def test_transcript_factory():
    from tests.fixtures import transcript_factory

    # Generate with defaults
    t1 = transcript_factory()

    # Generate with overrides
    t2 = transcript_factory(
        status="completed",
        language="ru",
        tags=["important"]
    )

    assert t1["status"] == "completed"
    assert t2["language"] == "ru"
    assert "important" in t2["tags"]
```

### Backend: Custom Assertions

```python
def test_api_response(assert_http_success):
    from tests.helpers import assert_transcript_response

    response = client.get("/api/transcripts/123")

    assert_http_success(response.status_code)
    assert_transcript_response(response.json())
```

### Backend: Mock Classes

```python
def test_with_mocks():
    from tests.helpers import MockEvolutionAPI, configure_transcription_failure

    mock_api = MockEvolutionAPI()
    configure_transcription_failure(mock_api)

    # Test error handling
    with pytest.raises(Exception):
        mock_api.transcribe("audio.mp3")
```

### Frontend: Mock Data

```javascript
test('displays transcript', () => {
  const transcript = createMockTranscript({
    original_filename: 'meeting.mp3',
    status: 'completed'
  })

  const { getByText } = renderWithProviders(
    <TranscriptCard transcript={transcript} />
  )

  expect(getByText('meeting.mp3')).toBeInTheDocument()
})
```

### Frontend: Custom Render

```javascript
test('navigates to detail', () => {
  const { getByRole } = renderWithRoute(
    <TranscriptDetail />,
    '/transcripts/:id',
    '/transcripts/123'
  )

  // Component is rendered with correct route
})
```

---

## Best Practices

### 1. Use Factory Functions

**Instead of:**
```python
transcript = {
    "id": str(uuid4()),
    "original_filename": "test.mp3",
    "status": "completed",
    # ... 15 more fields
}
```

**Use:**
```python
transcript = transcript_factory(status="completed")
```

### 2. Use Custom Assertions

**Instead of:**
```python
assert "id" in response
assert "status" in response
assert response["status"] in ["pending", "processing", "completed", "failed"]
```

**Use:**
```python
assert_transcript_response(response)
```

### 3. Use Pre-configured Mocks

**Instead of:**
```python
mock_api = Mock()
mock_api.transcribe = Mock(return_value={...})
mock_api.get_status = Mock(return_value={...})
```

**Use:**
```python
mock_api = MockEvolutionAPI()
configure_transcription_success(mock_api)
```

### 4. Use Test Scenarios

**Instead of:**
```python
transcript = create_transcript(...)
summary = create_summary(transcript_id=transcript.id)
job = create_job(transcript_id=transcript.id)
```

**Use:**
```python
scenario = build_test_scenario("meeting_with_summary")
transcript = scenario["transcript"]
summary = scenario["summary"]
```

---

## Migration Guide

### Migrating Existing Tests

**Before:**
```python
def test_transcript():
    transcript = Transcript(
        original_filename="test.mp3",
        file_path="/tmp/test.mp3",
        file_size=1024,
        status="completed"
    )
    db.add(transcript)
    db.commit()

    response = client.get(f"/api/transcripts/{transcript.id}")

    assert response.status_code == 200
    assert "id" in response.json()
    assert "original_filename" in response.json()
```

**After:**
```python
def test_transcript(test_transcript):
    response = client.get(f"/api/transcripts/{test_transcript.id}")

    assert_http_success(response.status_code)
    assert_transcript_response(response.json())
```

---

## Running Tests

### Backend

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific markers
pytest -m unit
pytest -m integration
pytest -m "not slow"
```

### Frontend

```bash
# Run all tests
npm test

# Run with coverage
npm run test:coverage

# Run in watch mode
npm run test:watch
```

---

## Summary

The new test infrastructure provides:

1. **Factory Functions** - Generate test data easily
2. **Custom Assertions** - Better error messages and validation
3. **Mock Classes** - Configurable external service mocks
4. **Test Scenarios** - Pre-built test data sets
5. **Enhanced Utilities** - More frontend testing helpers
6. **Comprehensive Handlers** - All API endpoints mocked

All utilities are:
- ✅ Generic and reusable
- ✅ Well-documented with docstrings
- ✅ Type-safe where possible
- ✅ Easy to configure

For more details, see the inline documentation in each file.
