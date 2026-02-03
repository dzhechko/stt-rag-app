# Tactical Design - Repository Interfaces

**Feature:** Performance Optimizations
**Version:** 1.0
**Date:** 2026-02-03

---

## Overview

This document defines the Repository interfaces for persisting and retrieving Aggregates.

---

## Repository Base Interface

```python
from typing import TypeVar, Generic, Type, Optional, List
from abc import ABC, abstractmethod

T = TypeVar('T', bound=AggregateRoot)

class Repository(ABC, Generic[T]):
    """Base repository interface"""

    @abstractmethod
    def save(self, aggregate: T) -> None:
        """Persist aggregate state"""
        pass

    @abstractmethod
    def load(self, id: UUID) -> Optional[T]:
        """Load aggregate by ID"""
        pass

    @abstractmethod
    def delete(self, id: UUID) -> None:
        """Delete aggregate by ID"""
        pass
```

---

## JobQueueRepository

**Purpose:** Persist job queue state (PostgreSQL + Redis)

**Primary Storage:** PostgreSQL (job records)
**Secondary Storage:** Redis (job state, results)

```python
class JobQueueRepository(Repository[JobQueue]):
    """Repository for JobQueue aggregate"""

    def save(self, queue: JobQueue) -> None:
        """Persist queue state to PostgreSQL + Redis"""
        # Save jobs to PostgreSQL
        for job in queue.get_all_jobs():
            self._save_job_to_postgres(job)

        # Update Redis queue state
        self._update_redis_queues(queue)

    def load(self, queue_id: QueueId) -> JobQueue:
        """Load queue from PostgreSQL + Redis"""
        jobs = self._load_jobs_from_postgres(queue_id)
        return JobQueue(id=queue_id, jobs=jobs)

    def find_pending_jobs(
        self,
        queue_name: str,
        limit: int = 10
    ) -> List[Job]:
        """Find jobs ready for processing"""
        query = """
        SELECT * FROM processing_jobs
        WHERE status = 'QUEUED'
        AND queue_name = %s
        ORDER BY
            priority DESC,
            created_at ASC
        LIMIT %s
        """
        return self._execute_query(query, [queue_name, limit])

    def update_job_status(
        self,
        job_id: JobId,
        status: JobStatus
    ) -> None:
        """Update job status (atomic)"""
        query = """
        UPDATE processing_jobs
        SET status = %s, updated_at = NOW()
        WHERE id = %s
        """
        self._execute_query(query, [status.value, str(job_id)])

    def get_job_stats(self, queue_name: str) -> JobStats:
        """Get queue statistics"""
        query = """
        SELECT
            status,
            COUNT(*) as count
        FROM processing_jobs
        WHERE queue_name = %s
        GROUP BY status
        """
        results = self._execute_query(query, [queue_name])
        return JobStats.from_results(results)

    # Private helper methods
    def _save_job_to_postgres(self, job: Job) -> None:
        """Persist job to PostgreSQL"""
        query = """
        INSERT INTO processing_jobs (
            id, type, payload, priority, status,
            retry_count, max_retries, created_at,
            transcript_id
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (id) DO UPDATE SET
            status = EXCLUDED.status,
            updated_at = NOW(),
            retry_count = EXCLUDED.retry_count,
            error_message = EXCLUDED.error_message
        """
        self._execute_query(query, [
            str(job.id),
            job.type.value,
            json.dumps(job.payload),
            job.priority.value,
            job.status.value,
            job.retry_count,
            job.max_retries,
            job.created_at,
            str(job.transcript_id)
        ])

    def _load_jobs_from_postgres(
        self,
        queue_id: QueueId
    ) -> List[Job]:
        """Load jobs from PostgreSQL"""
        query = """
        SELECT * FROM processing_jobs
        WHERE queue_id = %s
        ORDER BY created_at DESC
        """
        results = self._execute_query(query, [str(queue_id)])
        return [Job.from_db_row(row) for row in results]

    def _update_redis_queues(self, queue: JobQueue) -> None:
        """Update Redis queue state"""
        redis_client = self._get_redis_client()

        # Add pending jobs to Redis queue
        for job in queue.get_pending_jobs():
            queue_key = f"queue:{job.queue_name()}"
            redis_client.lpush(
                queue_key,
                json.dumps(job.to_dict())
            )
```

---

## CacheRepository

