# Quick Start Guide - Backend API Tests

## Installation (One-time setup)

```bash
cd backend
pip install -r requirements-test.txt
```

## Run All Tests

```bash
# Option 1: Using pytest directly
pytest

# Option 2: Using the test runner script
./run_tests.sh
```

## Run Specific Tests

```bash
# Transcript API tests
pytest tests/integration/test_transcripts_api.py

# Summary API tests
pytest tests/integration/test_summaries_api.py

# RAG API tests
pytest tests/integration/test_rag_api.py

# Translation API tests
pytest tests/integration/test_translation_api.py

# Model validation tests
pytest tests/unit/test_models.py
```

## Run with Coverage

```bash
pytest --cov=app --cov-report=html
open htmlcov/index.html  # On macOS
```

## Common Commands

```bash
# Verbose output
pytest -v

# Extra verbose
pytest -vv

# Run specific test class
pytest tests/integration/test_transcripts_api.py::TestTranscriptUpload

# Run specific test
pytest tests/integration/test_transcripts_api.py::TestTranscriptUpload::test_upload_valid_audio_file

# Stop on first failure
pytest -x

# Show local variables on failure
pytest -l

# Run only marked tests
pytest -m integration
```

## Test Runner Script Options

```bash
./run_tests.sh --help          # Show all options
./run_tests.sh --unit          # Run unit tests only
./run_tests.sh --integration   # Run integration tests only
./run_tests.sh --coverage      # Run with coverage report
./run_tests.sh --verbose       # Verbose output
./run_tests.sh --watch         # Watch mode (rerun on changes)
```

## Expected Results

When all tests pass, you should see:
```
========================= 150+ passed in XX.XX s =========================
```

## Troubleshooting

**Import errors?**
```bash
# Make sure you're in the backend directory
cd backend
pytest
```

**Async tests not running?**
```bash
pip install pytest-asyncio>=0.21.0
```

**Database errors?**
Tests use SQLite automatically - no setup needed!

## Next Steps

- Read `TEST_SUMMARY.md` for detailed documentation
- Check `README.md` for testing guide
- Look at test files for examples of how to test endpoints
