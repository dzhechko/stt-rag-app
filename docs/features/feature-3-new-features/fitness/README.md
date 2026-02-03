# Architecture Fitness Functions - Feature 3: New Features

**Version:** 1.0.0
**Date:** 2026-02-03

## Overview

This directory contains architecture fitness functions for Feature 3, defining automated checks that the system meets its architectural requirements.

## Fitness Function Categories

| Category | File | Description |
|----------|------|-------------|
| Structural | [structural.md](./structural.md) | Code structure and dependency rules |
| Performance | [performance.md](./performance.md) | Response time and throughput targets |
| Security | [security.md](./security.md) | Security compliance checks |
| API Compliance | [api-compliance.md](./api-compliance.md) | API contract compliance |

## What are Fitness Functions?

**Architecture Fitness Function** = Objective Metric + Threshold + Automation

**Example:**
```yaml
Name: Export Response Time
Category: Performance
Rule: P95 export time < 10 seconds for 10K-word transcripts
Threshold: 10 seconds
Test: Load test with various transcript sizes
Tools: k6, pytest-benchmark
Frequency: Every build
```

## Critical Fitness Functions

### P0 (Must Pass)
| ID | Name | Threshold | Category |
|----|------|-----------|----------|
| FF-001 | Bounded Context Independence | 0 violations | Structural |
| FF-002 | Export Performance | P95 < 10s | Performance |
| FF-003 | Search Performance | P95 < 500ms | Performance |
| FF-004 | API Security | 100% endpoints authenticated | Security |
| FF-005 | No Secrets in Code | 0 violations | Security |

### P1 (Should Pass)
| ID | Name | Threshold | Category |
|----|------|-----------|----------|
| FF-006 | Language Detection Accuracy | >= 95% | Performance |
| FF-007 | Batch Processing Throughput | 3 concurrent | Performance |
| FF-008 | API Rate Limiting | 100 req/min | API Compliance |
| FF-009 | Test Coverage | >= 80% | Structural |
| FF-010 | Aggregate Size | <= 7 entities | Structural |

## Implementation

### Fitness Function Template

```yaml
Name: [Descriptive name]
Category: Structural | Performance | Security | API Compliance
Related ADR: ADR-XXX
Rule: [Clear statement of what must be true]
Threshold: [Numeric or boolean threshold]
Test: [How to verify]
Tools: [Automation tools]
Frequency: Every commit | Daily | Weekly
Owner: [Team/person responsible]
Alert: [How to alert on failure]
```

### Example: Python Implementation

```python
# tests/fitness/test_export_performance.py
import pytest
from app.services.export_service import ExportService

@pytest.mark.fitness("FF-002")
def test_export_performance_10k_words(benchmark):
    """
    FF-002: Export Performance
    Threshold: P95 < 10 seconds for 10K-word transcripts
    Category: Performance
    """
    transcript = create_test_transcript(word_count=10000)
    export_service = ExportService()

    # Benchmark the export
    result = benchmark(
        export_service.export,
        transcript,
        ExportFormat.SRT,
        ExportOptions()
    )

    # Assert threshold
    assert result.duration < 10.0, \
        f"Export took {result.duration}s, exceeds 10s threshold"
```

## Continuous Integration

### GitHub Actions Workflow

```yaml
name: Fitness Functions

on: [pull_request, push]

jobs:
  fitness:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run structural checks
        run: pytest tests/fitness/test_structural.py
      - name: Run performance checks
        run: pytest tests/fitness/test_performance.py
      - name: Run security checks
        run: pytest tests/fitness/test_security.py
      - name: Run API compliance checks
        run: pytest tests/fitness/test_api_compliance.py
```

## Fitness Dashboard

### Monthly Fitness Report

```markdown
# Architecture Fitness Report - 2026-02

## Summary

| Category | Pass | Fail | Trend |
|----------|------|------|-------|
| Structural | 5/5 | 0 | ✅ Stable |
| Performance | 3/4 | 1 | ⚠️ Degraded |
| Security | 5/5 | 0 | ✅ Stable |
| API Compliance | 4/4 | 0 | ✅ Stable |

## Failing Checks

### FF-006: Language Detection Accuracy
- **Status:** FAIL
- **Current:** 93% accuracy
- **Threshold:** >= 95%
- **Action:** Investigate detection model, consider retraining

## Improvements

### FF-002: Export Performance
- **Previous:** P95 = 12.3s
- **Current:** P95 = 8.7s
- **Improvement:** 29% faster after optimization
```

## Fitness Function Lifecycle

1. **Define:** Create fitness function based on ADR or NFR
2. **Implement:** Write automated test
3. **Integrate:** Add to CI/CD pipeline
4. **Monitor:** Track results over time
5. **Evolve:** Adjust thresholds as system matures

## Related Documentation

- [Architecture Decision Records](../adr/) - Technical decisions
- [Non-Functional Requirements](../PRD.md#non-functional-requirements) - Performance targets
- [Test Scenarios](../tests/) - Acceptance criteria
