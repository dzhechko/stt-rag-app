# Domain Events

**Feature:** Performance Optimizations
**Version:** 1.0
**Date:** 2026-02-03

---

## Overview

Domain Events represent something that happened in the domain that domain experts care about. They enable loose coupling between bounded contexts and support eventual consistency.

---

## Event Taxonomy

```
DomainEvent (Abstract)
├── Processing Events
│   ├── FileUploadStarted
│   ├── ChunkProcessingStarted
│   ├── ChunkProcessingCompleted
│   ├── ChunkProcessingFailed
│   ├── FileProcessingCompleted
│   ├── FileProcessingFailed
│   └── ProgressUpdated
├── Caching Events
│   ├── CacheEntryCreated
│   ├── CacheEntryAccessed
│   ├── CacheEntryInvalidated
│   ├── CacheWarmerStarted
│   └── CacheWarmerCompleted
├── Queue Events
│   ├── JobQueued
│   ├── JobStarted
│   ├── JobProgressUpdated
│   ├── JobCompleted
│   ├── JobFailed
│   ├── JobRetryScheduled
│   ├── WorkerStarted
│   └── WorkerStopped
├── Monitoring Events
│   ├── MetricRecorded
│   ├── AlertTriggered
│   ├── AlertCleared
│   └── DashboardGenerated
└── Database Events
    ├── ConnectionAcquired
    ├── ConnectionReleased
    ├── QueryExecuted
    └── IndexCreated
```

---

## Processing Events

### FileUploadStarted

**When:** User initiates file upload

**Purpose:** Signal that processing pipeline should prepare

**Payload:**
```python
@dataclass
class FileUploadStarted(DomainEvent):
    event_id: UUID
    timestamp: datetime
    transcript_id: UUID
    file_name: str
    file_size: int
    file_hash: str  # SHA-256
    language: Optional[str]
    upload_ip: str
```

**Subscribers:**
- Monitoring Context (track upload rate)
- Processing Context (prepare for processing)
- Queue Context (prepare job)

---

### ChunkProcessingStarted

**When:** A chunk begins processing

**Purpose:** Track parallel processing progress

**Payload:**
```python
@dataclass
class ChunkProcessingStarted(DomainEvent):
    event_id: UUID
    timestamp: datetime
    transcript_id: UUID
    chunk_id: UUID
    chunk_index: int  # 0-based
    total_chunks: int
    chunk_size: int
    processing_strategy: str  # "parallel", "sequential"
```

**Subscribers:**
- Monitoring Context (track active chunks)
- Caching Context (check for existing cache)

---

### ChunkProcessingCompleted

**When:** A chunk completes successfully

**Purpose:** Enable result caching and progress tracking

**Payload:**
```python
@dataclass
class ChunkProcessingCompleted(DomainEvent):
    event_id: UUID
    timestamp: datetime
    transcript_id: UUID
    chunk_id: UUID
    chunk_index: int
    processing_duration_ms: int
    text_length: int
    was_cached: bool
    cache_key: Optional[str]
```

**Subscribers:**
- Caching Context (store result)
- Monitoring Context (record duration)
- Processing Context (update progress)

---

### ChunkProcessingFailed

**When:** A chunk fails after retries

**Purpose:** Trigger error handling and potential rollback

**Payload:**
```python
@dataclass
class ChunkProcessingFailed(DomainEvent):
    event_id: UUID
    timestamp: datetime
    transcript_id: UUID
    chunk_id: UUID
    chunk_index: int
    error_type: str  # "api_error", "timeout", "rate_limit"
    error_message: str
    retry_count: int
    will_retry: bool
```

**Subscribers:**
- Monitoring Context (record error)
- Queue Context (schedule retry if applicable)
- Processing Context (update job status)

---

### FileProcessingCompleted

**When:** All chunks processed and merged

**Purpose:** Signal completion to all interested parties