**Purpose:** Multi-level cache persistence (Memory, Redis, PostgreSQL)

**L1 Storage:** In-memory (dict)
**L2 Storage:** Redis
**L3 Storage:** PostgreSQL

```python
class CacheRepository(Repository[CacheManager]):
    """Repository for multi-level cache"""

    def __init__(self):
        self.l1_cache: Dict[str, CacheEntry] = {}
        self.redis_client = redis.Redis(...)
        self.db_session = SessionLocal()

    def get(self, key: CacheKey) -> Optional[CacheValue]:
        """Get from cache (L1 -> L2 -> L3)"""
        # L1: In-memory
        if str(key) in self.l1_cache:
            entry = self.l1_cache[str(key)]
            if not entry.is_expired():
                entry.touch()
                return entry.value

        # L2: Redis
        redis_value = self.redis_client.get(str(key))
        if redis_value:
            value = CacheValue.from_json(redis_value)
            # Promote to L1
            self.l1_cache[str(key)] = CacheEntry(
                key=key,
                value=value,
                ttl=TTL.minutes(5)
            )
            return value

        # L3: PostgreSQL
        db_entry = self.db_session.query(CacheTable).filter_by(
            cache_key=str(key)
        ).first()
        if db_entry and not db_entry.is_expired():
            value = CacheValue.from_json(db_entry.value)
            # Promote to L2, then L1
            self.redis_client.setex(
                str(key),
                24 * 3600,  # 24 hours
                value.to_json()
            )
            self.l1_cache[str(key)] = CacheEntry(
                key=key,
                value=value,
                ttl=TTL.minutes(5)
            )
            return value

        return None

    def put(
        self,
        key: CacheKey,
        value: CacheValue,
        ttl: TTL
    ) -> None:
        """Put in all cache levels"""
        # L1: In-memory (5 min TTL cap)
        l1_ttl = min(ttl, TTL.minutes(5))
        self.l1_cache[str(key)] = CacheEntry(
            key=key,
            value=value,
            ttl=l1_ttl
        )

        # L2: Redis (24 hour TTL cap)
        l2_ttl = min(ttl, TTL.hours(24))
        self.redis_client.setex(
            str(key),
            l2_ttl.to_seconds(),
            value.to_json()
        )

        # L3: PostgreSQL (full TTL)
        cache_record = CacheTable(
            cache_key=str(key),
            value=value.to_json(),
            ttl_seconds=ttl.to_seconds(),
            created_at=datetime.utcnow()
        )
        self.db_session.merge(cache_record)
        self.db_session.commit()

    def delete(self, key: CacheKey) -> None:
        """Delete from all cache levels"""
        # L1
        self.l1_cache.pop(str(key), None)

        # L2
        self.redis_client.delete(str(key))

        # L3
        self.db_session.query(CacheTable).filter_by(
            cache_key=str(key)
        ).delete()
        self.db_session.commit()

    def invalidate_pattern(self, pattern: str) -> None:
        """Invalidate all keys matching pattern"""
        # L1
        keys_to_delete = [
            k for k in self.l1_cache.keys()
            if fnmatch.fnmatch(k, pattern)
        ]
        for k in keys_to_delete:
            del self.l1_cache[k]

        # L2
        for key in self.redis_client.scan_iter(match=pattern):
            self.redis_client.delete(key)

        # L3
        self.db_session.query(CacheTable).filter(
            CacheTable.cache_key.like(pattern)
        ).delete()
        self.db_session.commit()

    def get_stats(self) -> CacheStats:
        """Get cache statistics"""
        return CacheStats(
            l1_size=len(self.l1_cache),
            l2_size=self.redis_client.dbsize(),
            l3_count=self.db_session.query(CacheTable).count(),
            l1_memory_bytes=sum(
                len(v.value.to_json())
                for v in self.l1_cache.values()
            )
        )
```

---

## ProcessingRepository

**Purpose:** Persist processing state and progress

**Storage:** PostgreSQL (processing records)

