# Context Map

**Feature:** Performance Optimizations
**Version:** 1.0
**Date:** 2026-02-03

---

## Overview

This document provides the Context Map showing relationships between all Bounded Contexts in the STT application performance optimization domain.

---

## System Context Map

```
                    ┌─────────────────────────────────────────┐
                    │            User Interface              │
                    │         (React Frontend)               │
                    └──────────────────┬──────────────────────┘
                                       │ HTTP/REST
                                       ▼
┌────────────────────────────────────────────────────────────────────────────┐
│                           STT Backend System                               │
│                                                                            │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │                     Core Domain Context                             │  │
│  │                    (Shared Kernel)                                  │  │
│  │  Transcript | AudioFile | ProcessingJob | Summary | RAGSession      │  │
│  └────────────────────────┬────────────────────────────────────────────┘  │
│                           │                                                │
│  ┌────────────────────────┼────────────────────────────────────────────┐  │
│  │                        │                                            │  │
│  ▼                        ▼                                            ▼  │
│ ┌────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐│
│ │Processing  │    │  Caching    │    │   Queue     │    │ Monitoring  ││
│ │  Context   │◄──►│   Context   │◄──►│   Context   │◄───│   Context   ││
│ │            │    │             │    │             │    │             ││
│ │ - Parallel │    │ - Multi-Lvl │    │ - Priority  │    │ - Metrics   ││
│ │ - Chunks   │    │ - Content   │    │ - Retry     │    │ - Alerts    ││
│ │ - Sizing   │    │   Address   │    │ - Workers   │    │ - Dashboards││
│ └─────┬──────┘    └──────┬──────┘    └──────┬──────┘    └──────┬──────┘│
│       │                  │                  │                  │        │
│       │                  │                  │                  │        │
│       ▼                  ▼                  ▼                  │        │
│ ┌────────────┐    ┌─────────────┐    ┌─────────────┐         │        │
│ │  External  │    │  Database   │    │   Flower    │         │        │
│ │  Context   │    │   Context   │    │  (Monitoring)│         │        │
│ │            │    │             │    │             │         │        │
│ │ - Cloud.ru │    │ - Indexes   │    │ - Job Status│         │        │
│ │ - CDN      │    │ - Pool      │    │ - Workers   │         │        │
│ │ - HTTP/2   │    │ - Queries   │    │ - Queues    │         │        │
│ └────────────┘    └─────────────┘    └─────────────┘         │        │
│       │                  │                                 │        │
└───────┼──────────────────┼─────────────────────────────────┼────────┘
        │                  │                                 │
        ▼                  ▼                                 ▼
┌───────────────┐  ┌───────────────┐              ┌───────────────┐
│  Cloud.ru API │  │  PostgreSQL   │              │  Prometheus   │
│  (STT/LLM)    │  │  Database     │              │  Metrics      │
└───────────────┘  └───────────────┘              └───────────────┘
```

---

## Relationship Types

### 1. Customer-Supplier Relationships

| Customer | Supplier | Data Flow | Interface |
|----------|----------|-----------|-----------|
| Processing | Caching | Key→Result | CacheService |
| Processing | Queue | Job→Status | QueueService |
| Processing | External | Chunk→Transcript | APIClient |
| Caching | Database | Entry→Storage | CacheRepository |
| Queue | Monitoring | Job→Metric | MetricCollector |
| All | Database | Entity→Persistence | Repository |

### 2. Partnership Relationships

| Context A | Context B | Collaboration Type |
|-----------|-----------|-------------------|
| Processing | Monitoring | Real-time metrics |
| Queue | Monitoring | Job status streaming |
| Caching | Monitoring | Cache statistics |

### 3. Anti-Corruption Layers

| Context | External System | ACL Pattern | Purpose |
|---------|----------------|-------------|---------|
| Queue | Celery | Adapter | Normalize job execution |
| Caching | Redis | Repository | Abstract cache storage |
| External | Cloud.ru | Gateway | Handle API quirks |
| Database | PostgreSQL | ORM | Map to domain entities |

---

## Context Details

### Processing Context

**Type:** Core Business Domain

