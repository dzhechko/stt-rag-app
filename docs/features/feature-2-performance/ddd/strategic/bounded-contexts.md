# Strategic Design - Bounded Contexts

**Feature:** Performance Optimizations
**Version:** 1.0
**Date:** 2026-02-03

---

## Overview

This document defines the Bounded Contexts for the Performance Optimization feature using Domain-Driven Design principles. Each context represents a specific area of the performance domain with clear responsibilities and boundaries.

---

## Context Map

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         STT Application Context                            │
│                                                                             │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐                 │
│  │   Processing │    │    Caching   │    │     Queue    │                 │
│  │   Context    │◄──►│    Context   │◄──►│   Context    │                 │
│  │              │    │              │    │              │                 │
│  │  - Chunk     │    │  - Content   │    │  - Job       │                 │
│  │    Splitter  │    │    Address   │    │    Dispatch  │                 │
│  │  - Parallel  │    │  - Multi     │    │  - Priority  │                 │
│  │    Executor  │    │    Level     │    │    Mgmt      │                 │
│  └──────┬───────┘    └──────────────┘    └──────┬───────┘                 │
│         │                                      │                          │
│         └──────────────┬───────────────────────┘                          │
│                        │                                                  │
│                        ▼                                                  │
│         ┌────────────────────────────────────────┐                        │
│         │         Core Domain Context            │                        │
│         │  (Shared Kernel - Transcript, File)    │                        │
│         └────────────────────────────────────────┘                        │
│                                                                             │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐                 │
│  │  Monitoring  │    │  Database    │    │   External   │                 │
│  │  Context     │    │  Context     │    │   Context    │                 │
│  │              │    │              │    │              │                 │
│  │  - Metrics   │    │  - Queries   │    │  - Cloud.ru  │                 │
│  │  - Alerts    │    │  - Indexes   │    │    API       │                 │
│  │  - Dashboards│    │  - Pool      │    │  - CDN       │                 │
│  └──────────────┘    └──────────────┘    └──────────────┘                 │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Bounded Contexts

### 1. Processing Context

**Responsibility:** Orchestrate parallel processing of audio chunks with optimal sizing.

**Domain Model:**
- Audio File → Chunks → Processing Tasks → Results → Merge

**Core Entities:**
- `AudioChunk` - Individual chunk of audio data
- `ProcessingStrategy` - Defines how chunks are processed
- `ChunkProcessor` - Executes individual chunk processing
- `ResultMerger` - Combines chunk results into final output

**Value Objects:**
- `ChunkSize` - Optimal size (10-30MB range)
- `ConcurrencyLimit` - Max parallel chunks (4)
- `ProcessingProgress` - Current progress (0-1)

**Domain Services:**
- `DynamicChunkSizer` - Analyzes file to determine optimal size
- `ParallelOrchestrator` - Manages concurrent chunk execution
- `TimestampAdjuster` - Aligns timestamps across chunks

**Ubiquitous Language:**
- Chunk, Segment, Parallel, Concurrency, Progress, Strategy

**Relationships:**
- **Upstream:** Core Domain (Transcript, File)
- **Downstream:** Caching Context, Queue Context
- **Partner:** Monitoring Context (metrics)

---

### 2. Caching Context

**Responsibility:** Store and retrieve computation results using multi-level caching strategy.

**Domain Model:**
- Cache Key → Cache Entry → Cache Level → Lookup/Store

**Core Entities:**
- `CacheEntry` - Cached result with metadata
- `CacheLevel` - L1 (memory), L2 (Redis), L3 (PostgreSQL)
- `CachePolicy` - TTL, eviction, invalidation rules

**Value Objects:**
- `CacheKey` - Content-addressed key (SHA-256 based)
- `TTL` - Time to live duration
- `CacheHitResult` - Hit or miss with data

**Domain Services:**
- `ContentAddresser` - Generates hash-based cache keys
- `MultiLevelCache` - Orchestrates L1→L2→L3 lookups
- `CacheInvalidator` - Handles explicit and time-based invalidation
- `CacheWarmer` - Pre-loads frequently accessed content

**Ubiquitous Language:**
- Cache Hit/Miss, TTL, Eviction, Warm-up, Content Address

**Relationships:**
- **Upstream:** Processing Context (results), Core Domain (transcripts)
- **Downstream:** Database Context (L3 storage)
- **Anti-Corruption Layer:** Redis API wrapper

---

### 3. Queue Context

**Responsibility:** Manage async job execution with priority and retry logic.