```python
class ProcessingRepository(Repository[ParallelProcessor]):
    """Repository for ParallelProcessor aggregate"""

    def save(self, processor: ParallelProcessor) -> None:
        """Save processing state"""
        # Save processing record
        processing_record = ProcessingTable(
            id=str(processor.id),
            transcript_id=str(processor.transcript_id),
            status=processor.status.value,
            total_chunks=processor.total_chunks,
            completed_chunks=processor.completed_chunks,
            progress=processor.get_progress(),
            started_at=processor.started_at,
            updated_at=datetime.utcnow()
        )
        self.db_session.merge(processing_record)

        # Save chunk tasks
        for task in processor.get_tasks():
            chunk_record = ChunkTaskTable(
                id=str(task.id),
                processing_id=str(processor.id),
                chunk_index=task.index,
                status=task.status.value,
                retry_count=task.retry_count,
                started_at=task.started_at,
                completed_at=task.completed_at
            )
            self.db_session.merge(chunk_record)

        self.db_session.commit()

    def load(
        self,
        processing_id: ProcessingId
    ) -> Optional[ParallelProcessor]:
        """Load processing state"""
        processing_record = self.db_session.query(ProcessingTable).filter_by(
            id=str(processing_id)
        ).first()

        if not processing_record:
            return None

        # Load chunk tasks
        chunk_tasks = self.db_session.query(ChunkTaskTable).filter_by(
            processing_id=str(processing_id)
        ).all()

        # Reconstruct processor
        return ParallelProcessor.from_db_records(
            processing_record,
            chunk_tasks
        )

    def update_progress(
        self,
        processing_id: ProcessingId,
        progress: float
    ) -> None:
        """Update processing progress"""
        self.db_session.query(ProcessingTable).filter_by(
            id=str(processing_id)
        ).update({
            "progress": progress,
            "updated_at": datetime.utcnow()
        })
        self.db_session.commit()

    def get_active_processings(self) -> List[ParallelProcessor]:
        """Get all active processing jobs"""
        records = self.db_session.query(ProcessingTable).filter(
            ProcessingTable.status.in_(["PROCESSING", "MERGING"])
        ).all()

        return [
            self.load(ProcessingId(record.id))
            for record in records
        ]
```

---

## MetricsRepository

**Purpose:** Store and query time-series metrics

**Storage:** Prometheus (remote write)

```python
class MetricsRepository(Repository[MetricsCollector]):
    """Repository for MetricsCollector aggregate"""

    def __init__(self):
        self.prometheus_client = PrometheusConnect(...)
        self.local_buffer: List[MetricData] = []

    def save(self, collector: MetricsCollector) -> None:
        """Write metrics to Prometheus"""
        # Collect all metric values
        for series in collector.get_all_series():
            for value in series.get_values():
                self._write_to_prometheus(
                    name=series.name,
                    value=value.value,
                    timestamp=value.timestamp,
                    tags=value.tags
                )

    def _write_to_prometheus(
        self,
        name: str,
        value: float,
        timestamp: datetime,
        tags: Dict[str, str]
    ) -> None:
        """Write single metric to Prometheus"""
        metric = Metric(
            name=name,
            documentation=f"Metric {name}",
            labels=tags
        )
        metric.observe(value, timestamp=int(timestamp.timestamp()))

    def query_time_series(
        self,
        metric_name: str,
        range: TimeRange,
        tags: Dict[str, str] = None
    ) -> List[TimestampedValue]:
        """Query metric time series from Prometheus"""
        query = self._build_promql_query(metric_name, tags)

        result = self.prometheus_client.custom_query_range(
            query=query,
            start_time=range.start,
            end_time=range.end,
            step=range.step
        )

        return self._parse_prometheus_result(result)

    def query_latest(
        self,
        metric_name: str,
        tags: Dict[str, str] = None
    ) -> Optional[float]:
        """Get latest value of metric"""
        query = self._build_promql_query(metric_name, tags) + " | max"

        result = self.prometheus_client.custom_query(query)

        if result and result[0]["values"]:
            return float(result[0]["values"][-1][1])

        return None

    def get_percentile(
        self,
        metric_name: str,
        percentile: Percentile,
        range: TimeRange
    ) -> float:
        """Get percentile value for metric"""
        quantile = percentile.value / 100
        query = (
            f'histogram_quantile({quantile}, '
            f'sum(rate({metric_name}_bucket[{range.step}s})) '
            f'by (le))'
        )

        result = self.prometheus_client.custom_query_range(
            query=query,
            start_time=range.start,
            end_time=range.end,
            step=range.step
        )

        if result and result[0]["values"]:
            return float(result[0]["values"][-1][1])

        return 0.0

    def _build_promql_query(
        self,
        metric_name: str,
        tags: Dict[str, str] = None
    ) -> str:
        """Build PromQL query from metric name and tags"""
        if not tags:
            return metric_name

        tag_str = ",".join([
            f'{k}="{v}"'
            for k, v in tags.items()
        ])
        return f"{metric_name}{{{tag_str}}}"
```

