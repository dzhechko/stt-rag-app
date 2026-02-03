# Tactical Design - Aggregates

**Feature:** Performance Optimizations
**Version:** 1.0
**Date:** 2026-02-03

---

## Overview

This document defines the Aggregates for the Performance Optimization feature. Aggregates are clusters of domain objects that can be treated as a single unit.

---

## Aggregate Definitions

### 1. JobQueue Aggregate

**Responsibility:** Manage job lifecycle, priority, and retry logic.

**Aggregate Root:** `JobQueue`

**Entities:**
- `Job` - Individual job with status and payload
- `JobAttempt` - Track retry attempts

**Value Objects:**
- `JobId` - Unique identifier
- `JobPriority` - High/Medium/Low
- `JobStatus` - Queued/Processing/Completed/Failed
- `RetryConfig` - Max retries, backoff strategy
- `JobPayload` - Encrypted job data

**Invariants:**
1. A job can only be in one state at a time
2. Failed jobs can only retry if retry_count < max_retries
3. Priority changes only allowed before job starts
4. Job payload cannot be modified after queuing

**Repository:** `JobQueueRepository`

```python
class JobQueue(AggregateRoot):
    """Aggregate root for job queue management"""

    def __init__(self, queue_id: QueueId):
        self.queue_id = queue_id
        self.jobs: Dict[JobId, Job] = {}

    def enqueue(
        self,
        job_type: JobType,
        payload: JobPayload,
        priority: JobPriority
    ) -> JobId:
        """Add job to queue"""
        job_id = JobId.generate()
        job = Job(
            id=job_id,
            type=job_type,
            payload=payload,
            priority=priority,
            status=JobStatus.QUEUED
        )
        self.jobs[job_id] = job

        # Publish event
        self._publish_event(
            JobQueued(
                job_id=job_id,
                job_type=job_type,
                priority=priority
            )
        )

        return job_id

    def start_processing(self, job_id: JobId, worker_id: str) -> None:
        """Mark job as processing"""
        job = self._get_job(job_id)
        job.start_processing(worker_id)

        self._publish_event(
            JobStarted(job_id=job_id, worker_id=worker_id)
        )

    def complete_job(
        self,
        job_id: JobId,
        result: JobResult
    ) -> None:
        """Mark job as completed"""
        job = self._get_job(job_id)
        job.complete(result)

        self._publish_event(
            JobCompleted(job_id=job_id, result=result)
        )

    def fail_job(
        self,
        job_id: JobId,
        error: JobError
    ) -> None:
        """Mark job as failed, schedule retry if allowed"""
        job = self._get_job(job_id)

        if job.can_retry():
            job.schedule_retry(error)
            self._publish_event(
                JobRetryScheduled(
                    job_id=job_id,
                    retry_attempt=job.retry_count
                )
            )
        else:
            job.fail_permanently(error)
            self._publish_event(
                JobFailed(job_id=job_id, error=error)
            )

    def update_progress(
        self,
        job_id: JobId,
        progress: float
    ) -> None:
        """Update job progress"""
        job = self._get_job(job_id)
        job.update_progress(progress)

        self._publish_event(
            JobProgressUpdated(job_id=job_id, progress=progress)
        )
```

---

### 2. CacheManager Aggregate

**Responsibility:** Manage multi-level cache with invalidation.

**Aggregate Root:** `CacheManager`

**Entities:**
- `CacheEntry` - Cached data with metadata
- `CacheLevel` - L1/L2/L3 storage configuration

**Value Objects:**
- `CacheKey` - Content-addressed key
- `CacheValue` - Cached data
- `TTL` - Time to live
- `CacheStats` - Hit/miss statistics

**Invariants:**
1. Cache key is always content-addressed (hash-based)
2. L1 is subset of L2, L2 is subset of L3
3. TTL is enforced at lookup time
4. Only one entry per key per level

**Repository:** `CacheRepository`

