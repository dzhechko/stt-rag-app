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

### 5. ConnectionPool Aggregate

**Responsibility:** Manage database connection pool lifecycle and health.

**Aggregate Root:** `ConnectionPool`

**Entities:**
- `Connection` - Individual database connection

**Value Objects:**
- `PoolSize` - Min/max pool configuration
- `PoolStatus` - Healthy/Unhealthy/Draining
- `ConnectionStats` - Active/idle connection counts

**Invariants:**
1. Active connections never exceed max size
2. Minimum connections always available
3. Failed connections are recycled
4. Pool maintains health check interval

**Repository:** `ConnectionPoolRepository`

```python
class ConnectionPool(AggregateRoot):
    """Aggregate root for database connection pool"""

    def __init__(
        self,
        pool_id: PoolId,
        min_size: PoolSize,
        max_size: PoolSize
    ):
        self.pool_id = pool_id
        self.min_size = min_size
        self.max_size = max_size
        self.connections: Dict[ConnectionId, Connection] = {}
        self.status = PoolStatus.INITIALIZING

    def initialize(self) -> None:
        """Initialize pool with minimum connections"""
        for _ in range(self.min_size.value):
            conn_id = ConnectionId.generate()
            conn = Connection(id=conn_id, pool_id=self.pool_id)
            self.connections[conn_id] = conn

        self.status = PoolStatus.HEALTHY
        self._publish_event(
            PoolInitialized(
                pool_id=self.pool_id,
                initial_size=len(self.connections)
            )
        )

    def acquire(self, timeout: timedelta) -> Optional[Connection]:
        """Acquire connection from pool"""
        # Find idle connection
        for conn in self.connections.values():
            if conn.is_idle():
                conn.acquire()
                self._publish_event(
                    ConnectionAcquired(
                        connection_id=conn.id,
                        pool_id=self.pool_id
                    )
                )
                return conn

        # Create new connection if under max
        if len(self.connections) < self.max_size.value:
            conn_id = ConnectionId.generate()
            conn = Connection(id=conn_id, pool_id=self.pool_id)
            conn.acquire()
            self.connections[conn_id] = conn

            self._publish_event(
                ConnectionCreated(
                    connection_id=conn_id,
                    pool_id=self.pool_id
                )
            )
            return conn

        # Pool exhausted
        return None

    def release(self, connection_id: ConnectionId) -> None:
        """Release connection back to pool"""
        conn = self.connections.get(connection_id)
        if conn and conn.is_acquired():
            conn.release()

            self._publish_event(
                ConnectionReleased(
                    connection_id=connection_id,
                    pool_id=self.pool_id
                )
            )

    def remove_failed(self, connection_id: ConnectionId) -> None:
        """Remove failed connection from pool"""
        if connection_id in self.connections:
            del self.connections[connection_id]

            self._publish_event(
                ConnectionFailed(
                    connection_id=connection_id,
                    pool_id=self.pool_id
                )
            )

    def get_stats(self) -> ConnectionStats:
        """Get pool statistics"""
        active = sum(1 for c in self.connections.values() if c.is_acquired())
        idle = sum(1 for c in self.connections.values() if c.is_idle())

        return ConnectionStats(
            total=len(self.connections),
            active=active,
            idle=idle,
            utilization=active / len(self.connections) if self.connections else 0
        )

    def scale_to(self, target_size: int) -> None:
        """Scale pool to target size"""
        target_size = max(self.min_size.value, min(target_size, self.max_size.value))
        current_size = len(self.connections)

        if target_size > current_size:
            # Add connections
            for _ in range(target_size - current_size):
                conn_id = ConnectionId.generate()
                conn = Connection(id=conn_id, pool_id=self.pool_id)
                self.connections[conn_id] = conn
        elif target_size < current_size:
            # Remove idle connections
            idle_conns = [
                c for c in self.connections.values()
                if c.is_idle()
            ][:current_size - target_size]

            for conn in idle_conns:
                del self.connections[conn.id]

        self._publish_event(
            PoolResized(
                pool_id=self.pool_id,
                old_size=current_size,
                new_size=len(self.connections)
            )
        )
```

**TypeScript Equivalent:**