**Domain Model:**
- Job → Queue → Worker → Result → Retry

**Core Entities:**
- `Job` - Unit of work to execute
- `JobQueue` - Priority-based queue
- `WorkerNode` - Execution worker
- `RetryPolicy` - Retry configuration

**Value Objects:**
- `JobPriority` - High, Medium, Low
- `JobStatus` - Queued, Processing, Completed, Failed
- `RetryConfig` - Max retries, backoff strategy
- `JobResult` - Success or failure with payload

**Domain Services:**
- `JobDispatcher` - Routes jobs to appropriate queues
- `PriorityManager` - Manages queue priorities
- `RetryHandler` - Implements exponential backoff
- `DeadLetterHandler` - Manages permanently failed jobs

**Ubiquitous Language:**
- Job, Queue, Worker, Priority, Retry, Backoff, DLQ

**Relationships:**
- **Upstream:** Processing Context (jobs)
- **Downstream:** Monitoring Context (status)
- **Anti-Corruption Layer:** Celery adapter

---

### 4. Monitoring Context

**Responsibility:** Track, aggregate, and alert on performance metrics.

**Domain Model:**
- Metric → Aggregation → Alert → Dashboard

**Core Entities:**
- `Metric` - Individual measurement point
- `MetricSeries` - Time-series of metrics
- `AlertRule` - Threshold and notification config
- `Dashboard` - Visualization configuration

**Value Objects:**
- `MetricName` - e.g., `processing.duration`, `cache.hit_rate`
- `MetricValue` - Numeric value with timestamp
- `Threshold` - Alert trigger value
- `Percentile` - p50, p95, p99

**Domain Services:**
- `MetricsCollector` - Gathers metrics from all contexts
- `Aggregator` - Computes percentiles, averages
- `AlertEvaluator` - Checks thresholds and triggers alerts
- `DashboardGenerator` - Creates visualization data

**Ubiquitous Language:**
- Metric, Percentile, Threshold, Alert, Dashboard, Latency

**Relationships:**
- **Upstream:** All contexts (metrics)
- **Downstream:** External (Prometheus, Grafana)

---

### 5. Database Context

**Responsibility:** Optimize data persistence with indexing and connection pooling.

**Domain Model:**
- Entity → Repository → Query → Result

**Core Entities:**
- `DatabaseConnection` - Pooled connection
- `Index` - Database index definition
- `QueryPlan` - Optimized execution plan

**Value Objects:**
- `ConnectionString` - Database connection details
- `PoolSize` - Min/max connections
- `QueryResult` - Data with metadata
- `IndexDefinition` - Column, type, uniqueness

**Domain Services:**
- `ConnectionPoolManager` - Manages pool lifecycle
- `QueryOptimizer` - Analyzes and optimizes queries
- `IndexManager` - Creates and maintains indexes
- `N1QueryEliminator` - Refactors ORM queries

**Ubiquitous Language:**
- Pool, Index, Query Plan, N+1, Eager Loading

**Relationships:**
- **Upstream:** All contexts requiring persistence
- **Downstream:** PostgreSQL database

---

### 6. External Context

**Responsibility:** Integrate with external APIs (Cloud.ru, CDN).

**Domain Model:**
- API Client → Request → Response → Error Handling

**Core Entities:**
- `APIConnection` - HTTP/2 persistent connection
- `APIRequest` - Outgoing request with retry
- `APIResponse` - Response with caching metadata
- `CDNAsset` - Asset stored on CDN

**Value Objects:**
- `APIEndpoint` - URL and authentication
- `ConnectionPool` - Pool configuration
- `RateLimit` - Request rate limits
- `CDNLocation` - Geographic distribution

**Domain Services:**
- `ConnectionPoolManager` - Maintains HTTP/2 connections
- `RateLimitHandler` - Respects API limits
- `CDNUploader` - Uploads and manages CDN assets
- `APIResponseParser` - Extracts data from responses

**Ubiquitous Language:**
- Connection Pool, HTTP/2, Rate Limit, CDN, Edge

**Relationships:**
- **Upstream:** Processing Context (API calls)
- **Downstream:** Cloud.ru API, CDN provider

---

### 7. Core Domain Context (Shared Kernel)

**Responsibility:** Core transcript and file entities shared across contexts.

**Core Entities:**
- `Transcript` - Main transcript entity
- `AudioFile` - Source audio file
- `ProcessingJob` - Job tracking

**Shared Value Objects:**
- `TranscriptId` - UUID identifier
- `Language` - ISO-639-1 code
- `FileHash` - SHA-256 content hash
- `Timestamp` - Unix timestamp

