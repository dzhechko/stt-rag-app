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

    def find_by_transcript(
        self,
        transcript_id: UUID
    ) -> List[ParallelProcessor]:
        """Find all processing jobs for a transcript"""
        records = self.db_session.query(ProcessingTable).filter_by(
            transcript_id=str(transcript_id)
        ).order_by(ProcessingTable.created_at.desc()).all()

        return [
            self.load(ProcessingId(record.id))
            for record in records
        ]

    def find_stalled_tasks(
        self,
        timeout: timedelta = timedelta(minutes=30)
    ) -> List[ProcessingTask]:
        """Find tasks that have been running too long"""
        timeout_threshold = datetime.utcnow() - timeout

        chunk_records = self.db_session.query(ChunkTaskTable).filter(
            ChunkTaskTable.status == "PROCESSING",
            ChunkTaskTable.started_at < timeout_threshold
        ).all()

        return [
            ProcessingTask.from_db_record(record)
            for record in chunk_records
        ]

    def find_failed_chunks(
        self,
        processing_id: ProcessingId
    ) -> List[ProcessingTask]:
        """Find all failed chunks for a processing job"""
        chunk_records = self.db_session.query(ChunkTaskTable).filter(
            ChunkTaskTable.processing_id == str(processing_id),
            ChunkTaskTable.status == "FAILED"
        ).all()

        return [
            ProcessingTask.from_db_record(record)
            for record in chunk_records
        ]

    def bulk_update_status(
        self,
        task_ids: List[TaskId],
        status: TaskStatus
    ) -> int:
        """Update status for multiple tasks atomically"""
        updated = self.db_session.query(ChunkTaskTable).filter(
            ChunkTaskTable.id.in_([str(tid) for tid in task_ids])
        ).update({
            "status": status.value,
            "updated_at": datetime.utcnow()
        }, synchronize_session=False)

        self.db_session.commit()
        return updated

    def get_processing_stats(
        self,
        transcript_id: UUID
    ) -> ProcessingStats:
        """Get aggregate statistics for transcript processing"""
        total = self.db_session.query(ProcessingTable).filter_by(
            transcript_id=str(transcript_id)
        ).count()

        completed = self.db_session.query(ProcessingTable).filter(
            ProcessingTable.transcript_id == str(transcript_id),
            ProcessingTable.status == "COMPLETED"
        ).count()

        failed = self.db_session.query(ProcessingTable).filter(
            ProcessingTable.transcript_id == str(transcript_id),
            ProcessingTable.status == "FAILED"
        ).count()

        avg_duration = self.db_session.query(
            func.avg(
                ProcessingTable.completed_at - ProcessingTable.started_at
            )
        ).filter(
            ProcessingTable.transcript_id == str(transcript_id),
            ProcessingTable.status == "COMPLETED"
        ).scalar()

        return ProcessingStats(
            total=total,
            completed=completed,
            failed=failed,
            avg_duration_seconds=int(avg_duration.total_seconds()) if avg_duration else 0
        )
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

    def get_sum(
        self,
        metric_name: str,
        range: TimeRange,
        tags: Dict[str, str] = None
    ) -> float:
        """Get sum of metric values over time range"""
        query = f"sum_over_time({self._build_promql_query(metric_name, tags)}[{range.step}s])"

        result = self.prometheus_client.custom_query_range(
            query=query,
            start_time=range.start,
            end_time=range.end,
            step=range.step
        )

        if result and result[0]["values"]:
            values = [float(v[1]) for v in result[0]["values"]]
            return sum(values)

        return 0.0

    def get_average(
        self,
        metric_name: str,
        range: TimeRange,
        tags: Dict[str, str] = None
    ) -> float:
        """Get average of metric values over time range"""
        query = f"avg_over_time({self._build_promql_query(metric_name, tags)}[{range.step}s])"

        result = self.prometheus_client.custom_query_range(
            query=query,
            start_time=range.start,
            end_time=range.end,
            step=range.step
        )

        if result and result[0]["values"]:
            values = [float(v[1]) for v in result[0]["values"]]
            return sum(values) / len(values) if values else 0.0

        return 0.0

    def get_rate(
        self,
        metric_name: str,
        range: TimeRange,
        tags: Dict[str, str] = None
    ) -> float:
        """Get rate of change per second"""
        query = f"rate({self._build_promql_query(metric_name, tags)}[{range.step}s])"

        result = self.prometheus_client.custom_query_range(
            query=query,
            start_time=range.start,
            end_time=range.end,
            step=range.step
        )

        if result and result[0]["values"]:
            # Return average rate over the period
            rates = [float(v[1]) for v in result[0]["values"]]
            return sum(rates) / len(rates) if rates else 0.0

        return 0.0

    def get_iqr(
        self,
        metric_name: str,
        range: TimeRange
    ) -> float:
        """Get interquartile range (Q3 - Q1)"""
        q1 = self.get_percentile(metric_name, Percentile(value=25), range)
        q3 = self.get_percentile(metric_name, Percentile(value=75), range)
        return q3 - q1

    def get_stddev(
        self,
        metric_name: str,
        range: TimeRange
    ) -> float:
        """Get standard deviation of metric values"""
        # Use PromQL stddev function if available
        query = f"stddev_over_time({metric_name}[{range.step}s])"

        result = self.prometheus_client.custom_query_range(
            query=query,
            start_time=range.start,
            end_time=range.end,
            step=range.step
        )

        if result and result[0]["values"]:
            values = [float(v[1]) for v in result[0]["values"]]
            return sum(values) / len(values) if values else 0.0

        return 0.0

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

