# Architecture Decision Records - Feature 3: New Features

**Version:** 1.0.0
**Date:** 2026-02-03

## ADR Index

### System Architecture

| ADR | Title | Status | Date |
|-----|-------|--------|------|
| [ADR-001](./ADR-001-export-architecture.md) | Export Service Architecture | Accepted | 2026-02-03 |
| [ADR-002](./ADR-002-language-detection.md) | Language Detection Approach | Accepted | 2026-02-03 |
| [ADR-003](./ADR-003-speaker-diarization.md) | Speaker Diarization Approach | Accepted | 2026-02-03 |
| [ADR-004](./ADR-004-search-architecture.md) | Global Search Architecture | Accepted | 2026-02-03 |
| [ADR-005](./ADR-005-batch-processing.md) | Batch Processing Strategy | Accepted | 2026-02-03 |
| [ADR-006](./ADR-006-editing-storage.md) | Transcript Editing Storage | Accepted | 2026-02-03 |
| [ADR-007](./ADR-007-version-storage.md) | Version History Implementation | Accepted | 2026-02-03 |
| [ADR-008](./ADR-008-api-design.md) | REST API Design | Accepted | 2026-02-03 |
| [ADR-009](./ADR-009-event-driven.md) | Event-Driven Communication | Accepted | 2026-02-03 |
| [ADR-010](./ADR-010-security.md) | Security Architecture | Accepted | 2026-02-03 |
| [ADR-011](./ADR-011-scalability.md) | Scalability Strategy | Accepted | 2026-02-03 |
| [ADR-012](./ADR-012-observability.md) | Observability and Monitoring | Accepted | 2026-02-03 |

## ADR Categories

### Performance & Scalability
- ADR-004: Search Architecture (Qdrant + PostgreSQL)
- ADR-005: Batch Processing (Redis queue)
- ADR-011: Scalability Strategy

### Integration & Communication
- ADR-009: Event-Driven Communication
- ADR-008: REST API Design

### Data Management
- ADR-006: Editing Storage
- ADR-007: Version History Implementation

### External Services
- ADR-001: Export Architecture
- ADR-002: Language Detection
- ADR-003: Speaker Diarization

### Cross-Cutting Concerns
- ADR-010: Security Architecture
- ADR-012: Observability and Monitoring

## Decision Summary

### Export Formats
| Format | Status | Implementation |
|--------|--------|----------------|
| SRT | MVP | Native Python implementation |
| VTT | MVP | Native Python implementation |
| DOCX | v1.1 | python-docx library |
| TXT | v1.1 | Native Python |
| JSON | v1.1 | Native Python |

### Language Detection
- **Provider:** Cloud.ru Whisper API
- **Approach:** Pre-transcription detection on audio sample
- **Fallback:** User-specified or English default

### Speaker Diarization
- **Approach:** Third-party service integration (deferred to v1.1)
- **Rationale:** High computational cost, specialized ML required

### Search Architecture
- **Primary:** Qdrant vector database for semantic search
- **Secondary:** PostgreSQL full-text for keyword search
- **Ranking:** Custom relevance scoring

### Batch Processing
- **Queue:** Redis with priority queues
- **Concurrency:** Max 3 simultaneous transcriptions
- **Orchestration:** Async job processing

## ADR Template

```markdown
# ADR-XXX: [Title]

## Status
[Proposed | Accepted | Deprecated | Superseded by ADR-XXX]

## Context
[Situation requiring decision]

## Decision Drivers
- [Driver 1]: [Why it matters]
- [Driver 2]: [Why it matters]

## Considered Options
1. [Option A]
2. [Option B]
3. [Option C]

## Decision
[Chosen option] because [rationale]

## Consequences

### Positive
- [Benefit]

### Negative
- [Trade-off]

### Risks
- [Risk]: Mitigation: [approach]

## Related ADRs
- ADR-XXX: [relationship]
```

## ADR Lifecycle

1. **Proposed:** Initial draft for discussion
2. **Accepted:** Decision made and implemented
3. **Deprecated:** No longer recommended but still in use
4. **Superseded:** Replaced by newer decision

## Contribution Guidelines

When creating a new ADR:
1. Use the template above
2. Number sequentially (ADR-001, ADR-002, etc.)
3. Link related ADRs
4. Update this INDEX.md
5. Store in `/docs/features/feature-3-new-features/adr/`

## Review Schedule

- **Quarterly:** Review all Accepted ADRs for continued relevance
- **On Major Changes:** Reconsider related ADRs
- **Deprecated ADRs:** Mark but don't delete (historical record)