```typescript
class ConnectionPool extends AggregateRoot {
  private connections: Map<ConnectionId, Connection> = new Map();
  private status: PoolStatus = PoolStatus.Initializing;

  constructor(
    private poolId: PoolId,
    private minSize: PoolSize,
    private maxSize: PoolSize
  ) {
    super();
  }

  initialize(): void {
    for (let i = 0; i < this.minSize.value; i++) {
      const connId = ConnectionId.generate();
      const conn = new Connection(connId, this.poolId);
      this.connections.set(connId, conn);
    }

    this.status = PoolStatus.Healthy;
    this.publishEvent(new PoolInitialized(this.poolId, this.connections.size));
  }

  acquire(timeout: TimeSpan): Connection | null {
    // Find idle connection
    for (const conn of this.connections.values()) {
      if (conn.isIdle()) {
        conn.acquire();
        this.publishEvent(new ConnectionAcquired(conn.id, this.poolId));
        return conn;
      }
    }

    // Create new connection if under max
    if (this.connections.size < this.maxSize.value) {
      const connId = ConnectionId.generate();
      const conn = new Connection(connId, this.poolId);
      conn.acquire();
      this.connections.set(connId, conn);

      this.publishEvent(new ConnectionCreated(connId, this.poolId));
      return conn;
    }

    return null;
  }

  release(connectionId: ConnectionId): void {
    const conn = this.connections.get(connectionId);
    if (conn && conn.isAcquired()) {
      conn.release();
      this.publishEvent(new ConnectionReleased(connectionId, this.poolId));
    }
  }

  removeFailed(connectionId: ConnectionId): void {
    if (this.connections.has(connectionId)) {
      this.connections.delete(connectionId);
      this.publishEvent(new ConnectionFailed(connectionId, this.poolId));
    }
  }

  getStats(): ConnectionStats {
    let active = 0;
    let idle = 0;

    for (const conn of this.connections.values()) {
      if (conn.isAcquired()) active++;
      else if (conn.isIdle()) idle++;
    }

    return {
      total: this.connections.size,
      active,
      idle,
      utilization: this.connections.size > 0 ? active / this.connections.size : 0
    };
  }

  scaleTo(targetSize: number): void {
    const clampedSize = Math.max(
      this.minSize.value,
      Math.min(targetSize, this.maxSize.value)
    );
    const currentSize = this.connections.size;

    if (clampedSize > currentSize) {
      for (let i = 0; i < clampedSize - currentSize; i++) {
        const connId = ConnectionId.generate();
        const conn = new Connection(connId, this.poolId);
        this.connections.set(connId, conn);
      }
    } else if (clampedSize < currentSize) {
      const idleConns = Array.from(this.connections.values())
        .filter(c => c.isIdle())
        .slice(0, currentSize - clampedSize);

      for (const conn of idleConns) {
        this.connections.delete(conn.id);
      }
    }

    this.publishEvent(new PoolResized(this.poolId, currentSize, this.connections.size));
  }
}
```

---

### 6. APIConnection Aggregate

**Responsibility:** Manage HTTP/2 connection pool for external APIs.

**Aggregate Root:** `APIConnection`

**Entities:**
- `HTTP2Connection` - Individual HTTP/2 connection

**Value Objects:**
- `APIEndpoint` - API URL and configuration
- `RateLimit` - Request rate limit configuration
- `ConnectionHealth` - Health status metrics

**Invariants:**
1. Rate limits are never exceeded
2. Maximum concurrent streams per connection
3. Failed connections trigger backoff
4. Connection reuse within keep-alive period

**Repository:** `APIConnectionRepository`