## Bulk Operations

### Bulk Insert

```python
class BulkInsertSpec:
    """Specification for bulk insert operations"""

    def __init__(
        self,
        batch_size: int = 1000,
        continue_on_error: bool = False,
        update_on_conflict: bool = True
    ):
        self.batch_size = batch_size
        self.continue_on_error = continue_on_error
        self.update_on_conflict = update_on_conflict

class JobQueueRepository:

    def bulk_enqueue(
        self,
        jobs: List[Job],
        spec: BulkInsertSpec = None
    ) -> List[JobId]:
        """Enqueue multiple jobs efficiently"""
        if spec is None:
            spec = BulkInsertSpec()

        job_ids = []

        # Process in batches
        for i in range(0, len(jobs), spec.batch_size):
            batch = jobs[i:i + spec.batch_size]

            try:
                # Bulk insert to PostgreSQL
                query = """
                INSERT INTO processing_jobs (
                    id, type, payload, priority, status,
                    retry_count, max_retries, created_at,
                    transcript_id
                ) VALUES """
                values = []
                params = []

                for job in batch:
                    values.append("(%s, %s, %s, %s, %s, %s, %s, %s, %s)")
                    params.extend([
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
                    job_ids.append(job.id)

                query += ", ".join(values)

                if spec.update_on_conflict:
                    query += """
                    ON CONFLICT (id) DO UPDATE SET
                        status = EXCLUDED.status,
                        updated_at = NOW(),
                        retry_count = EXCLUDED.retry_count
                    """

                self._execute_query(query, params)

            except Exception as e:
                if not spec.continue_on_error:
                    raise
                # Log error and continue with next batch

        return job_ids
```

**TypeScript Equivalent:**