```python
class CacheManager(AggregateRoot):
    """Aggregate root for multi-level cache management"""

    def __init__(self):
        self.l1_cache: InMemoryCache()  # Dict-based
        self.l2_cache: RedisCache()     # Redis
        self.l3_cache: DatabaseCache()  # PostgreSQL

    def get(self, key: CacheKey) -> Optional[CacheValue]:
        """Lookup across all cache levels"""
        # L1 check
        value = self.l1_cache.get(key)
        if value:
            self._publish_event(
                CacheEntryAccessed(
                    cache_key=key,
                    cache_level="L1",
                    was_hit=True
                )
            )
            return value

        # L2 check
        value = self.l2_cache.get(key)
        if value:
            # Promote to L1
            self.l1_cache.put(key, value, ttl=5m)
            self._publish_event(
                CacheEntryAccessed(
                    cache_key=key,
                    cache_level="L2",
                    was_hit=True
                )
            )
            return value

        # L3 check
        value = self.l3_cache.get(key)
        if value:
            # Promote to L2, then L1
            self.l2_cache.put(key, value, ttl=24h)
            self.l1_cache.put(key, value, ttl=5m)
            self._publish_event(
                CacheEntryAccessed(
                    cache_key=key,
                    cache_level="L3",
                    was_hit=True
                )
            )
            return value

        # Cache miss
        self._publish_event(
            CacheEntryAccessed(
                cache_key=key,
                cache_level="ALL",
                was_hit=False
            )
        )
        return None

    def put(
        self,
        key: CacheKey,
        value: CacheValue,
        ttl: TTL
    ) -> None:
        """Store in all cache levels"""
        self.l1_cache.put(key, value, ttl=min(ttl, 5m))
        self.l2_cache.put(key, value, ttl=min(ttl, 24h))
        self.l3_cache.put(key, value, ttl)

        self._publish_event(
            CacheEntryCreated(
                cache_key=key,
                entry_size=len(value),
                ttl=ttl
            )
        )

    def invalidate(self, key: CacheKey) -> None:
        """Remove from all cache levels"""
        self.l1_cache.delete(key)
        self.l2_cache.delete(key)
        self.l3_cache.delete(key)

        self._publish_event(
            CacheEntryInvalidated(
                cache_key=key,
                reason="explicit"
            )
        )

    def get_stats(self) -> CacheStats:
        """Get aggregate cache statistics"""
        return CacheStats(
            l1_size=self.l1_cache.size(),
            l2_size=self.l2_cache.size(),
            l3_size=self.l3_cache.size(),
            hit_rate=self._calculate_hit_rate()
        )
```

---

### 3. ParallelProcessor Aggregate

**Responsibility:** Orchestrate parallel chunk processing.

**Aggregate Root:** `ParallelProcessor`

**Entities:**
- `ProcessingTask` - Individual chunk task
- `ChunkResult` - Result from chunk processing

**Value Objects:**
- `ConcurrencyLimit` - Max parallel tasks
- `ChunkSize` - Optimal chunk size
- `ProcessingStrategy` - How to process chunks
- `MergeStrategy` - How to combine results

**Invariants:**
1. Never exceed concurrency limit
2. Chunks processed in any order, merged in order
3. Failed chunks trigger retry before failing overall
4. Progress is accurate and monotonic

**Repository:** `ProcessingRepository`

```python
class ParallelProcessor(AggregateRoot):
    """Aggregate root for parallel processing orchestration"""

    def __init__(
        self,
        concurrency_limit: ConcurrencyLimit = ConcurrencyLimit(4)
    ):
        self.concurrency_limit = concurrency_limit
        self.active_tasks: Dict[TaskId, ProcessingTask] = {}
        self.completed_results: List[ChunkResult] = []

    def process_file(
        self,
        file: AudioFile,
        strategy: ProcessingStrategy
    ) -> ProcessingId:
        """Start parallel processing of file"""
        # Calculate optimal chunk size
        chunk_size = self._calculate_optimal_chunk_size(file)

        # Split file into chunks
        chunks = file.split_into_chunks(chunk_size)

        processing_id = ProcessingId.generate()

        # Create processing tasks
        for index, chunk in enumerate(chunks):
            task_id = TaskId.generate()
            task = ProcessingTask(
                id=task_id,
                processing_id=processing_id,
                chunk=chunk,
                index=index,
                total_chunks=len(chunks)
            )
            self.active_tasks[task_id] = task

            self._publish_event(
                ChunkProcessingStarted(
                    task_id=task_id,
                    chunk_index=index,
                    total_chunks=len(chunks)
                )
            )

        # Start parallel execution
        asyncio.create_task(
            self._execute_parallel(processing_id, strategy)
        )

        return processing_id

    async def _execute_parallel(
        self,
        processing_id: ProcessingId,
        strategy: ProcessingStrategy
    ) -> None:
        """Execute chunks with controlled concurrency"""
        semaphore = asyncio.Semaphore(
            self.concurrency_limit.value
        )

        async def process_with_limit(task: ProcessingTask):
            async with semaphore:
                return await self._process_single_chunk(task, strategy)

        # Process all chunks concurrently (with limit)
        results = await asyncio.gather(
            *[
                process_with_limit(task)
                for task in self.active_tasks.values()
            ],
            return_exceptions=True
        )

        # Merge results in order
        ordered_results = self._order_results(results)

        self._publish_event(
            FileProcessingCompleted(
                processing_id=processing_id,
                results=ordered_results
            )
        )

    async def _process_single_chunk(
        self,
        task: ProcessingTask,
        strategy: ProcessingStrategy
    ) -> ChunkResult:
        """Process single chunk with retry"""
        for attempt in range(strategy.max_retries):
            try:
                # Check cache first
                cache_key = CacheKey.from_content(task.chunk.data)
                cached = self._cache.get(cache_key)
                if cached:
                    return ChunkResult.from_cache(cached, task.index)

                # Process via API
                result = await self._api_client.transcribe(task.chunk)

                # Cache result
                self._cache.put(cache_key, result, ttl=24h)

                self._publish_event(
                    ChunkProcessingCompleted(
                        task_id=task.id,
                        was_cached=False
                    )
                )

                return ChunkResult.from_api(result, task.index)

            except TransientError as e:
                if attempt < strategy.max_retries - 1:
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff
                    continue
                else:
                    self._publish_event(
                        ChunkProcessingFailed(
                            task_id=task.id,
                            error=str(e)
                        )
                    )
                    raise

    def _calculate_optimal_chunk_size(
        self,
        file: AudioFile
    ) -> ChunkSize:
        """Calculate optimal chunk size based on file characteristics"""
        # Base size on file size (larger files = larger chunks)
        base_size = 20  # MB

        # Adjust for audio quality
        if file.bitrate > 320:
            base_size = 25
        elif file.bitrate < 128:
            base_size = 15

        # Respect API limit
        max_size = 25  # MB (Cloud.ru limit)
        optimal_size = min(base_size, max_size)

        return ChunkSize(optimal_size)
```