```python
class APIConnection(AggregateRoot):
    """Aggregate root for HTTP/2 API connection pool"""

    def __init__(
        self,
        endpoint: APIEndpoint,
        rate_limit: RateLimit,
        max_streams: int = 100
    ):
        self.endpoint = endpoint
        self.rate_limit = rate_limit
        self.max_streams = max_streams
        self.connections: List[HTTP2Connection] = []
        self.request_queue: Queue[APIRequest] = Queue()

    def add_connection(self) -> ConnectionId:
        """Add new HTTP/2 connection to pool"""
        conn_id = ConnectionId.generate()
        conn = HTTP2Connection(
            id=conn_id,
            endpoint=self.endpoint,
            max_streams=self.max_streams
        )
        self.connections.append(conn)

        self._publish_event(
            APIConnectionCreated(
                connection_id=conn_id,
                endpoint=str(self.endpoint)
            )
        )

        return conn_id

    async def execute_request(
        self,
        request: APIRequest
    ) -> APIResponse:
        """Execute API request respecting rate limits"""
        # Check rate limit
        if not self._can_make_request():
            await self._wait_for_rate_limit()

        # Find connection with available streams
        conn = self._get_available_connection()
        if not conn:
            # Add new connection if at limit
            conn = self._add_connection()

        try:
            response = await conn.execute(request)

            self._publish_event(
                APIRequestCompleted(
                    request_id=request.id,
                    connection_id=conn.id,
                    status_code=response.status_code
                )
            )

            return response

        except APIError as e:
            self._handle_error(conn, e)
            raise

    def _can_make_request(self) -> bool:
        """Check if request respects rate limit"""
        now = datetime.utcnow()
        window_start = now - timedelta(seconds=60)

        recent_requests = [
            r for r in self.connections[0].completed_requests
            if r.completed_at > window_start
        ] if self.connections else []

        return len(recent_requests) < self.rate_limit.requests_per_minute

    async def _wait_for_rate_limit(self) -> None:
        """Wait until rate limit allows requests"""
        oldest = self.connections[0].completed_requests[0].completed_at
        wait_time = timedelta(seconds=60) - (datetime.utcnow() - oldest)
        await asyncio.sleep(wait_time.total_seconds())

    def _get_available_connection(self) -> Optional[HTTP2Connection]:
        """Get connection with available stream slots"""
        for conn in self.connections:
            if conn.active_streams < conn.max_streams:
                return conn
        return None

    def _handle_error(
        self,
        conn: HTTP2Connection,
        error: APIError
    ) -> None:
        """Handle connection error"""
        if error.is_transient():
            # Back off on transient errors
            conn.backoff_until = datetime.utcnow() + timedelta(seconds=30)
        else:
            # Remove failed connection
            self.connections.remove(conn)

        self._publish_event(
            APIConnectionError(
                connection_id=conn.id,
                error_type=error.type,
                is_transient=error.is_transient()
            )
        )

    def get_stats(self) -> ConnectionHealth:
        """Get connection pool health stats"""
        total_streams = sum(c.active_streams for c in self.connections)
        available_streams = sum(
            c.max_streams - c.active_streams
            for c in self.connections
        )

        return ConnectionHealth(
            total_connections=len(self.connections),
            active_streams=total_streams,
            available_streams=available_streams,
            utilization=total_streams / (total_streams + available_streams)
            if (total_streams + available_streams) > 0 else 0
        )
```

**TypeScript Equivalent:**