**Responsibilities:**
- Split files into optimal chunks
- Execute parallel chunk processing
- Merge chunk results
- Track processing progress

**Upstream Dependencies:**
- Core Domain (Transcript, AudioFile)

**Downstream Dependencies:**
- Caching Context (store/retrieve results)
- Queue Context (submit jobs)
- External Context (API calls)

**Exposed Interfaces:**
```python
class ProcessingService:
    def process_file(file: AudioFile, strategy: ProcessingStrategy) -> Transcript
    def get_progress(job_id: JobId) -> ProcessingProgress
    def cancel_processing(job_id: JobId) -> None
```

---

### Caching Context

**Type:** Supporting Domain with High Strategic Value

**Responsibilities:**
- Multi-level caching (L1/L2/L3)
- Content-addressed cache keys
- Cache invalidation
- Cache warming

**Upstream Dependencies:**
- Core Domain (cacheable entities)

**Downstream Dependencies:**
- Database Context (L3 storage)
- Redis (L2 storage)

**Exposed Interfaces:**
```python
class CacheService:
    def get(key: CacheKey) -> Optional[CacheEntry]
    def put(key: CacheKey, value: Any, ttl: timedelta) -> None
    def invalidate(key: CacheKey) -> None
    def get_stats() -> CacheStatistics
```

---

### Queue Context

**Type:** Generic Subdomain

**Responsibilities:**
- Job queueing and routing
- Priority management
- Retry handling
- Worker coordination

**Upstream Dependencies:**
- Core Domain (jobs)

**Downstream Dependencies:**
- Celery (execution backend)
- Monitoring Context (job status)

**Exposed Interfaces:**
```python
class QueueService:
    def enqueue(job: Job) -> JobId
    def get_status(job_id: JobId) -> JobStatus
    def cancel_job(job_id: JobId) -> None
    def retry_job(job_id: JobId) -> None
```

---

### Monitoring Context

**Type:** Supporting Domain

**Responsibilities:**
- Metrics collection
- Alert evaluation
- Dashboard generation
- Performance tracking

**Upstream Dependencies:**
- All contexts (metrics source)

**Downstream Dependencies:**
- Prometheus (metrics storage)
- Grafana (visualization)

**Exposed Interfaces:**
```python
class MonitoringService:
    def record_metric(name: str, value: float, tags: Dict) -> None
    def create_alert(rule: AlertRule) -> AlertId
    def get_dashboard(dashboard_id: str) -> Dashboard
```

---

### Database Context

**Type:** Generic Subdomain

**Responsibilities:**
- Connection pooling
- Query optimization
- Index management
- N+1 query elimination

**Upstream Dependencies:**
- All contexts requiring persistence

**Downstream Dependencies:**
- PostgreSQL database

**Exposed Interfaces:**
```python
class DatabaseService:
    def execute_query(query: Query) -> QueryResult
    def get_connection() -> Connection
    def create_index(index: IndexDefinition) -> None
```

---

### External Context

**Type:** Generic Subdomain with ACL

**Responsibilities:**
- HTTP/2 connection pooling
- API rate limiting
- CDN asset management
- Response parsing

**Upstream Dependencies:**
- Processing Context (API calls)

**Downstream Dependencies:**
- Cloud.ru API
- CDN provider

**Exposed Interfaces:**
```python
class ExternalService:
    def transcribe(chunk: AudioChunk) -> TranscriptionResult
    def upload_to_cdn(asset: Asset) -> CDNLocation
    def get_api_status() -> APIStatus
```

---

## Integration Patterns

### 1. Synchronous Integration (Processing ↔ Caching)

```python
class ProcessingService:
    def __init__(self, cache: CacheService):
        self.cache = cache

    def process_chunk(self, chunk: AudioChunk):
        # Try cache
        result = self.cache.get(chunk.hash)
        if result:
            return result

        # Process
        result = self.api_client.transcribe(chunk)

        # Cache
        self.cache.put(chunk.hash, result, ttl=24h)
        return result
```

### 2. Asynchronous Integration (Processing ↔ Queue)