```typescript
interface BulkInsertSpec {
  batchSize?: number;
  continueOnError?: boolean;
  updateOnConflict?: boolean;
}

class JobQueueRepository {
  async bulkEnqueue(
    jobs: Job[],
    spec: BulkInsertSpec = {}
  ): Promise<JobId[]> {
    const batchSize = spec.batchSize ?? 1000;
    const continueOnError = spec.continueOnError ?? false;
    const updateOnConflict = spec.updateOnConflict ?? true;

    const jobIds: JobId[] = [];

    for (let i = 0; i < jobs.length; i += batchSize) {
      const batch = jobs.slice(i, i + batchSize);

      try {
        const query = `
          INSERT INTO processing_jobs (
            id, type, payload, priority, status,
            retry_count, max_retries, created_at, transcript_id
          ) VALUES ${batch.map((_, idx) => {
            const offset = idx * 9;
            return `($${offset + 1}, $${offset + 2}, $${offset + 3}, $${offset + 4}, $${offset + 5}, $${offset + 6}, $${offset + 7}, $${offset + 8}, $${offset + 9})`;
          }).join(',')}
          ${updateOnConflict ? `
          ON CONFLICT (id) DO UPDATE SET
            status = EXCLUDED.status,
            updated_at = NOW(),
            retry_count = EXCLUDED.retry_count
          ` : ''}
        `;

        const params: any[] = [];
        for (const job of batch) {
          params.push(
            job.id.toString(),
            job.type,
            JSON.stringify(job.payload),
            job.priority,
            job.status,
            job.retryCount,
            job.maxRetries,
            job.createdAt,
            job.transcriptId.toString()
          );
          jobIds.push(job.id);
        }

        await this.executeQuery(query, params);

      } catch (error) {
        if (!continueOnError) {
          throw error;
        }
        // Log error and continue
      }
    }

    return jobIds;
  }
}
```

### Bulk Update

```python
class BulkUpdateSpec:
    """Specification for bulk update operations"""
    def __init__(
        self,
        batch_size: int = 500,
        validate_before_update: bool = True
    ):
        self.batch_size = batch_size
        self.validate_before_update = validate_before_update

class ProcessingRepository:

    def bulk_update_progress(
        self,
        updates: List[Tuple[ProcessingId, float]],
        spec: BulkUpdateSpec = None
    ) -> int:
        """Update progress for multiple processings"""
        if spec is None:
            spec = BulkUpdateSpec()

        total_updated = 0

        for i in range(0, len(updates), spec.batch_size):
            batch = updates[i:i + spec.batch_size]

            # Build CASE statement for bulk update
            query = """
            UPDATE processing_tasks
            SET progress = CASE id
            """

            params = []
            case_clauses = []

            for processing_id, progress in batch:
                case_clauses.append("WHEN %s THEN %s")
                params.extend([str(processing_id), progress])

            query += " ".join(case_clauses)
            query += f" END, updated_at = NOW() WHERE id IN ({','.join(['%s'] * len(batch))})"

            # Add IDs for WHERE clause
            params.extend([str(pid) for pid, _ in batch])

            result = self._execute_query(query, params)
            total_updated += result.rowcount

        self.db_session.commit()
        return total_updated
```

---

## Pagination

### Pagination Specification

```python
@dataclass(frozen=True)
class PageSpec:
    """Pagination specification"""
    page: int = 1
    size: int = 20
    sort_by: str = "created_at"
    sort_order: str = "DESC"  # ASC or DESC

    def __post_init__(self):
        if self.page < 1:
            raise ValueError("Page must be >= 1")
        if self.size < 1 or self.size > 100:
            raise ValueError("Size must be between 1 and 100")

        valid_orders = ["ASC", "DESC"]
        if self.sort_order not in valid_orders:
            raise ValueError(f"Sort order must be one of {valid_orders}")

    @property
    def offset(self) -> int:
        """Calculate offset from page and size"""
        return (self.page - 1) * self.size

@dataclass(frozen=True)
class PagedResult[T]:
    """Paged query result"""
    items: List[T]
    total: int
    page: int
    size: int
    total_pages: int

    @property
    def has_next(self) -> bool:
        return self.page < self.total_pages

    @property
    def has_previous(self) -> bool:
        return self.page > 1

    @classmethod
    def create(
        cls,
        items: List[T],
        total: int,
        spec: PageSpec
    ) -> "PagedResult[T]":
        total_pages = (total + spec.size - 1) // spec.size
        return cls(
            items=items,
            total=total,
            page=spec.page,
            size=spec.size,
            total_pages=total_pages
        )
```

**TypeScript Equivalent:**