```typescript
class APIConnection extends AggregateRoot {
  private connections: HTTP2Connection[] = [];
  private requestQueue: APIRequest[] = [];

  constructor(
    private endpoint: APIEndpoint,
    private rateLimit: RateLimit,
    private maxStreams: number = 100
  ) {
    super();
  }

  addConnection(): ConnectionId {
    const connId = ConnectionId.generate();
    const conn = new HTTP2Connection(connId, this.endpoint, this.maxStreams);
    this.connections.push(conn);

    this.publishEvent(new APIConnectionCreated(connId, this.endpoint.toString()));

    return connId;
  }

  async executeRequest(request: APIRequest): Promise<APIResponse> {
    if (!this.canMakeRequest()) {
      await this.waitForRateLimit();
    }

    let conn = this.getAvailableConnection();
    if (!conn) {
      conn = this.addConnection();
    }

    try {
      const response = await conn.execute(request);

      this.publishEvent(new APIRequestCompleted(
        request.id,
        conn.id,
        response.statusCode
      ));

      return response;

    } catch (error) {
      this.handleError(conn, error as APIError);
      throw error;
    }
  }

  private canMakeRequest(): boolean {
    const now = new Date();
    const windowStart = new Date(now.getTime() - 60000);

    const recentRequests = this.connections[0]?.completedRequests.filter(
      r => r.completedAt > windowStart
    ) || [];

    return recentRequests.length < this.rateLimit.requestsPerMinute;
  }

  private async waitForRateLimit(): Promise<void> {
    const oldest = this.connections[0].completedRequests[0].completedAt;
    const waitTime = 60000 - (Date.now() - oldest.getTime());
    await new Promise(resolve => setTimeout(resolve, waitTime));
  }

  private getAvailableConnection(): HTTP2Connection | undefined {
    return this.connections.find(c => c.activeStreams < c.maxStreams);
  }

  private handleError(conn: HTTP2Connection, error: APIError): void {
    if (error.isTransient()) {
      const backoffUntil = new Date(Date.now() + 30000);
      conn.backoffUntil = backoffUntil;
    } else {
      const index = this.connections.indexOf(conn);
      this.connections.splice(index, 1);
    }

    this.publishEvent(new APIConnectionError(
      conn.id,
      error.type,
      error.isTransient()
    ));
  }

  getStats(): ConnectionHealth {
    const totalStreams = this.connections.reduce(
      (sum, c) => sum + c.activeStreams, 0
    );
    const availableStreams = this.connections.reduce(
      (sum, c) => sum + (c.maxStreams - c.activeStreams), 0
    );

    return {
      totalConnections: this.connections.length,
      activeStreams: totalStreams,
      availableStreams,
      utilization: (totalStreams + availableStreams) > 0
        ? totalStreams / (totalStreams + availableStreams)
        : 0
    };
  }
}
```

---

### 7. WorkerNode Aggregate

**Responsibility:** Manage worker node registration and job assignment.

**Aggregate Root:** `WorkerNode`

**Entities:**
- `WorkerJob` - Job assigned to worker

**Value Objects:**
- `WorkerCapabilities` - Supported job types
- `WorkerStatus` - Active/Idle/Offline/Draining
- `WorkerLoad` - Current load metrics

**Invariants:**
1. Worker only processes jobs it supports
2. Maximum concurrent jobs per worker
3. Heartbeat timeout marks worker offline
4. Draining workers receive no new jobs

**Repository:** `WorkerNodeRepository`