```python
class ProcessingService:
    def __init__(self, queue: QueueService):
        self.queue = queue

    def submit_file(self, file: AudioFile) -> JobId:
        job = Job(
            type=JobType.TRANSCRIPTION,
            payload=file.to_dict(),
            priority=JobPriority.HIGH
        )
        return self.queue.enqueue(job)

    def get_status(self, job_id: JobId):
        return self.queue.get_status(job_id)
```

### 3. Event-Driven Integration (All → Monitoring)

```python
class MonitoredService:
    def __init__(self, monitoring: MonitoringService):
        self.monitoring = monitoring

    def process(self, input):
        timer = self.monitoring.timer("operation.duration")
        with timer:
            try:
                result = self._do_process(input)
                self.monitoring.record_metric("operation.success", 1)
                return result
            except Exception:
                self.monitoring.record_metric("operation.error", 1)
                raise
```

---

## Data Flow Diagrams

### File Upload Flow

```
User Upload
    │
    ▼
┌─────────────┐
│  Frontend   │
└──────┬──────┘
       │ POST /api/transcripts/upload
       ▼
┌─────────────────────────────────────────────┐
│           Core Domain Context               │
│  - Create Transcript entity                │
│  - Create ProcessingJob entity             │
└──────┬──────────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────────────┐
│          Queue Context                      │
│  - Enqueue transcription job               │
│  - Return JobId                            │
└──────┬──────────────────────────────────────┘
       │ Job Queued
       ▼
┌─────────────────────────────────────────────┐
│        Processing Context                   │
│  - Calculate optimal chunk size            │
│  - Split file into chunks                  │
│  - For each chunk:                         │
│      1. Check cache (Caching Context)      │
│      2. If miss, call API (External)       │
│      3. Cache result (Caching Context)     │
│  - Merge chunk results                     │
└──────┬──────────────────────────────────────┘
       │ Progress/Completion Events
       ▼
┌─────────────────────────────────────────────┐
│       Monitoring Context                    │
│  - Record processing metrics               │
│  - Update dashboard                        │
└──────┬──────────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────────────┐
│      Core Domain Context                    │
│  - Update Transcript status                 │
│  - Persist to database                     │
└──────┬──────────────────────────────────────┘
       │
       ▼
    Complete
```

### Cache Lookup Flow

```
Request
    │
    ▼
┌─────────────────────────────────────────────┐
│        Processing Context                   │
│  - Generate cache key from file hash       │
└──────┬──────────────────────────────────────┘
       │ Lookup
       ▼
┌─────────────────────────────────────────────┐
│         Caching Context                     │
│  - Check L1 (Memory)                       │
│  - Check L2 (Redis)                        │
│  - Check L3 (PostgreSQL)                   │
└──────┬──────────────────────────────────────┘
       │
       ├─► Hit ──► Return Cached Result
       │
       └─► Miss ──► Trigger Processing
```

---

## Communication Protocols

### 1. Synchronous (REST API)

**Used Between:**
- Frontend ↔ Backend (all contexts)
- Processing ↔ Caching
- Processing ↔ External

**Protocol:** HTTP/HTTPS
**Format:** JSON
**Latency:** <500ms target

### 2. Asynchronous (Domain Events)

**Used Between:**
- All contexts → Monitoring
- Queue → Processing (job updates)

**Protocol:** Redis Pub/Sub or internal event bus
**Format:** JSON
**Latency:** <100ms target

### 3. Queue-Based (Celery)

**Used Between:**
- Backend → Workers
- Queue Context → Processing Workers

**Protocol:** Redis as broker
**Format:** Pickle/JSON
**Latency:** Variable (async)

---

## Context Evolution

### Phase 1: Monolith to Contexts
- Extract Processing Context
- Extract Caching Context
- Define Core Domain

### Phase 2: Queue Integration
- Extract Queue Context
- Integrate Celery
- Add Flower monitoring

### Phase 3: Observability
- Extract Monitoring Context
- Add metrics collection
- Create dashboards

### Phase 4: Optimization
- Tune boundaries
- Optimize event flow
- Refactor based on metrics

---

**Document Control**

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-02-03 | Performance Team | Initial context map |
