# C4 Model - Container Diagram

**Feature:** Performance Optimizations
**Version:** 1.0
**Date:** 2026-02-03

---

## Container Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           Single Page Application                         │
│                                      │                                    │
│  - React + TypeScript                                                  │
│  - Code splitting (route-based)                                        │
│  - Lazy loading for heavy components                                    │
│  - Real-time progress updates (SSE/WebSocket)                           │
│  - Bundle size: <500KB (initial)                                       │
└──────────────────────────────────────┬───────────────────────────────────┘
                                       │ HTTPS
                                       │
┌──────────────────────────────────────▼───────────────────────────────────┐
│                                Nginx                                    │
│                                                                           │
│  - Reverse proxy                                                         │
│  - Static asset hosting                                                  │
│  - SSL termination                                                       │
│  - Request routing                                                       │
│  - Gzip/Brotli compression                                               │
└─────┬─────────────────────────────────────────────────────────────────────┘
      │
      │ HTTP
      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              FastAPI Backend                             │
│                                                                            │
│  ┌──────────────────────────────────────────────────────────────────────┐ │
│  │                        API Layer                                    │ │
│  │  - CORS middleware                                                   │ │
│  │  - Request validation                                                │ │
│  │  - Authentication (future)                                           │ │
│  └──────────────────────────────────────────────────────────────────────┘ │
│                                                                            │
│  ┌──────────────────────────────────────────────────────────────────────┐ │
│  │                      Service Layer                                   │ │
│  │                                                                       │ │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │ │
│  │  │ Transcription│  │ Summarization│  │     RAG      │              │ │
│  │  │   Service    │  │   Service    │  │   Service    │              │ │
│  │  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘              │ │
│  │         │                  │                  │                       │ │
│  │         │                  │                  │                       │ │
│  │  ┌──────▼──────────────────▼──────────────────▼───────┐            │ │
│  │  │              Multi-Level Cache Manager              │            │ │
│  │  │                                                       │            │ │
│  │  │  ┌─────────┐  ┌─────────┐  ┌─────────┐              │            │ │
│  │  │  │   L1    │  │   L2    │  │   L3    │              │            │ │
│  │  │  │ (Memory)│  │ (Redis) │  │  (PG)   │              │            │ │
│  │  │  └─────────┘  └─────────┘  └─────────┘              │            │ │
│  │  └───────────────────────────────────────────────────────┘            │ │
│  └──────────────────────────────────────────────────────────────────────┘ │
│                                                                            │
│  ┌──────────────────────────────────────────────────────────────────────┐ │
│  │                      Queue Layer (Celery)                            │ │
│  │                                                                       │ │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │ │
│  │  │ High Priority│  │  Medium      │  │   Low        │              │ │
│  │  │   Queue      │  │  Priority    │  │  Priority    │              │ │
│  │  │              │  │    Queue     │  │   Queue      │              │ │
│  │  │ Transcription│  │ Summarization│  │ RAG Indexing │              │ │
│  │  └──────────────┘  └──────────────┘  └──────────────┘              │ │
│  └──────────────────────────────────────────────────────────────────────┘ │
└──────────────────────────────┬─────────────────────────────────────────────┘
                               │
        ┌──────────────────────┼──────────────────────┐
        │                      │                      │
        ▼                      ▼                      ▼
┌───────────────────┐ ┌───────────────────┐ ┌───────────────────┐
│   PostgreSQL      │ │     Redis         │ │    Celery         │
│   Database        │ │                   │ │    Workers        │
│                   │ │  ┌─────────────┐  │ │                   │
│  - transcripts    │ │  │   L2 Cache  │  │  - Worker High    │
│  - summaries      │ │  └─────────────┘  │  - Worker Medium   │
│  - processing_jobs│ │  ┌─────────────┐  │  - Worker Low      │
│  - cache_entries  │ │  │ Job Broker  │  │  - Beat Scheduler  │
│  - rag_sessions   │ │  └─────────────┘  │                   │
│                   │ │                   │ └───────────────────┘
│  Connection Pool: │ │                   │
│  - Min: 5         │ └───────────────────┘
│  - Max: 20        │
│  - Recycle: 1h    │
└───────────────────┘
         │
         │
         ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                            Cloud.ru API                                    │
│                                                                            │
│  HTTP/2 Connection Pool:                                                   │
│  - Max keepalive: 10                                                       │
│  - Max connections: 20                                                     │
│  - Keepalive expiry: 30s                                                   │
│                                                                            │
│  Services:                                                                 │
│  - Whisper Large v3 (STT)                                                  │
│  - GigaChat (Summarization, Translation)                                   │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Container Descriptions

### Single Page Application

**Technology:** React + TypeScript, Vite

**Responsibilities:**
- User interface for file upload
- Transcript display and editing
- Real-time progress monitoring
- RAG search interface
- Settings and configuration

**Key Features:**
- **Code Splitting:** Separate chunks per route
- **Lazy Loading:** Load heavy components on demand
- **Bundle Size:** Initial load <500KB
- **Progress Streaming:** SSE or WebSocket for real-time updates

---

### Nginx

**Technology:** Nginx Alpine

**Responsibilities:**
- Reverse proxy for FastAPI
- Static asset hosting (with CDN fallback)
- SSL/TLS termination
- Request routing and load balancing
- Gzip/Brotli compression

