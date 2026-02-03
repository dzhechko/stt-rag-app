# DDD Strategic Design - Feature 3: New Features

**Version:** 1.0.0
**Date:** 2026-02-03

## Overview

This directory contains Domain-Driven Design strategic documentation for Feature 3, defining bounded contexts, their relationships, and the ubiquitous language shared across teams.

## Documents

| Document | Description |
|----------|-------------|
| [bounded-contexts.md](./bounded-contexts.md) | Definitions and responsibilities of each bounded context |
| [context-map.md](./context-map.md) | Visual map of context relationships and integration patterns |
| [ubiquitous-language.md](./ubiquitous-language.md) | Shared domain vocabulary and definitions |
| [domain-events.md](./domain-events.md) | Strategic domain events across contexts |

## Bounded Contexts Overview

### Core Contexts
Provide competitive advantage and require deep domain expertise.

1. **Language Detection** - Auto-detect spoken language before transcription
2. **Global Search** - Search across all transcripts with intelligent ranking
3. **Transcript Editing** - Edit transcripts with synchronized playback

### Supporting Contexts
Support core contexts but don't provide unique differentiation.

1. **Export** - Multi-format transcript export (SRT, VTT, DOCX, TXT, JSON)
2. **Speaker Diarization** - Identify and label different speakers
3. **Version History** - Track transcript changes over time
4. **API Access** - REST API for programmatic access

### Generic Contexts
Commodity capabilities that can be bought or outsourced.

1. **Batch Processing** - Multi-file upload and queue management

## Context Integration Patterns

| Pattern | Contexts | Description |
|---------|----------|-------------|
| **Partnership** | Transcript Editing + Version History | Tight collaboration, same team |
| **Customer-Supplier** | Export + Transcript | Export serves Transcript's needs |
| **Open Host Service** | API Access + All contexts | API exposes all capabilities |
| **Anticorruption Layer** | Speaker Diarization + Cloud.ru API | Shield from external changes |

## Domain Model Summary

### Core Entities
- **Transcript** - The central entity, all contexts operate on it
- **Speaker** - Identified person in audio (Diarization context)
- **SearchResult** - Ranked match from search operation

### Key Value Objects
- **Language** - Detected language with confidence score
- **TimeRange** - Audio segment timestamps
- **ExportFormat** - Target export format specification

### Strategic Events
- **TranscriptCreated** - New transcript available
- **LanguageDetected** - Language detection complete
- **ExportCompleted** - Export file ready
- **VersionCreated** - New version snapshot

## Quick Reference

### Subdomain Classification

| Context | Type | Rationale |
|---------|------|-----------|
| Language Detection | Core | Unique value, complex ML integration |
| Global Search | Core | User retention, complex ranking |
| Transcript Editing | Core | User engagement, complex sync logic |
| Export | Supporting | Necessary but not unique |
| Speaker Diarization | Supporting | Enhanced value, can be external |
| Version History | Supporting | User confidence, can be deferred |
| API Access | Supporting | Integration capability |
| Batch Processing | Generic | Commodity, can use SaaS |

### Team Alignment

| Context | Primary Owner | Collaborators |
|---------|---------------|---------------|
| Language Detection | ML Engineer | Backend Dev |
| Global Search | Backend Dev | ML Engineer |
| Transcript Editing | Frontend Dev | Backend Dev |
| Export | Backend Dev | QA |
| Speaker Diarization | ML Engineer | Backend Dev |
| Version History | Backend Dev | Database Admin |
| API Access | Backend Dev | DevOps |
| Batch Processing | Backend Dev | DevOps |

## Next Steps

After understanding strategic design:
1. Review [Tactical Design](../tactical/) for detailed aggregates and entities
2. Check [Architecture Decisions](../../adr/) for technical choices
3. Review [C4 Diagrams](../../c4/) for system architecture