---

## Database Schema

### processing_jobs Table

```sql
CREATE TABLE processing_jobs (
    id UUID PRIMARY KEY,
    transcript_id UUID NOT NULL REFERENCES transcripts(id),
    job_type VARCHAR(50) NOT NULL,
    payload JSONB NOT NULL,
    priority INTEGER NOT NULL DEFAULT 2,
    status VARCHAR(50) NOT NULL DEFAULT 'QUEUED',
    retry_count INTEGER NOT NULL DEFAULT 0,
    max_retries INTEGER NOT NULL DEFAULT 3,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    error_message TEXT,
    worker_id VARCHAR(255),

    INDEX idx_jobs_status (status),
    INDEX idx_jobs_transcript (transcript_id),
    INDEX idx_jobs_type_status (job_type, status),
    INDEX idx_jobs_priority_created (priority DESC, created_at ASC)
);
```

### cache_entries Table

```sql
CREATE TABLE cache_entries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    cache_key VARCHAR(500) UNIQUE NOT NULL,
    value JSONB NOT NULL,
    ttl_seconds INTEGER NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    accessed_at TIMESTAMP,
    access_count INTEGER NOT NULL DEFAULT 0,

    INDEX idx_cache_key (cache_key),
    INDEX idx_cache_created (created_at)
);
```

### processing_tasks Table

```sql
CREATE TABLE processing_tasks (
    id UUID PRIMARY KEY,
    processing_id UUID NOT NULL REFERENCES processing_tasks(id),
    transcript_id UUID NOT NULL REFERENCES transcripts(id),
    status VARCHAR(50) NOT NULL DEFAULT 'PENDING',
    total_chunks INTEGER NOT NULL,
    completed_chunks INTEGER NOT NULL DEFAULT 0,
    progress FLOAT NOT NULL DEFAULT 0,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),

    INDEX idx_processing_status (status),
    INDEX idx_processing_transcript (transcript_id)
);
```

### chunk_tasks Table

```sql
CREATE TABLE chunk_tasks (
    id UUID PRIMARY KEY,
    processing_id UUID NOT NULL REFERENCES processing_tasks(id),
    chunk_index INTEGER NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'PENDING',
    retry_count INTEGER NOT NULL DEFAULT 0,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    error_message TEXT,

    INDEX idx_chunk_processing (processing_id),
    INDEX idx_chunk_status (status)
);
```

### metrics Table (Optional - for L3 metrics storage)

```sql
CREATE TABLE metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    metric_name VARCHAR(255) NOT NULL,
    metric_value FLOAT NOT NULL,
    tags JSONB,
    timestamp TIMESTAMP NOT NULL DEFAULT NOW(),

    INDEX idx_metrics_name_time (metric_name, timestamp),
    INDEX idx_metrics_tags (tags gin_path_ops)
);
```

---

## Repository Factory

```python
class RepositoryFactory:
    """Factory for creating repository instances"""

    def __init__(self, db_session: Session, redis_client: Redis):
        self.db_session = db_session
        self.redis_client = redis_client

    def job_queue_repository(self) -> JobQueueRepository:
        return JobQueueRepository(
            db_session=self.db_session,
            redis_client=self.redis_client
        )

    def cache_repository(self) -> CacheRepository:
        return CacheRepository(
            db_session=self.db_session,
            redis_client=self.redis_client
        )

    def processing_repository(self) -> ProcessingRepository:
        return ProcessingRepository(
            db_session=self.db_session
        )

    def metrics_repository(self) -> MetricsRepository:
        return MetricsRepository()
```

---

## Connection Pool Configuration

```python
from sqlalchemy import create_engine
from sqlalchemy.pool import QueuePool

# Create engine with connection pooling
engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=10,           # Max connections
    max_overflow=20,        # Additional connections
    pool_timeout=30,        # Wait timeout
    pool_recycle=3600,      # Recycle after 1 hour
    pool_pre_ping=True,     # Verify connections
    echo=False
)
```

---

**Document Control**

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-02-03 | Performance Team | Initial repository interfaces |