```python
class WorkerNode(AggregateRoot):
    """Aggregate root for worker node management"""

    def __init__(
        self,
        worker_id: WorkerId,
        capabilities: WorkerCapabilities,
        max_concurrent_jobs: int = 5
    ):
        self.worker_id = worker_id
        self.capabilities = capabilities
        self.max_concurrent_jobs = max_concurrent_jobs
        self.jobs: Dict[JobId, WorkerJob] = {}
        self.status = WorkerStatus.IDLE
        self.last_heartbeat = datetime.utcnow()

    def register(self) -> None:
        """Register worker node"""
        self.status = WorkerStatus.IDLE
        self.last_heartbeat = datetime.utcnow()

        self._publish_event(
            WorkerRegistered(
                worker_id=self.worker_id,
                capabilities=self.capabilities
            )
        )

    def assign_job(self, job: Job) -> bool:
        """Assign job to worker if capacity available"""
        if not self._can_accept_job(job):
            return False

        worker_job = WorkerJob(
            id=JobId.generate(),
            worker_id=self.worker_id,
            job_id=job.id,
            job_type=job.type
        )
        self.jobs[job.id] = worker_job

        if len(self.jobs) >= self.max_concurrent_jobs:
            self.status = WorkerStatus.ACTIVE

        self._publish_event(
            JobAssignedToWorker(
                job_id=job.id,
                worker_id=self.worker_id
            )
        )

        return True

    def complete_job(self, job_id: JobId, result: JobResult) -> None:
        """Mark job as completed"""
        if job_id in self.jobs:
            job = self.jobs[job_id]
            job.complete(result)

            # Remove from active jobs
            del self.jobs[job_id]

            if not self.jobs:
                self.status = WorkerStatus.IDLE

            self._publish_event(
                JobCompletedByWorker(
                    job_id=job_id,
                    worker_id=self.worker_id,
                    result=result
                )
            )

    def fail_job(self, job_id: JobId, error: str) -> None:
        """Mark job as failed"""
        if job_id in self.jobs:
            job = self.jobs[job_id]
            job.fail(error)

            # Remove from active jobs
            del self.jobs[job_id]

            if not self.jobs:
                self.status = WorkerStatus.IDLE

            self._publish_event(
                JobFailedByWorker(
                    job_id=job_id,
                    worker_id=self.worker_id,
                    error=error
                )
            )

    def update_heartbeat(self) -> None:
        """Update worker heartbeat"""
        self.last_heartbeat = datetime.utcnow()

        if self.status == WorkerStatus.OFFLINE:
            self.status = WorkerStatus.IDLE
            self._publish_event(
                WorkerCameOnline(
                    worker_id=self.worker_id
                )
            )

    def check_timeout(self, timeout_seconds: int = 300) -> bool:
        """Check if worker has timed out"""
        timeout = timedelta(seconds=timeout_seconds)
        if datetime.utcnow() - self.last_heartbeat > timeout:
            if self.status != WorkerStatus.OFFLINE:
                self.status = WorkerStatus.OFFLINE

                self._publish_event(
                    WorkerWentOffline(
                        worker_id=self.worker_id,
                        active_jobs=list(self.jobs.keys())
                    )
                )

            return True

        return False

    def start_draining(self) -> None:
        """Start graceful shutdown (no new jobs)"""
        self.status = WorkerStatus.DRAINING

        self._publish_event(
            WorkerDrainingStarted(
                worker_id=self.worker_id,
                active_jobs=len(self.jobs)
            )
        )

    def _can_accept_job(self, job: Job) -> bool:
        """Check if worker can accept job"""
        if self.status in [WorkerStatus.OFFLINE, WorkerStatus.DRAINING]:
            return False

        if len(self.jobs) >= self.max_concurrent_jobs:
            return False

        if job.type not in self.capabilities.supported_types:
            return False

        return True

    def get_load(self) -> WorkerLoad:
        """Get current worker load"""
        return WorkerLoad(
            active_jobs=len(self.jobs),
            max_jobs=self.max_concurrent_jobs,
            utilization=len(self.jobs) / self.max_concurrent_jobs,
            status=self.status
        )
```

**TypeScript Equivalent:**

```typescript
class WorkerNode extends AggregateRoot {
  private jobs: Map<JobId, WorkerJob> = new Map();
  private status: WorkerStatus = WorkerStatus.Idle;
  private lastHeartbeat: Date = new Date();

  constructor(
    private workerId: WorkerId,
    private capabilities: WorkerCapabilities,
    private maxConcurrentJobs: number = 5
  ) {
    super();
  }

  register(): void {
    this.status = WorkerStatus.Idle;
    this.lastHeartbeat = new Date();

    this.publishEvent(new WorkerRegistered(this.workerId, this.capabilities));
  }

  assignJob(job: Job): boolean {
    if (!this.canAcceptJob(job)) return false;

    const workerJob = new WorkerJob(
      JobId.generate(),
      this.workerId,
      job.id,
      job.type
    );
    this.jobs.set(job.id, workerJob);

    if (this.jobs.size >= this.maxConcurrentJobs) {
      this.status = WorkerStatus.Active;
    }

    this.publishEvent(new JobAssignedToWorker(job.id, this.workerId));

    return true;
  }

  completeJob(jobId: JobId, result: JobResult): void {
    const job = this.jobs.get(jobId);
    if (job) {
      job.complete(result);
      this.jobs.delete(jobId);

      if (this.jobs.size === 0) {
        this.status = WorkerStatus.Idle;
      }

      this.publishEvent(new JobCompletedByWorker(jobId, this.workerId, result));
    }
  }

  failJob(jobId: JobId, error: string): void {
    const job = this.jobs.get(jobId);
    if (job) {
      job.fail(error);
      this.jobs.delete(jobId);

      if (this.jobs.size === 0) {
        this.status = WorkerStatus.Idle;
      }

      this.publishEvent(new JobFailedByWorker(jobId, this.workerId, error));
    }
  }

  updateHeartbeat(): void {
    this.lastHeartbeat = new Date();

    if (this.status === WorkerStatus.Offline) {
      this.status = WorkerStatus.Idle;
      this.publishEvent(new WorkerCameOnline(this.workerId));
    }
  }

  checkTimeout(timeoutSeconds: number = 300): boolean {
    const timeout = timeoutSeconds * 1000;
    const now = Date.now();

    if (now - this.lastHeartbeat.getTime() > timeout) {
      if (this.status !== WorkerStatus.Offline) {
        this.status = WorkerStatus.Offline;

        this.publishEvent(new WorkerWentOffline(
          this.workerId,
          Array.from(this.jobs.keys())
        ));
      }

      return true;
    }

    return false;
  }

  startDraining(): void {
    this.status = WorkerStatus.Draining;

    this.publishEvent(new WorkerDrainingStarted(
      this.workerId,
      this.jobs.size
    ));
  }

  private canAcceptJob(job: Job): boolean {
    if (this.status === WorkerStatus.Offline ||
        this.status === WorkerStatus.Draining) {
      return false;
    }

    if (this.jobs.size >= this.maxConcurrentJobs) {
      return false;
    }

    if (!this.capabilities.supportedTypes.includes(job.type)) {
      return false;
    }

    return true;
  }

  getLoad(): WorkerLoad {
    return {
      activeJobs: this.jobs.size,
      maxJobs: this.maxConcurrentJobs,
      utilization: this.jobs.size / this.maxConcurrentJobs,
      status: this.status
    };
  }
}
```