**Payload:**
```python
@dataclass
class FileProcessingCompleted(DomainEvent):
    event_id: UUID
    timestamp: datetime
    transcript_id: UUID
    total_duration_ms: int
    total_chunks: int
    successful_chunks: int
    failed_chunks: int
    cache_hits: int
    final_text_length: int
    detected_language: str
```

**Subscribers:**
- Monitoring Context (record total time)
- Core Domain (update transcript status)
- Caching Context (warm related entries)

---

### ProgressUpdated

**When:** Processing progress changes

**Purpose:** Real-time progress updates for UI

**Payload:**
```python
@dataclass
class ProgressUpdated(DomainEvent):
    event_id: UUID
    timestamp: datetime
    transcript_id: UUID
    progress: float  # 0.0 - 1.0
    current_chunk: int
    total_chunks: int
    status: str  # "processing", "merging", "completed"
```

**Subscribers:**
- Monitoring Context (update progress metrics)
- Frontend (via WebSocket/SSE)

---

## Caching Events

### CacheEntryCreated

**When:** New entry added to cache

**Purpose:** Track cache growth and efficiency

**Payload:**
```python
@dataclass
class CacheEntryCreated(DomainEvent):
    event_id: UUID
    timestamp: datetime
    cache_key: str
    cache_level: str  # "L1", "L2", "L3"
    entry_size_bytes: int
    ttl_seconds: int
    entry_type: str  # "transcript", "embeddings", "summary"
    source: str  # "api_result", "computation"
```

**Subscribers:**
- Monitoring Context (track cache size)
- Database Context (L3 persistence)

---

### CacheEntryAccessed

**When:** Cache entry is read

**Purpose:** Calculate hit rates and access patterns

**Payload:**
```python
@dataclass
class CacheEntryAccessed(DomainEvent):
    event_id: UUID
    timestamp: datetime
    cache_key: str
    cache_level: str  # "L1", "L2", "L3"
    was_hit: bool
    access_duration_ms: int
```

**Subscribers:**
- Monitoring Context (track hit rate)
- Caching Context (promote/demote entries)

---

### CacheEntryInvalidated

**When:** Cache entry removed (explicit or TTL)

**Purpose:** Track invalidation patterns

**Payload:**
```python
@dataclass
class CacheEntryInvalidated(DomainEvent):
    event_id: UUID
    timestamp: datetime
    cache_key: str
    cache_level: str  # "L1", "L2", "L3"
    reason: str  # "ttl_expired", "explicit", "eviction"
    entry_age_seconds: int
```

**Subscribers:**
- Monitoring Context (track invalidation rate)
- Database Context (cleanup L3 if needed)

---

### CacheWarmerStarted

**When:** Background cache warming begins

**Purpose:** Track pre-loading operations

**Payload:**
```python
@dataclass
class CacheWarmerStarted(DomainEvent):
    event_id: UUID
    timestamp: datetime
    warming_strategy: str  # "frequent_access", "scheduled"
    target_entries: int
```

**Subscribers:**
- Monitoring Context (track warming progress)

---

### CacheWarmerCompleted

**When:** Cache warming cycle completes

**Purpose:** Report warming results

**Payload:**
```python
@dataclass
class CacheWarmerCompleted(DomainEvent):
    event_id: UUID
    timestamp: datetime
    warming_strategy: str
    entries_loaded: int
    entries_failed: int
    duration_ms: int
```

**Subscribers:**
- Monitoring Context (track warming efficiency)

---

## Queue Events

### JobQueued

**When:** Job added to queue

**Purpose:** Track queue depth and job submission rate

**Payload:**
```python
@dataclass
class JobQueued(DomainEvent):
    event_id: UUID
    timestamp: datetime
    job_id: UUID
    job_type: str  # "transcription", "summarization", "indexing"
    priority: str  # "high", "medium", "low"
    queue_name: str
    payload_size: int
    submitter: str  # "api", "system", "retry"
```

**Subscribers:**
- Monitoring Context (track queue metrics)
- Flower (display in dashboard)

---

### JobStarted

**When:** Worker begins executing job

