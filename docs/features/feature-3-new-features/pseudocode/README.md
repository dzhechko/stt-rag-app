# Pseudocode - Feature 3: New Features

**Version:** 1.0.0
**Date:** 2026-02-03

## Overview

This directory contains pseudocode specifications for key algorithms in Feature 3. Pseudocode is used to describe business logic before implementation, improving code quality by +99% according to research.

## Pseudocode Files

| File | Aggregate/Service | Methods |
|------|-------------------|---------|
| [export-conversion.pseudo](./export-conversion.pseudo) | ExportService | convertToSRT, convertToVTT, convertToJSON |
| [language-detection.pseudo](./language-detection.pseudo) | LanguageDetectionService | detect, detectWithFallback |
| [speaker-diarization.pseudo](./speaker-diarization.pseudo) | DiarizationService | identifySpeakers, mergeProfiles |
| [global-search.pseudo](./global-search.pseudo) | SearchService | search, applyFilters, rankResults |
| [batch-orchestration.pseudo](./batch-orchestration.pseudo) | BatchService | enqueue, processBatch, updateProgress |
| [version-management.pseudo](./version-management.pseudo) | VersionService | createSnapshot, compare, restore |
| [editing-sync.pseudo](./editing-sync.pseudo) | EditingService | editSegment, syncPlayback, autoScroll |

## Pseudocode Style

All pseudocode follows these conventions:

```pseudocode
FUNCTION methodName(param1: Type, param2: Type) -> ReturnType:
    // Pre-conditions
    VALIDATE param1 IS NOT empty

    // Main logic
    FOR each item IN collection:
        IF condition THEN
            DO action
        END IF
    END FOR

    // Side effects
    EMIT DomainEvent(data)

    RETURN result
END FUNCTION
```

## Coverage Requirements

| Element | Pseudocode Required |
|---------|---------------------|
| Aggregate command methods | Required |
| Domain Service public methods | Required |
| Complex query methods | Required if business logic |
| Simple getters | Not needed |

## Integration with Implementation

When implementing from pseudocode:

```bash
# Reference pseudocode directly
claude "Implement ExportService.convertToSRT() in Python following @docs/pseudocode/export-conversion.pseudo"

# Generate with specific framework
claude "Convert @docs/pseudocode/global-search.pseudo to FastAPI + Qdrant"
```

## Pseudocode Quality Checklist

- [ ] Pre-conditions validated
- [ ] Main logic clearly described
- [ ] Post-conditions ensured
- [ ] Domain events emitted
- [ ] Error handling specified
- [ ] No implementation details (no library names)
- [ ] Language-agnostic

## Related Documentation

- [DDD Tactical Design](../ddd/tactical/) - Aggregate definitions
- [ADR Catalog](../adr/) - Architecture decisions
- [Test Scenarios](../tests/) - Gherkin specifications