---

## Aggregate Relationships

```
┌─────────────────────────────────────────────────────────────────┐
│                      Core Domain (Shared Kernel)                 │
│  Transcript | AudioFile | ProcessingJob | Summary | RAGSession  │
└────────────────────────────┬────────────────────────────────────┘
                             │
        ┌────────────────────┼────────────────────┬──────────────┐
        │                    │                    │              │
┌───────▼────────┐  ┌────────▼────────┐  ┌───────▼────────┐  ┌──▼─────────────┐
│ JobQueue       │  │ CacheManager    │  │ ParallelProc.  │  │ ConnectionPool  │
│ Aggregate      │  │ Aggregate       │  │ Aggregate      │  │ Aggregate       │
│                │  │                 │  │                │  │                 │
│ - Job          │  │ - CacheEntry    │  │ - Processing   │  │ - Connection    │
│ - JobAttempt   │  │ - CacheLevel    │  │   Task         │  │ - PoolSize     │
│                │  │                 │  │ - ChunkResult  │  │ - PoolStatus   │
└───────┬────────┘  └────────┬────────┘  └───────┬────────┘  └────────┬────────┘
        │                    │                    │                      │
        │           ┌────────▼───────────────────▼───────────────┐      │
        │           │                                           │      │
        │           │         APIConnection Aggregate            │      │
        │           │         - HTTP2Connection                 │      │
        │           │         - RateLimit                       │      │
        │           │                                           │      │
        │           └───────────────────────────────────────────┘      │
        │                    │                                     │
        └────────────────────┼────────────────────┬────────────────┘
                             │                    │
                             ▼                    ▼
                   ┌─────────────────────┐  ┌─────────────┐
                   │ MetricsCollector    │  │ WorkerNode  │
                   │ Aggregate           │  │ Aggregate   │
                   │                     │  │             │
                   │ - MetricSeries      │  │ - WorkerJob │
                   │ - AlertRule        │  │ - Load      │
                   └─────────────────────┘  └─────────────┘
```

---

## Aggregate Context Mapping

| Aggregate | Context | Primary Storage | Event Publisher |
|-----------|---------|-----------------|-----------------|
| JobQueue | Queue | PostgreSQL + Redis | JobQueued, JobStarted, JobCompleted |
| WorkerNode | Queue | Redis | WorkerRegistered, JobAssignedToWorker |
| CacheManager | Caching | Memory + Redis + PG | CacheEntryCreated, CacheInvalidated |
| ParallelProcessor | Processing | PostgreSQL | ChunkProcessingStarted, FileProcessingCompleted |
| MetricsCollector | Monitoring | Prometheus | MetricRecorded, AlertTriggered |
| ConnectionPool | Database | Connection Pool | PoolInitialized, ConnectionAcquired |
| APIConnection | External | HTTP/2 Pool | APIConnectionCreated, APIRequestCompleted |

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