**Purpose:** Track worker utilization

**Payload:**
```python
@dataclass
class JobStarted(DomainEvent):
    event_id: UUID
    timestamp: datetime
    job_id: UUID
    worker_id: str
    worker_pid: int
    queue_name: str
```

**Subscribers:**
- Monitoring Context (track worker activity)
- Flower (update job status)

---

### JobProgressUpdated

**When:** Job progress changes

**Purpose:** Real-time job tracking

**Payload:**
```python
@dataclass
class JobProgressUpdated(DomainEvent):
    event_id: UUID
    timestamp: datetime
    job_id: UUID
    progress: float  # 0.0 - 1.0
    message: Optional[str]
    current_step: str
```

**Subscribers:**
- Flower (update progress bar)
- Frontend (via polling/WebSocket)

---

### JobCompleted

**When:** Job finishes successfully

**Purpose:** Record completion and trigger post-processing

**Payload:**
```python
@dataclass
class JobCompleted(DomainEvent):
    event_id: UUID
    timestamp: datetime
    job_id: UUID
    worker_id: str
    duration_ms: int
    result_size: int
    retry_count: int
```

**Subscribers:**
- Monitoring Context (record job duration)
- Core Domain (update entity status)
- Queue Context (remove from queue)

---

### JobFailed

**When:** Job fails permanently

**Purpose:** Trigger alert and DLQ handling

**Payload:**
```python
@dataclass
class JobFailed(DomainEvent):
    event_id: UUID
    timestamp: datetime
    job_id: UUID
    worker_id: str
    error_type: str  # "api_error", "timeout", "validation"
    error_message: str
    retry_count: int
    sent_to_dlq: bool
```

**Subscribers:**
- Monitoring Context (record failure rate)
- Queue Context (handle DLQ)

---

### JobRetryScheduled

**When:** Job scheduled for retry

**Purpose:** Track retry patterns

**Payload:**
```python
@dataclass
class JobRetryScheduled(DomainEvent):
    event_id: UUID
    timestamp: datetime
    job_id: UUID
    retry_attempt: int
    max_retries: int
    backoff_seconds: int
    reason: str
```

**Subscribers:**
- Monitoring Context (track retry rate)
- Queue Context (schedule retry)

---

### WorkerStarted

**When:** Worker process starts

**Purpose:** Track worker availability

**Payload:**
```python
@dataclass
class WorkerStarted(DomainEvent):
    event_id: UUID
    timestamp: datetime
    worker_id: str
    worker_pid: int
    queues: List[str]
    concurrency: int
```

**Subscribers:**
- Monitoring Context (track worker count)
- Flower (display worker)

---

### WorkerStopped

**When:** Worker process stops

**Purpose:** Detect worker failures

**Payload:**
```python
@dataclass
class WorkerStopped(DomainEvent):
    event_id: UUID
    timestamp: datetime
    worker_id: str
    reason: str  # "shutdown", "crash", "timeout"
    jobs_running: int
```

**Subscribers:**
- Monitoring Context (alert on worker loss)
- Queue Context (reschedule orphaned jobs)

---

## Monitoring Events

### MetricRecorded

**When:** Any metric is captured

**Purpose:** Central metric collection

**Payload:**
```python
@dataclass
class MetricRecorded(DomainEvent):
    event_id: UUID
    timestamp: datetime
    metric_name: str
    metric_value: float
    metric_type: str  # "counter", "gauge", "histogram"
    tags: Dict[str, str]
```

**Subscribers:**
- Prometheus (metric storage)

---

### AlertTriggered

**When:** Alert condition met

**Purpose:** Notify operators of issues

**Payload:**
```python
@dataclass
class AlertTriggered(DomainEvent):
    event_id: UUID
    timestamp: datetime
    alert_rule_id: str
    alert_name: str
    severity: str  # "info", "warning", "critical"
    metric_name: str
    current_value: float
    threshold: float
    message: str
```

**Subscribers:**
- Notification service (email/Slack)
- Monitoring dashboard