```typescript
class PageSpec {
  readonly offset: number;

  constructor(
    readonly page: number = 1,
    readonly size: number = 20,
    readonly sortBy: string = "created_at",
    readonly sortOrder: "ASC" | "DESC" = "DESC"
  ) {
    if (page < 1) {
      throw new Error("Page must be >= 1");
    }
    if (size < 1 || size > 100) {
      throw new Error("Size must be between 1 and 100");
    }

    this.offset = (page - 1) * size;
  }
}

class PagedResult<T> {
  readonly totalPages: number;
  readonly hasNext: boolean;
  readonly hasPrevious: boolean;

  constructor(
    readonly items: T[],
    readonly total: number,
    readonly page: number,
    readonly size: number
  ) {
    this.totalPages = Math.ceil(total / size);
    this.hasNext = page < this.totalPages;
    this.hasPrevious = page > 1;
  }

  static create<T>(items: T[], total: number, spec: PageSpec): PagedResult<T> {
    return new PagedResult(items, total, spec.page, spec.size);
  }
}
```

### Paginated Query Implementation

```python
class JobQueueRepository:

    def find_jobs_paginated(
        self,
        spec: PageSpec = None,
        filters: Dict[str, Any] = None
    ) -> PagedResult[Job]:
        """Find jobs with pagination"""
        if spec is None:
            spec = PageSpec()

        # Build query
        query = "SELECT * FROM processing_jobs WHERE 1=1"
        params = []

        if filters:
            if "status" in filters:
                query += " AND status = %s"
                params.append(filters["status"])

            if "transcript_id" in filters:
                query += " AND transcript_id = %s"
                params.append(str(filters["transcript_id"]))

            if "type" in filters:
                query += " AND job_type = %s"
                params.append(filters["type"])

        # Get total count
        count_query = query.replace("*", "COUNT(*)")
        total = self._execute_query(count_query, params)[0]["count"]

        # Add sorting and pagination
        query += f" ORDER BY {spec.sort_by} {spec.sort_order}"
        query += " LIMIT %s OFFSET %s"
        params.extend([spec.size, spec.offset])

        # Execute query
        rows = self._execute_query(query, params)
        items = [Job.from_db_row(row) for row in rows]

        return PagedResult.create(items, total, spec)

    def find_jobs_by_user_paginated(
        self,
        user_id: UUID,
        spec: PageSpec = None
    ) -> PagedResult[Job]:
        """Find user's jobs with pagination"""
        if spec is None:
            spec = PageSpec()

        # Join with transcripts table
        query = """
        SELECT j.* FROM processing_jobs j
        INNER JOIN transcripts t ON j.transcript_id = t.id
        WHERE t.user_id = %s
        ORDER BY %s %s
        LIMIT %s OFFSET %s
        """

        params = [str(user_id), spec.sort_by, spec.sort_order, spec.size, spec.offset]

        # Get total count
        count_query = """
        SELECT COUNT(*) FROM processing_jobs j
        INNER JOIN transcripts t ON j.transcript_id = t.id
        WHERE t.user_id = %s
        """
        total = self._execute_query(count_query, [str(user_id)])[0]["count"]

        rows = self._execute_query(query, params)
        items = [Job.from_db_row(row) for row in rows]

        return PagedResult.create(items, total, spec)
```

---

## Specification Pattern

### Query Specifications

