# C4 Model - System Context

**Feature:** Performance Optimizations
**Version:** 1.0
**Date:** 2026-02-03

---

## System Context Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                  User                                       │
│                                                                             │
│  - Uploads audio files                                                     │
│  - Views transcripts                                                       │
│  - Monitors processing progress                                            │
│  - Searches transcripts (RAG)                                              │
└────────────────────────────────────┬────────────────────────────────────────┘
                                     │
                                     │ HTTPS
                                     │
┌────────────────────────────────────▼────────────────────────────────────────┐
│                           STT Application System                           │
│                                                                             │
│  A speech-to-text application with performance optimizations:                │
│  - Multi-level caching (L1/L2/L3)                                          │
│  - Parallel chunk processing                                               │
│  - Async job queue (Celery)                                                │
│  - HTTP/2 connection pooling                                               │
│  - Database query optimization                                             │
│  - Frontend code splitting                                                 │
│  - CDN for static assets                                                   │
└───────────┬─────────────────────────────────────────────────────┬───────────┤
            │                                                     │
            │ REST API                                            │
            ▼                                                     │
┌─────────────────────────────────────┐                           │
│        Cloud.ru API                 │                           │
│                                     │                           │
│  - Whisper Large v3 (STT)           │                           │
│  - GigaChat (Summarization)         │                           │
│  - GigaChat (Translation)           │                           │
│  - No embeddings endpoint           │                           │
└─────────────────────────────────────┘                           │
                                                                    │
┌───────────────────────────────────────────────────────────────────┤
│                              External Systems                       │
│                                                                    │
│  ┌─────────────┐   ┌─────────────┐   ┌─────────────┐             │
│  │   CDN       │   │   Redis     │   │  Celery     │             │
│  │ (Optional)  │   │  (Cache)    │   │  (Queue)    │             │
│  └─────────────┘   └─────────────┘   └─────────────┘             │
└────────────────────────────────────────────────────────────────────┘
```

---

## System Descriptions

### STT Application System

**Description:**
A speech-to-text web application that transcribes audio files using Cloud.ru's Whisper API. The system has been optimized for performance with parallel processing, multi-level caching, and async job queues.

**Primary Functions:**
1. Accept audio file uploads (MP3, MP4, WAV, etc.)
2. Transcribe audio using Whisper Large v3
3. Generate summaries of transcripts
4. Translate transcripts between languages
5. Enable semantic search (RAG) on transcripts
6. Store and manage transcripts

**Performance Optimizations:**
- **Caching:** 3-tier cache (Memory, Redis, PostgreSQL)
- **Parallel Processing:** 4 concurrent chunk processing
- **Connection Pooling:** HTTP/2 with persistent connections
- **Job Queue:** Celery + Redis for async processing
- **Database:** Optimized queries and indexes
- **Frontend:** Code splitting and lazy loading
- **CDN:** Static asset delivery

---

### User

**Description:**
End users who interact with the STT application through a web browser.

**Key Responsibilities:**
- Upload audio files for transcription
- Monitor processing progress
- View and edit transcripts
- Search transcripts using RAG
- Manage transcript library

**User Personas:**
1. **Content Creator:** Records meetings, podcasts, interviews
2. **Researcher:** Analyzes audio content for insights
3. **Developer:** Integrates transcription API
4. **Enterprise:** Bulk processing of audio archives

---

### Cloud.ru API

**Description:**
Evolution Cloud.ru API provides AI services including speech recognition and text generation.

**Services Used:**
1. **Whisper Large v3:** State-of-the-art speech-to-text
2. **GigaChat:** Text generation for summaries
3. **GigaChat:** Translation between languages

**Constraints:**
- API latency: 12-15 seconds per chunk
- File size limit: 25MB per request
- Rate limiting: ~20 requests/minute
- No embeddings endpoint available

---

## Performance Context

### Current Performance (Before Optimization)

| Metric | Value | Issue |
|--------|-------|-------|
| 100MB file processing | 48-60 seconds | Sequential chunks |
| API connection overhead | +200ms per request | New connection each time |
| Cache hit rate | 0% | No caching |
| Concurrent capacity | 1-2 jobs | BackgroundTasks only |
| Frontend bundle size | ~3MB | No code splitting |

### Target Performance (After Optimization)

| Metric | Target | Improvement |
|--------|--------|-------------|
| 100MB file processing | 12-24 seconds | 2-5x speedup |
| API connection overhead | 0ms (after first) | Connection pooling |
| Cache hit rate | >70% | Multi-level cache |
| Concurrent capacity | 5-10 jobs | Celery workers |
| Frontend bundle size | <500KB | Code splitting |

---

## Data Flow

### File Upload Flow

```
User → STT System → Celery Queue → Workers → Cloud.ru API → Cache → Database
         ↓
    Progress Updates
```

### Cached Request Flow

```
User → STT System → L1 Cache (Memory) → L2 Cache (Redis) → L3 Cache (DB) → Cloud.ru API
                            ↑______________| (promote on hit)
```

---

## Quality Attributes

### Performance

- **Processing Speed:** 2-5x faster with parallel processing
- **Response Time:** <200ms for cached results
- **Throughput:** 5-10 concurrent jobs

### Scalability

- **Horizontal Scale:** Add Celery workers
- **Vertical Scale:** Increase connection pool size
- **Cache Scale:** Redis cluster for L2

### Reliability

- **Retry Logic:** Exponential backoff on failures
- **Graceful Degradation:** Fallback to sequential if needed
- **Job Persistence:** Redis broker for durability

### Maintainability

- **Modular Design:** Separate bounded contexts
- **Monitoring:** Prometheus + Flower dashboards
- **Logging:** Structured logging with correlation IDs

---

## Technology Stack

### Frontend

- React with TypeScript
- Vite for bundling
- Code splitting (route-based)
- Lazy loading for components

### Backend

- FastAPI (Python)
- Celery for job queue
- Redis for cache + broker
- PostgreSQL for storage

### Infrastructure

- Docker Compose for deployment
- Nginx as reverse proxy
- Optional CDN (Cloudflare R2)

---

**Document Control**

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-02-03 | Performance Team | Initial context diagram |