---

### AlertCleared

**When:** Alert condition resolved

**Purpose:** Clear alert notifications

**Payload:**
```python
@dataclass
class AlertCleared(DomainEvent):
    event_id: UUID
    timestamp: datetime
    alert_rule_id: str
    alert_name: str
    duration_seconds: int
```

**Subscribers:**
- Notification service
- Monitoring dashboard

---

## Database Events

### ConnectionAcquired

**When:** Database connection checked out from pool

**Purpose:** Track pool utilization

**Payload:**
```python
@dataclass
class ConnectionAcquired(DomainEvent):
    event_id: UUID
    timestamp: datetime
    pool_id: str
    pool_size: int
    pool_available: int
    checkout_duration_ms: int
```

**Subscribers:**
- Monitoring Context (track pool health)

---

### QueryExecuted

**When:** SQL query executed

**Purpose:** Track query performance

**Payload:**
```python
@dataclass
class QueryExecuted(DomainEvent):
    event_id: UUID
    timestamp: datetime
    query_hash: str  # Sanitized query signature
    query_type: str  # "SELECT", "INSERT", "UPDATE"
    table_name: str
    duration_ms: int
    row_count: int
    used_index: Optional[str]
```

**Subscribers:**
- Monitoring Context (identify slow queries)

---

## Event Flow Examples

### File Upload Flow

```
FileUploadStarted
    │
    ├──► Monitoring: Track upload rate
    ├──► Queue: JobQueued
    └──► Processing: Prepare for processing

JobQueued
    │
    ├──► Monitoring: Track queue depth
    └──► Flower: Display in dashboard

JobStarted
    │
    ├──► Monitoring: Track worker activity
    └──► Flower: Update job status

ChunkProcessingStarted (for each chunk)
    │
    ├──► Monitoring: Track active chunks
    └──► Caching: Check for existing cache

CacheEntryAccessed
    │
    └──► Monitoring: Track hit/miss

[if cache miss]
    ChunkProcessingCompleted
        │
        ├──► Monitoring: Record duration
        ├──► Caching: CacheEntryCreated
        └──► Processing: Update progress

[if cache hit]
    ChunkProcessingCompleted (with was_cached=true)
        │
        ├──► Monitoring: Record cache hit
        └──► Processing: Update progress

FileProcessingCompleted
    │
    ├──► Monitoring: Record total time
    ├──► Core Domain: Update transcript status
    └──► JobCompleted

JobCompleted
    │
    ├──► Monitoring: Record job duration
    ├──► Core Domain: Update entity status
    └──► Flower: Mark complete
```

---

## Event Schema

All domain events inherit from a base `DomainEvent` class:

```python
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID
from typing import Protocol

class DomainEvent(Protocol):
    """Base protocol for all domain events"""
    event_id: UUID
    timestamp: datetime
    event_type: str
    event_version: str = "1.0"

    def to_dict(self) -> dict:
        """Serialize event to dictionary"""
        ...

    @classmethod
    def from_dict(cls, data: dict) -> "DomainEvent":
        """Deserialize event from dictionary"""
        ...
```

---

## Event Delivery Guarantees

### 1. At Least Once Delivery

**Implementation:**
- Event store with write-ahead log
- Retry mechanism with exponential backoff
- Idempotent event handlers

**Used For:**
- All critical domain events
- Job lifecycle events
- Cache invalidation events

### 2. At Most Once Delivery

**Implementation:**
- Fire-and-forget publishing
- No retry mechanism
- Best-effort delivery

**Used For:**
- Progress updates (will be superseded)
- Metric collection (aggregation tolerates loss)

---

## Event Versioning

Event schemas follow semantic versioning:

- **1.x.x:** Backward compatible changes (add fields)
- **2.0.0:** Breaking changes (modify/remove fields)

**Migration Strategy:**
- Support multiple versions concurrently
- Transform events at consumer
- Deprecate old versions after 30 days

---

**Document Control**

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-02-03 | Performance Team | Initial domain events |