```python
from abc import ABC, abstractmethod

class Specification(ABC):
    """Base specification for queries"""

    @abstractmethod
    def to_sql(self) -> Tuple[str, List[Any]]:
        """Convert to SQL WHERE clause and parameters"""
        pass

    def and_(self, other: Specification) -> "AndSpecification":
        return AndSpecification(self, other)

    def or_(self, other: Specification) -> "OrSpecification":
        return OrSpecification(self, other)

    def not_(self) -> "NotSpecification":
        return NotSpecification(self)

class JobStatusSpecification(Specification):
    """Filter jobs by status"""

    def __init__(self, status: JobStatus):
        self.status = status

    def to_sql(self) -> Tuple[str, List[Any]]:
        return "status = %s", [self.status.value]

class JobPrioritySpecification(Specification):
    """Filter jobs by minimum priority"""

    def __init__(self, min_priority: JobPriority):
        self.min_priority = min_priority

    def to_sql(self) -> Tuple[str, List[Any]]:
        return "priority >= %s", [self.min_priority.value]

class JobDateRangeSpecification(Specification):
    """Filter jobs by date range"""

    def __init__(self, start: datetime, end: datetime):
        self.start = start
        self.end = end

    def to_sql(self) -> Tuple[str, List[Any]]:
        return "created_at BETWEEN %s AND %s", [self.start, self.end]

class AndSpecification(Specification):
    """Combine specifications with AND"""

    def __init__(self, *specs: Specification):
        self.specs = specs

    def to_sql(self) -> Tuple[str, List[Any]]:
        clauses = []
        params = []

        for spec in self.specs:
            clause, spec_params = spec.to_sql()
            clauses.append(f"({clause})")
            params.extend(spec_params)

        return " AND ".join(clauses), params

class OrSpecification(Specification):
    """Combine specifications with OR"""

    def __init__(self, *specs: Specification):
        self.specs = specs

    def to_sql(self) -> Tuple[str, List[Any]]:
        clauses = []
        params = []

        for spec in self.specs:
            clause, spec_params = spec.to_sql()
            clauses.append(f"({clause})")
            params.extend(spec_params)

        return " OR ".join(clauses), params

class JobQueueRepository:

    def find_by_specification(
        self,
        spec: Specification,
        page_spec: PageSpec = None
    ) -> PagedResult[Job]:
        """Find jobs using specification pattern"""
        if page_spec is None:
            page_spec = PageSpec()

        where_clause, params = spec.to_sql()

        # Build query
        query = f"SELECT * FROM processing_jobs WHERE {where_clause}"
        query += f" ORDER BY {page_spec.sort_by} {page_spec.sort_order}"
        query += " LIMIT %s OFFSET %s"
        params.extend([page_spec.size, page_spec.offset])

        # Get total count
        count_query = f"SELECT COUNT(*) FROM processing_jobs WHERE {where_clause}"
        total = self._execute_query(count_query, params[:len(params)-2])[0]["count"]

        rows = self._execute_query(query, params)
        items = [Job.from_db_row(row) for row in rows]

        return PagedResult.create(items, total, page_spec)

# Usage example
spec = JobStatusSpecification(JobStatus.QUEUED).and_(
    JobPrioritySpecification(JobPriority.high())
).and_(
    JobDateRangeSpecification(
        start=datetime.utcnow() - timedelta(days=7),
        end=datetime.utcnow()
    )
)

jobs = repository.find_by_specification(spec, PageSpec(page=1, size=20))
```

**TypeScript Equivalent:**

```typescript
abstract class Specification {
  abstract toSql(): [string, any[]];

  and(other: Specification): AndSpecification {
    return new AndSpecification(this, other);
  }

  or(other: Specification): OrSpecification {
    return new OrSpecification(this, other);
  }

  not(): NotSpecification {
    return new NotSpecification(this);
  }
}

class JobStatusSpecification extends Specification {
  constructor(private status: JobStatus) {
    super();
  }

  toSql(): [string, any[]] {
    return ["status = $1", [this.status]];
  }
}

class JobPrioritySpecification extends Specification {
  constructor(private minPriority: JobPriority) {
    super();
  }

  toSql(): [string, any[]] {
    return ["priority >= $1", [this.minPriority]];
  }
}

class AndSpecification extends Specification {
  constructor(private specs: Specification[]) {
    super();
  }

  toSql(): [string, any[]] {
    const clauses: string[] = [];
    const params: any[] = [];

    for (const spec of this.specs) {
      const [clause, specParams] = spec.toSql();
      clauses.push(`(${clause})`);
      params.push(...specParams);
    }

    return [clauses.join(" AND "), params];
  }
}
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