**Relationships:**
- Shared by all contexts via Domain Events

---

## Context Relationships

### Customer-Supplier

| Customer | Supplier | Interface |
|----------|----------|-----------|
| Processing | Caching | Cache lookup/store |
| Processing | Queue | Job submission |
| Processing | External | API calls |
| Queue | Monitoring | Job status updates |
| All | Database | Persistence |

### Partnership

| Context A | Context B | Purpose |
|-----------|-----------|---------|
| Processing | Monitoring | Real-time metrics |
| Queue | Monitoring | Job visibility |

### Anti-Corruption Layers

| Context | External System | ACL Pattern |
|---------|----------------|-------------|
| Queue | Celery | Adapter |
| Caching | Redis | Repository |
| External | Cloud.ru API | Gateway |

---

## Domain Events

### Processing Context Events

```python
class ChunkProcessingStarted(DomainEvent):
    chunk_id: ChunkId
    transcript_id: TranscriptId
    timestamp: datetime

class ChunkProcessingCompleted(DomainEvent):
    chunk_id: ChunkId
    result: ProcessingResult
    duration_ms: int

class FileProcessingCompleted(DomainEvent):
    transcript_id: TranscriptId
    total_chunks: int
    total_duration_ms: int
```

### Caching Context Events

```python
class CacheEntryCreated(DomainEvent):
    cache_key: CacheKey
    level: CacheLevel
    ttl: timedelta

class CacheInvalidated(DomainEvent):
    cache_key: CacheKey
    reason: InvalidationReason
```

### Queue Context Events

```python
class JobQueued(DomainEvent):
    job_id: JobId
    priority: JobPriority
    queue_name: str

class JobCompleted(DomainEvent):
    job_id: JobId
    result: JobResult
    retry_count: int
```

### Monitoring Context Events

```python
class MetricRecorded(DomainEvent):
    metric_name: str
    value: float
    timestamp: datetime

class AlertTriggered(DomainEvent):
    alert_rule_id: str
    metric_value: float
    threshold: float
```

---

## Integration Patterns

### 1. Processing → Caching Integration

**Pattern:** Cache-Aside

```python
class ProcessingService:
    def process_chunk(self, chunk: AudioChunk) -> ProcessingResult:
        # Try cache first
        cached = cache_service.get(chunk.hash)
        if cached:
            return cached

        # Process and cache result
        result = api_client.transcribe(chunk)
        cache_service.put(chunk.hash, result, ttl=24h)
        return result
```

### 2. Processing → Queue Integration

**Pattern:** Command Message

```python
class ProcessingService:
    def submit_job(self, file: AudioFile) -> JobId:
        job = Job(
            type=JobType.TRANSCRIPTION,
            payload=file.to_dict(),
            priority=JobPriority.HIGH
        )
        return queue_service.enqueue(job)
```

### 3. All → Monitoring Integration

**Pattern:** Event-Driven Monitoring

```python
class InstrumentedService:
    def process(self, input):
        timer = metrics.timer("operation.duration")
        with timer:
            result = self._do_process(input)

        metrics.record("operation.success", 1)
        return result
```

---

## Context Boundaries Enforcement

### 1. Module Boundaries

```
backend/
  app/
    contexts/
      processing/    # Processing Context
      caching/       # Caching Context
      queue/         # Queue Context
      monitoring/    # Monitoring Context
      database/      # Database Context
      external/      # External Context
      core/          # Core Domain (Shared Kernel)
```

### 2. API Boundaries

Each context exposes a well-defined interface:

```python
# Processing Context API
class ProcessingService(ABC):
    @abstractmethod
    def process_file(self, file: AudioFile) -> Transcript

    @abstractmethod
    def get_progress(self, job_id: JobId) -> ProcessingProgress
```

### 3. Data Boundaries

- No direct database access across contexts
- Use Domain Events for cross-context communication
- Shared types in Core Domain only

---

## Evolution Strategy

### Phase 1: Define Boundaries
- Create context modules
- Define interfaces
- Implement Domain Events

### Phase 2: Implement Contexts
- Processing Context (parallel execution)
- Caching Context (multi-level cache)
- Queue Context (Celery integration)

### Phase 3: Integrate
- Wire contexts together
- Implement ACLs
- Add monitoring

### Phase 4: Optimize
- Tune boundaries
- Optimize event flow
- Refactor based on metrics

---

**Document Control**

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-02-03 | Performance Team | Initial bounded contexts |