---

### 4. MetricsCollector Aggregate

**Responsibility:** Collect and aggregate performance metrics.

**Aggregate Root:** `MetricsCollector`

**Entities:**
- `MetricSeries` - Time-series of metric values
- `AlertRule` - Alert threshold configuration

**Value Objects:**
- `MetricName` - e.g., "processing.duration"
- `MetricValue` - Numeric value with tags
- `Percentile` - p50, p95, p99
- `Threshold` - Alert trigger value

**Invariants:**
1. Metrics are immutable once recorded
2. Percentiles computed over sliding window
3. Alerts triggered only once per condition
4. Time-series data expires after retention period

**Repository:** `MetricsRepository`

```python
class MetricsCollector(AggregateRoot):
    """Aggregate root for metrics collection and aggregation"""

    def __init__(self):
        self.series: Dict[MetricName, MetricSeries] = {}
        self.alert_rules: List[AlertRule] = []

    def record_metric(
        self,
        name: MetricName,
        value: MetricValue,
        tags: Dict[str, str] = None
    ) -> None:
        """Record a metric value"""
        if name not in self.series:
            self.series[name] = MetricSeries(name=name)

        self.series[name].add_value(value, tags)

        self._publish_event(
            MetricRecorded(
                metric_name=name,
                metric_value=value.value,
                metric_type=value.metric_type,
                tags=tags or {}
            )
        )

        # Check alerts
        self._check_alerts(name, value)

    def get_percentile(
        self,
        name: MetricName,
        percentile: Percentile,
        window: timedelta = timedelta(minutes=5)
    ) -> float:
        """Get percentile value for metric"""
        series = self.series.get(name)
        if not series:
            return 0.0

        return series.calculate_percentile(
            percentile=percentile,
            window=window
        )

    def create_alert_rule(
        self,
        name: str,
        metric_name: MetricName,
        threshold: Threshold,
        severity: str
    ) -> AlertRuleId:
        """Create new alert rule"""
        rule_id = AlertRuleId.generate()
        rule = AlertRule(
            id=rule_id,
            name=name,
            metric_name=metric_name,
            threshold=threshold,
            severity=severity
        )
        self.alert_rules.append(rule)
        return rule_id

    def _check_alerts(
        self,
        metric_name: MetricName,
        value: MetricValue
    ) -> None:
        """Check if any alert rules triggered"""
        for rule in self.alert_rules:
            if rule.metric_name == metric_name:
                if rule.is_triggered(value.value):
                    self._publish_event(
                        AlertTriggered(
                            alert_rule_id=rule.id,
                            alert_name=rule.name,
                            current_value=value.value,
                            threshold=rule.threshold.value
                        )
                    )
```

---

## Aggregate Relationships