**Configuration:**
```nginx
# Upstream to FastAPI
upstream backend {
    server backend:8000;
    keepalive 32;
}

# Gzip compression
gzip on;
gzip_types text/plain application/json application/javascript text/css;
gzip_min_length 1024;

# Brotli compression (if available)
brotli on;
brotli_types text/plain application/json application/javascript text/css;
```

---

### FastAPI Backend

**Technology:** Python 3.11+, FastAPI

**Responsibilities:**
- REST API endpoints
- Business logic orchestration
- Cache management
- Queue job submission
- Progress tracking

**API Endpoints:**
- `POST /api/transcripts/upload` - Upload and queue transcription
- `GET /api/transcripts/{id}` - Get transcript
- `GET /api/jobs/{id}/status` - Get job status
- `POST /api/summaries` - Create summary
- `POST /api/rag/ask` - Ask RAG question

---

### Multi-Level Cache Manager

**Technology:** Custom Python + Redis + PostgreSQL

**Responsibilities:**
- Content-addressed cache key generation
- L1 (Memory) cache operations
- L2 (Redis) cache operations
- L3 (PostgreSQL) cache operations
- Cache promotion/demotion

**Cache Hierarchy:**
```
Request → L1 (Memory, 5min TTL)
    Miss → L2 (Redis, 24h TTL)
        Miss → L3 (PostgreSQL, 7d TTL)
            Miss → Cloud.ru API → Populate all levels
```

---

### Celery Queue System

**Technology:** Celery + Redis

**Responsibilities:**
- Async job execution
- Priority-based routing
- Automatic retry with backoff
- Worker health monitoring

**Worker Configuration:**
- **Worker High:** 4 concurrency, transcriptions only
- **Worker Medium:** 2 concurrency, summaries/translations
- **Worker Low:** 2 concurrency, RAG indexing

---

### Celery Workers

**Technology:** Celery Worker processes

**Responsibilities:**
- Execute transcriptions (parallel chunks)
- Generate summaries
- Perform translations
- Index RAG vectors

**Worker Types:**

| Worker | Concurrency | Queues | Purpose |
|--------|-------------|--------|---------|
| High | 4 | high_priority | Transcription (fast) |
| Medium | 2 | medium_priority | Summarization |
| Low | 2 | low_priority | RAG indexing |

---

### PostgreSQL Database

**Technology:** PostgreSQL 15

**Responsibilities:**
- Persistent data storage
- Transaction management
- Full-text search
- Cache L3 storage

**Key Tables:**
- `transcripts` - Main transcript records
- `processing_jobs` - Job tracking
- `cache_entries` - L3 cache
- `summaries` - Generated summaries
- `rag_sessions` - RAG conversation state

**Connection Pool:**
- Min: 5 connections
- Max: 20 connections
- Recycle: 1 hour
- Pre-ping: enabled

---

### Redis

**Technology:** Redis 7 Alpine

**Responsibilities:**
- L2 cache storage
- Celery message broker
- Celery result backend
- Session storage (future)

**Memory Configuration:**
- Max memory: 5GB (configurable)
- Eviction policy: allkeys-lru
- Persistence: AOF enabled

---

### Flower

**Technology:** Flower (Celery monitoring)

**Responsibilities:**
- Real-time job monitoring
- Worker health status
- Queue depth visualization
- Task history and debugging

**Access:** http://localhost:5555

---

### Cloud.ru API

**Technology:** External REST API

**Responsibilities:**
- Whisper speech-to-text
- GigaChat text generation
- Rate limiting and authentication

**Integration:**
- HTTP/2 connection pooling
- Persistent connections (30s keepalive)
- Exponential backoff on errors

---

## Inter-Container Communication

### Synchronous Communication

| From | To | Protocol | Purpose |
|------|-----|----------|---------|
| SPA | Nginx | HTTPS | Static assets, API proxy |
| Nginx | FastAPI | HTTP | API requests |
| FastAPI | PostgreSQL | pgwire | Query data |
| FastAPI | Redis | RESP | Cache operations |
| FastAPI | Cloud.ru API | HTTPS | AI services |

### Asynchronous Communication

| From | To | Protocol | Purpose |
|------|-----|----------|---------|
| FastAPI | Celery | Redis (tasks) | Submit jobs |
| Workers | FastAPI | Redis (results) | Update status |
| Workers | PostgreSQL | pgwire | Save results |
| Workers | Redis | RESP | Cache results |

---

## Data Flow Examples

### File Upload with Caching

```
1. SPA uploads file to Nginx
2. Nginx proxies to FastAPI
3. FastAPI saves file, creates transcript record
4. FastAPI checks cache (L1 → L2 → L3)
5. If cache miss: submit to Celery
6. Celery worker processes with parallel chunks
7. Results cached in L1, L2, L3
8. FastAPI returns job ID
9. SPA polls for status
```

### Cached Request

```
1. SPA requests transcript
2. FastAPI checks L1 (memory) → HIT!
3. Return result in <50ms
4. No API call needed
```

---

## Scaling Strategy

### Horizontal Scaling

- **Celery Workers:** Add more worker containers
- **FastAPI:** Multiple instances behind Nginx
- **Redis:** Redis Cluster for L2 cache

### Vertical Scaling

- **Worker Concurrency:** Increase `--concurrency` flag
- **Connection Pool:** Increase `max_connections`
- **Cache Size:** Increase Redis memory limit

---

**Document Control**

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-02-03 | Performance Team | Initial container diagram |
