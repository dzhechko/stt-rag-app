# Testing and CI/CD Guide

This document provides comprehensive information about the testing infrastructure and CI/CD pipelines for the STT App project.

## Table of Contents

- [Overview](#overview)
- [Local Testing](#local-testing)
- [E2E Testing](#e2e-testing)
- [CI/CD Pipelines](#cicd-pipelines)
- [Test Reports](#test-reports)
- [Environment Setup](#environment-setup)

## Overview

The project includes comprehensive testing at multiple levels:

- **Backend Tests**: Python pytest with coverage
- **Frontend Tests**: Vitest with coverage
- **E2E Tests**: Playwright for full workflow testing
- **Code Quality**: Linting, formatting, and security scanning

## Local Testing

### Prerequisites

```bash
# Install Node.js dependencies
cd frontend
npm install

# Install Python dependencies
cd backend
pip install -r requirements.txt
```

### Backend Tests

```bash
# Run all backend tests
cd backend
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test categories
pytest -m unit              # Unit tests only
pytest -m integration       # Integration tests only
pytest -m "not slow"        # Skip slow tests

# Run with verbose output
pytest -v

# Run in parallel
pytest -n auto
```

### Frontend Tests

```bash
# Run all frontend tests
cd frontend
npm test

# Run with coverage
npm run test:coverage

# Watch mode
npm run test:watch

# UI mode
npm run test:ui
```

### Code Quality Checks

```bash
# Backend linting
cd backend
black --check app/          # Check formatting
isort --check-only app/     # Check import sorting
flake8 app/                 # PEP8 compliance
mypy app/                   # Type checking
ruff check app/             # Fast linter

# Frontend linting
cd frontend
npm run lint                # ESLint
npm run format:check        # Prettier check
```

## E2E Testing

### Running E2E Tests

```bash
# Install Playwright browsers
npx playwright install --with-deps

# Run all E2E tests
npx playwright test

# Run specific test file
npx playwright test e2e/specs/upload.spec.ts

# Run with UI
npx playwright test --ui

# Debug mode
npx playwright test --debug

# Run specific browsers
npx playwright test --project=chromium
npx playwright test --project=firefox
npx playwright test --project=webkit

# Run in parallel
npx playwright test --workers=4

# Run with shard
npx playwright test --shard=1/4
```

### E2E Test Structure

```
e2e/
├── specs/
│   ├── upload.spec.ts           # Upload workflow tests
│   ├── transcription.spec.ts    # Transcription workflow tests
│   ├── rag.spec.ts              # RAG chat workflow tests
│   └── summaries.spec.ts        # Summaries workflow tests
├── fixtures/
│   └── test-fixtures.ts         # Test fixtures and timeouts
├── global-setup.ts              # Global test setup
├── global-teardown.ts           # Global test teardown
└── playwright.config.ts         # Playwright configuration
```

### E2E Test Scenarios

#### Upload Tests (`upload.spec.ts`)
- Navigate to upload page
- Display upload zone with drag and drop
- File selection dialog
- Language selector
- Upload button state
- File format validation
- Upload progress indicator
- Multiple file uploads

#### Transcription Tests (`transcription.spec.ts`)
- Display transcripts list
- Filter by status
- Filter by language
- Expand/collapse transcript text
- Navigate to detail page
- Switch view modes (text, json, srt)
- Export transcripts
- Delete transcripts

#### RAG Tests (`rag.spec.ts`)
- Navigate to RAG chat
- Display chat input
- Submit questions
- Receive answers with metrics
- Display sources
- Copy answers/sources
- Chat history
- RAG sessions
- Settings panel

#### Summaries Tests (`summaries.spec.ts`)
- Display summaries section
- Create new summary
- Select models and templates
- Display with markdown rendering
- Expand/collapse summaries
- Copy summaries
- Loading states

## CI/CD Pipelines

### Workflow Files

```
.github/workflows/
├── test.yml                # Unified test pipeline
├── test-backend.yml        # Backend-specific tests
├── test-frontend.yml       # Frontend-specific tests
├── test-e2e.yml            # E2E tests
└── lint.yml                # Code quality checks
```

### Unified Test Pipeline (`test.yml`)

Triggers on:
- Push to main/develop/staging branches
- Pull requests to main/develop/staging
- Manual workflow dispatch

Jobs:
1. **backend-unit**: Unit tests with coverage
2. **backend-integration**: Integration tests
3. **frontend-unit**: Unit tests with coverage
4. **e2e**: End-to-end tests (sharded)
5. **code-quality**: Linting and formatting checks
6. **security**: Security scanning
7. **coverage-report**: Merge coverage reports
8. **notify**: Send notifications on failure

### Backend Tests Pipeline (`test-backend.yml`)

Multi-environment testing (dev, staging) across Python versions (3.10, 3.11, 3.12).

Features:
- Parallel test execution
- Coverage reporting to Codecov
- JUnit XML output
- Artifact collection
- Code quality checks (black, isort, flake8, mypy, pylint)
- Security scanning (bandit, safety, Trivy)

### Frontend Tests Pipeline (`test-frontend.yml`)

Multi-version Node.js testing (18, 20, 21).

Features:
- Unit tests with Vitest
- Coverage reporting
- ESLint and Prettier checks
- Type checking
- Bundle size analysis
- Security scanning (npm audit, Snyk)

### E2E Tests Pipeline (`test-e2e.yml`)

Sharded test execution (4 shards) for parallel testing.

Features:
- Multi-browser testing (Chromium, Firefox, WebKit)
- Visual regression tests
- Performance tests (Lighthouse)
- Screenshot and video capture on failure
- Merged test reports

### Lint Pipeline (`lint.yml`)

Comprehensive code quality checks:
- Backend: Black, isort, ruff, flake8, mypy, pylint, bandit
- Frontend: ESLint, Prettier, Stylelint, TypeScript
- Dockerfiles: Hadolint
- YAML: yamllint
- Markdown: markdownlint
- Security: Trivy, CodeQL
- Dependencies: Safety, npm audit

### Multi-Environment Testing

All pipelines support multiple environments:
- **dev**: Development environment
- **staging**: Staging environment
- **production**: Production environment (on manual trigger)

Configure via workflow inputs:
```yaml
environment:
  description: 'Target environment'
  type: choice
  options: ['dev', 'staging', 'production']
```

### Parallel Test Execution

- Backend tests: `pytest -n auto`
- Frontend tests: Vitest parallel mode
- E2E tests: 4 shards with 4 workers each
- GitHub Actions: Matrix strategy for multiple versions

### Coverage Reporting

Coverage is reported to:
- **Codecov**: Backend and frontend coverage
- **GitHub Actions Artifacts**: HTML reports
- **Pull Request Comments**: Coverage summaries

Coverage thresholds:
- Statements: 50%
- Branches: 50%
- Functions: 50%
- Lines: 50%

### Artifact Collection

Artifacts are retained for 7 days:
- Test results (JUnit, JSON)
- Coverage reports (HTML, XML)
- Screenshots and videos (on failure)
- Lint reports
- Security scan results

### Notifications

Notifications are sent on:
- Pipeline failure
- Test failures
- Security vulnerabilities

Configure notification channels:
- Slack webhooks
- Email notifications
- Discord webhooks
- GitHub Issues (auto-created on failure)

## Test Reports

### Viewing Reports

#### Local Reports

```bash
# Backend coverage
open backend/htmlcov/index.html

# Frontend coverage
open frontend/coverage/index.html

# E2E test report
npx playwright show-report
```

#### CI/CD Reports

Reports are available as GitHub Actions artifacts:
1. Go to the Actions tab
2. Select a workflow run
3. Download artifacts from the bottom of the page

### Coverage Badges

Add to your README.md:

```markdown
[![Backend Coverage](https://codecov.io/gh/YOUR_USERNAME/STT-app/branch/main/graph/badge.svg)](https://codecov.io/gh/YOUR_USERNAME/STT-app)
[![Frontend Coverage](https://codecov.io/gh/YOUR_USERNAME/STT-app/branch/main/graph/badge.svg)](https://codecov.io/gh/YOUR_USERNAME/STT-app)
```

## Environment Setup

### GitHub Secrets

Required secrets for CI/CD:

```bash
# Codecov
CODECOV_TOKEN: your_codecov_token

# Snyk (optional)
SNYK_TOKEN: your_snyk_token

# Lighthouse CI (optional)
LHCI_GITHUB_APP_TOKEN: your_lhci_token

# Notification webhooks (optional)
SLACK_WEBHOOK_URL: your_slack_webhook
DISCORD_WEBHOOK_URL: your_discord_webhook
```

### Local Environment Variables

Create a `.env.test` file in both frontend and backend:

**Backend (.env.test):**
```env
DATABASE_URL=postgresql://test_user:test_password@localhost:5432/test_db
QDRANT_URL=http://localhost:6333
EVOLUTION_API_KEY=test_key
EVOLUTION_BASE_URL=https://api.example.com
SECRET_KEY=test_secret_key
ENVIRONMENT=test
```

**Frontend (.env.test):**
```env
VITE_API_URL=http://localhost:8000/api
VITE_ENVIRONMENT=test
```

### Docker Services for Testing

```bash
# Start test services
docker-compose -f docker-compose.test.yml up -d

# Run tests
npm test

# Stop services
docker-compose -f docker-compose.test.yml down
```

## Best Practices

### Writing Tests

1. **Unit Tests**: Test individual functions and classes
2. **Integration Tests**: Test API endpoints and database interactions
3. **E2E Tests**: Test complete user workflows
4. **Keep Tests Independent**: Each test should run in isolation
5. **Use Descriptive Names**: Test names should describe what they test
6. **Mock External Dependencies**: Avoid external API calls in tests

### Test Organization

```
backend/tests/
├── unit/               # Unit tests
│   ├── test_models.py
│   ├── test_services.py
│   └── test_utils.py
├── integration/        # Integration tests
│   ├── test_api.py
│   └── test_database.py
└── conftest.py        # Test fixtures
```

### Continuous Improvement

- Regularly update test dependencies
- Monitor test execution time
- Remove or refactor slow tests
- Maintain high coverage (>80%)
- Fix flaky tests promptly
- Review and update test cases regularly

## Troubleshooting

### Common Issues

1. **Tests timeout**: Increase timeout in test configuration
2. **Port conflicts**: Use different ports for test services
3. **Database errors**: Ensure test database is properly initialized
4. **Browser not found**: Install Playwright browsers (`npx playwright install`)
5. **Coverage not generating**: Check coverage configuration

### Debugging Tips

- Run tests with verbose output (`-v` flag)
- Use debug mode for E2E tests (`--debug`)
- Check test logs in GitHub Actions
- Review screenshots and videos for E2E failures
- Use `pdb.set_trace()` or `breakpoint()` for Python debugging
- Use `console.log()` or `debugger` for JavaScript debugging

## Additional Resources

- [pytest Documentation](https://docs.pytest.org/)
- [Vitest Documentation](https://vitest.dev/)
- [Playwright Documentation](https://playwright.dev/)
- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Codecov Documentation](https://docs.codecov.com/)