```
┌─────────────────────────────────────────────────────────────────┐
│                      Core Domain (Shared Kernel)                 │
│  Transcript | AudioFile | ProcessingJob | Summary | RAGSession  │
└────────────────────────────┬────────────────────────────────────┘
                             │
        ┌────────────────────┼────────────────────┐
        │                    │                    │
┌───────▼────────┐  ┌────────▼────────┐  ┌───────▼────────┐
│ JobQueue       │  │ CacheManager    │  │ ParallelProc.  │
│ Aggregate      │  │ Aggregate       │  │ Aggregate      │
│                │  │                 │  │                │
│ - Job          │  │ - CacheEntry    │  │ - Processing   │
│ - JobAttempt   │  │ - CacheLevel    │  │   Task         │
│                │  │                 │  │ - ChunkResult  │
└────────────────┘  └─────────────────┘  └────────────────┘
        │                    │                    │
        └────────────────────┼────────────────────┘
                             │
                             ▼
                   ┌─────────────────────┐
                   │ MetricsCollector    │
                   │ Aggregate           │
                   │                     │
                   │ - MetricSeries      │
                   │ - AlertRule        │
                   └─────────────────────┘
```

---

## Aggregate Lifecycle

### JobQueue Aggregate

**Lifecycle States:**
1. **Created** - Queue initialized
2. **Active** - Jobs being enqueued/processed
3. **Draining** - No new jobs, finishing existing
4. **Shutdown** - All jobs complete

**State Transitions:**
```
Created → Active → Draining → Shutdown
                     ↑______________|
```

---

### CacheManager Aggregate

**Lifecycle States:**
1. **Initialized** - Cache levels created
2. **Warming** - Pre-loading frequent entries
3. **Active** - Normal operation
4. **Stale** - Needs refresh
5. **Invalidated** - All entries cleared

**State Transitions:**
```
Initialized → Warming → Active → Stale → Invalidated
                                    ↑__________|
```

---

### ParallelProcessor Aggregate

**Lifecycle States:**
1. **Idle** - No active processing
2. **Splitting** - Dividing file into chunks
3. **Processing** - Chunks being processed
4. **Merging** - Combining results
5. **Completed** - Results ready
6. **Failed** - Error occurred

**State Transitions:**
```
Idle → Splitting → Processing → Merging → Completed
                                   ↓
                                Failed
```

---

## Aggregate Persistence

### Repositories

```python
# JobQueue Repository
class JobQueueRepository(Repository[JobQueue]):
    def save(self, queue: JobQueue) -> None:
        """Persist queue state to PostgreSQL + Redis"""
        ...

    def load(self, queue_id: QueueId) -> JobQueue:
        """Load queue state from PostgreSQL + Redis"""
        ...

    def find_pending_jobs(
        self,
        queue_name: str,
        limit: int
    ) -> List[Job]:
        """Find jobs ready for processing"""
        ...

# CacheManager Repository
class CacheRepository(Repository[CacheManager]):
    def save_l1(self, cache: CacheManager) -> None:
        """Persist L1 cache to memory (no-op)"""
        ...

    def save_l2(self, cache: CacheManager) -> None:
        """Persist L2 cache to Redis"""
        ...

    def save_l3(self, cache: CacheManager) -> None:
        """Persist L3 cache to PostgreSQL"""
        ...

# ParallelProcessor Repository
class ProcessingRepository(Repository[ParallelProcessor]):
    def save(self, processor: ParallelProcessor) -> None:
        """Persist processing state"""
        ...

    def load(self, processing_id: ProcessingId) -> ParallelProcessor:
        """Load processing state"""
        ...

# MetricsCollector Repository
class MetricsRepository(Repository[MetricsCollector]):
    def save(self, collector: MetricsCollector) -> None:
        """Persist metrics to Prometheus"""
        ...

    def query_time_series(
        self,
        metric_name: MetricName,
        range: TimeRange
    ) -> List[MetricValue]:
        """Query metric time series"""
        ...
```

---

## Aggregate Design Principles

### 1. Consistency Boundary

Each aggregate maintains its own consistency:
- **JobQueue**: Job state transitions are atomic
- **CacheManager**: Cache operations are atomic per key
- **ParallelProcessor**: Chunk processing is independent
- **MetricsCollector**: Metric recording is append-only

### 2. Event Sourcing

Aggregate state changes produce domain events:
- Every state transition publishes an event
- Events are stored for replay/audit
- Projections built from event stream

### 3. Optimistic Concurrency

Aggregates use optimistic concurrency:
- Version number incremented on each change
- Conflicts detected and resolved by retry
- No long-running transactions

---

**Document Control**

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-02-03 | Performance Team | Initial aggregates |
