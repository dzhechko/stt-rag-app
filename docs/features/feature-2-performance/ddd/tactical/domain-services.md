# Tactical Design - Domain Services

**Feature:** Performance Optimizations
**Version:** 1.0
**Date:** 2026-02-03

---

## Overview

Domain Services are stateless services that encapsulate domain logic that doesn't naturally fit within an Entity or Value Object. Unlike Application Services (which orchestrate use cases), Domain Services contain business rules and calculations.

---

## Domain Service Catalog

| Service | Context | Responsibility | Stateless |
|---------|---------|---------------|------------|
| DynamicChunkSizer | Processing | Calculate optimal chunk sizes | Yes |
| ParallelOrchestrator | Processing | Manage concurrent execution | No |
| TimestampAdjuster | Processing | Align chunk timestamps | Yes |
| ContentAddresser | Caching | Generate cache keys | Yes |
| MultiLevelCache | Caching | Orchestrate cache levels | Yes |
| CacheInvalidator | Caching | Handle cache eviction | Yes |
| CacheWarmer | Caching | Pre-load frequent entries | Yes |
| JobDispatcher | Queue | Route jobs to workers | Yes |
| PriorityManager | Queue | Manage job priorities | Yes |
| RetryHandler | Queue | Exponential backoff logic | Yes |
| MetricsCollector | Monitoring | Gather performance metrics | No |
| Aggregator | Monitoring | Compute percentiles | Yes |
| AlertEvaluator | Monitoring | Check alert conditions | Yes |
| ConnectionPoolManager | Database | Pool lifecycle management | No |
| QueryOptimizer | Database | Analyze query performance | Yes |
| IndexManager | Database | Maintain optimal indexes | Yes |
| ConnectionPoolManager | External | HTTP/2 pool management | No |
| RateLimitHandler | External | API rate limit handling | Yes |

---

## Processing Context Services

### DynamicChunkSizer

**Purpose:** Calculate optimal chunk sizes based on file characteristics and API constraints.

**Interface:**

```python
from typing import List
from dataclasses import dataclass

@dataclass
class ChunkSizeRecommendation:
    """Recommended chunk size with metadata"""
    size_mb: int
    chunk_count: int
    estimated_duration_seconds: int
    reason: str

class DynamicChunkSizer:
    """Calculate optimal chunk sizes for parallel processing"""

    def __init__(
        self,
        max_chunk_mb: int = 25,
        min_chunk_mb: int = 10,
        target_chunk_duration_seconds: int = 300  # 5 minutes
    ):
        self.max_chunk_mb = max_chunk_mb
        self.min_chunk_mb = min_chunk_mb
        self.target_duration = target_chunk_duration_seconds

    def calculate_chunk_size(
        self,
        file: AudioFile,
        concurrency_limit: ConcurrencyLimit
    ) -> ChunkSizeRecommendation:
        """Calculate optimal chunk size for file"""
        file_size_mb = file.size_bytes / (1024 * 1024)

        # Base calculation on file size
        if file_size_mb < 50:
            size_mb = 15
        elif file_size_mb < 100:
            size_mb = 20
        else:
            size_mb = 25

        # Respect API limits
        size_mb = min(size_mb, self.max_chunk_mb)
        size_mb = max(size_mb, self.min_chunk_mb)

        # Calculate chunk count
        chunk_count = math.ceil(file_size_mb / size_mb)

        # Estimate duration (assuming 1 minute per 5MB)
        estimated_duration = (chunk_count / concurrency_limit.value) * 60

        return ChunkSizeRecommendation(
            size_mb=size_mb,
            chunk_count=chunk_count,
            estimated_duration_seconds=int(estimated_duration),
            reason=f"File size: {file_size_mb:.1f}MB, Concurrency: {concurrency_limit.value}"
        )

    def split_into_chunks(
        self,
        file: AudioFile,
        chunk_size: int
    ) -> List[AudioChunk]:
        """Split file into chunks of specified size"""
        chunks = []
        total_bytes = len(file.data)
        chunk_bytes = chunk_size * 1024 * 1024

        for i in range(0, total_bytes, chunk_bytes):
            chunk_data = file.data[i:i + chunk_bytes]
            chunk = AudioChunk(
                index=i // chunk_bytes,
                data=chunk_data,
                start_timestamp=self._calculate_timestamp(file, i),
                duration_seconds=len(chunk_data) / file.byte_rate
            )
            chunks.append(chunk)

        return chunks

    def _calculate_timestamp(
        self,
        file: AudioFile,
        byte_offset: int
    ) -> datetime:
        """Calculate timestamp for byte offset"""
        seconds_offset = byte_offset / file.byte_rate
        return file.start_time + timedelta(seconds=seconds_offset)
```

**TypeScript Equivalent:**

```typescript
interface ChunkSizeRecommendation {
  sizeMb: number;
  chunkCount: number;
  estimatedDurationSeconds: number;
  reason: string;
}

class DynamicChunkSizer {
  constructor(
    private maxChunkMb: number = 25,
    private minChunkMb: number = 10,
    private targetChunkDurationSeconds: number = 300
  ) {}

  calculateChunkSize(
    file: AudioFile,
    concurrencyLimit: ConcurrencyLimit
  ): ChunkSizeRecommendation {
    const fileSizeMb = file.sizeBytes / (1024 * 1024);

    let sizeMb = fileSizeMb < 50 ? 15 :
                 fileSizeMb < 100 ? 20 : 25;

    sizeMb = Math.min(sizeMb, this.maxChunkMb);
    sizeMb = Math.max(sizeMb, this.minChunkMb);

    const chunkCount = Math.ceil(fileSizeMb / sizeMb);
    const estimatedDuration = (chunkCount / concurrencyLimit.value) * 60;

    return {
      sizeMb,
      chunkCount,
      estimatedDurationSeconds: Math.floor(estimatedDuration),
      reason: `File size: ${fileSizeMb.toFixed(1)}MB, Concurrency: ${concurrencyLimit.value}`
    };
  }

  splitIntoChunks(file: AudioFile, chunkSize: number): AudioChunk[] {
    const chunks: AudioChunk[] = [];
    const totalBytes = file.data.length;
    const chunkBytes = chunkSize * 1024 * 1024;

    for (let i = 0; i < totalBytes; i += chunkBytes) {
      const chunkData = file.data.slice(i, i + chunkBytes);
      chunks.push({
        index: Math.floor(i / chunkBytes),
        data: chunkData,
        startTimestamp: this.calculateTimestamp(file, i),
        durationSeconds: chunkData.length / file.byteRate
      });
    }

    return chunks;
  }

  private calculateTimestamp(file: AudioFile, byteOffset: number): Date {
    const secondsOffset = byteOffset / file.byteRate;
    return new Date(file.startTime.getTime() + secondsOffset * 1000);
  }
}
```

---

### ParallelOrchestrator

**Purpose:** Manage concurrent chunk processing with controlled parallelism.

**Interface:**

```python
import asyncio
from typing import Dict, List, Optional

class ParallelOrchestrator:
    """Orchestrate parallel chunk processing with controlled concurrency"""

    def __init__(
        self,
        concurrency_limit: ConcurrencyLimit,
        retry_config: RetryConfig
    ):
        self.concurrency_limit = concurrency_limit
        self.retry_config = retry_config
        self.active_tasks: Dict[TaskId, asyncio.Task] = {}
        self.semaphore = asyncio.Semaphore(concurrency_limit.value)

    async def execute_parallel(
        self,
        tasks: List[ProcessingTask],
        processor: Callable[[ProcessingTask], Awaitable[ChunkResult]]
    ) -> Dict[TaskId, ChunkResult]:
        """Execute tasks with controlled concurrency"""
        async def process_with_limit(task: ProcessingTask):
            async with self.semaphore:
                return await self._execute_with_retry(task, processor)

        # Execute all tasks concurrently (with semaphore limit)
        results = await asyncio.gather(
            *[process_with_limit(task) for task in tasks],
            return_exceptions=True
        )

        # Map results back to task IDs
        result_map = {}
        for task, result in zip(tasks, results):
            if isinstance(result, Exception):
                # Handle failed task
                result_map[task.id] = ChunkResult.error(
                    task.index,
                    str(result)
                )
            else:
                result_map[task.id] = result

        return result_map

    async def _execute_with_retry(
        self,
        task: ProcessingTask,
        processor: Callable[[ProcessingTask], Awaitable[ChunkResult]]
    ) -> ChunkResult:
        """Execute single task with retry logic"""
        for attempt in range(self.retry_config.max_retries):
            try:
                return await processor(task)
            except TransientError as e:
                if attempt < self.retry_config.max_retries - 1:
                    delay = self.retry_config.calculate_delay(attempt)
                    await asyncio.sleep(delay / 1000)
                else:
                    raise
            except PermanentError:
                # No retry for permanent errors
                raise

    def get_progress(self) -> float:
        """Get overall progress (0.0 to 1.0)"""
        if not self.active_tasks:
            return 0.0

        completed = sum(
            1 for task in self.active_tasks.values()
            if task.done()
        )
        return completed / len(self.active_tasks)

    async def cancel_all(self) -> None:
        """Cancel all active tasks"""
        for task in self.active_tasks.values():
            if not task.done():
                task.cancel()
        await asyncio.gather(*self.active_tasks.values(), return_exceptions=True)
        self.active_tasks.clear()
```

**TypeScript Equivalent:**

```typescript
class ParallelOrchestrator {
  private activeTasks: Map<TaskId, Promise<ChunkResult>> = new Map();
  private semaphore: Semaphore;

  constructor(
    private concurrencyLimit: ConcurrencyLimit,
    private retryConfig: RetryConfig
  ) {
    this.semaphore = new Semaphore(concurrencyLimit.value);
  }

  async executeParallel(
    tasks: ProcessingTask[],
    processor: (task: ProcessingTask) => Promise<ChunkResult>
  ): Promise<Map<TaskId, ChunkResult>> {
    const result = new Map<TaskId, ChunkResult>();

    const processWithLimit = async (task: ProcessingTask) => {
      return await this.semaphore.acquire(() =>
        this.executeWithRetry(task, processor)
      );
    };

    const results = await Promise.allSettled(
      tasks.map(processWithLimit)
    );

    tasks.forEach((task, index) => {
      const settled = results[index];
      if (settled.status === 'fulfilled') {
        result.set(task.id, settled.value);
      } else {
        result.set(task.id, ChunkResult.error(task.index, settled.reason));
      }
    });

    return result;
  }

  private async executeWithRetry(
    task: ProcessingTask,
    processor: (task: ProcessingTask) => Promise<ChunkResult>
  ): Promise<ChunkResult> {
    for (let attempt = 0; attempt < this.retryConfig.maxRetries; attempt++) {
      try {
        return await processor(task);
      } catch (error) {
        if (error instanceof TransientError &&
            attempt < this.retryConfig.maxRetries - 1) {
          const delay = this.retryConfig.calculateDelay(attempt);
          await this.sleep(delay);
        } else {
          throw error;
        }
      }
    }
  }

  getProgress(): number {
    if (this.activeTasks.size === 0) return 0;
    let completed = 0;
    for (const task of this.activeTasks.values()) {
      // Check if task promise is settled
    }
    return completed / this.activeTasks.size;
  }

  async cancelAll(): Promise<void> {
    // Cancel all active tasks
    this.activeTasks.clear();
  }

  private sleep(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms));
  }
}
```

---

### ContentAddresser

**Purpose:** Generate content-addressed cache keys.

**Interface:**

```python
import hashlib
from typing import Union

class ContentAddresser:
    """Generate content-addressed cache keys"""

    def __init__(self, hash_algorithm: str = "sha256"):
        self.hash_algorithm = hash_algorithm

    def generate_key(
        self,
        content: Union[bytes, str],
        prefix: str,
        metadata: Dict[str, str] = None
    ) -> CacheKey:
        """Generate cache key from content"""
        if isinstance(content, str):
            content_bytes = content.encode('utf-8')
        else:
            content_bytes = content

        # Add metadata to hash
        if metadata:
            metadata_str = json.dumps(metadata, sort_keys=True)
            content_bytes += metadata_str.encode('utf-8')

        # Calculate hash
        hash_obj = hashlib.new(self.hash_algorithm)
        hash_obj.update(content_bytes)
        content_hash = hash_obj.hexdigest()

        return CacheKey(
            hash=content_hash,
            prefix=prefix
        )

    def generate_transcript_key(
        self,
        file_hash: str,
        language: str,
        model: str
    ) -> CacheKey:
        """Generate key for transcript cache"""
        combined = f"{file_hash}:{language}:{model}"
        return self.generate_key(
            content=combined,
            prefix="transcript"
        )

    def generate_embeddings_key(
        self,
        text: str,
        model: str,
        dimension: int
    ) -> CacheKey:
        """Generate key for embeddings cache"""
        metadata = {"model": model, "dimension": str(dimension)}
        return self.generate_key(
            content=text,
            prefix="embeddings",
            metadata=metadata
        )

    def validate_key(self, key: CacheKey, content: bytes) -> bool:
        """Validate that key matches content"""
        expected_hash = self.generate_key(content, key.prefix).hash
        return key.hash == expected_hash
```

---

## Caching Context Services

### MultiLevelCache

**Purpose:** Orchestrate L1/L2/L3 cache hierarchy.

**Interface:**

```python
from typing import Optional, Tuple
from enum import Enum

class CacheLevel(Enum):
    L1 = "L1"  # In-memory
    L2 = "L2"  # Redis
    L3 = "L3"  # PostgreSQL

class CacheHitResult:
    """Result of cache lookup"""
    def __init__(
        self,
        hit: bool,
        level: Optional[CacheLevel],
        value: Optional[CacheValue] = None
    ):
        self.hit = hit
        self.level = level
        self.value = value

    @classmethod
    def miss(cls) -> "CacheHitResult":
        return cls(hit=False, level=None)

    @classmethod
    def hit_l1(cls, value: CacheValue) -> "CacheHitResult":
        return cls(hit=True, level=CacheLevel.L1, value=value)

    @classmethod
    def hit_l2(cls, value: CacheValue) -> "CacheHitResult":
        return cls(hit=True, level=CacheLevel.L2, value=value)

    @classmethod
    def hit_l3(cls, value: CacheValue) -> "CacheHitResult":
        return cls(hit=True, level=CacheLevel.L3, value=value)

class MultiLevelCache:
    """Orchestrate multi-level cache hierarchy"""

    def __init__(
        self,
        l1_cache: InMemoryCache,
        l2_cache: RedisCache,
        l3_cache: DatabaseCache
    ):
        self.l1 = l1_cache
        self.l2 = l2_cache
        self.l3 = l3_cache

    def get(self, key: CacheKey) -> CacheHitResult:
        """Get from cache (L1 -> L2 -> L3)"""
        # L1 check
        value = self.l1.get(key)
        if value and not value.is_expired():
            return CacheHitResult.hit_l1(value)

        # L2 check
        value = self.l2.get(key)
        if value and not value.is_expired():
            # Promote to L1
            self.l1.put(key, value, ttl=TTL.minutes(5))
            return CacheHitResult.hit_l2(value)

        # L3 check
        value = self.l3.get(key)
        if value and not value.is_expired():
            # Promote to L2, then L1
            self.l2.put(key, value, ttl=TTL.hours(24))
            self.l1.put(key, value, ttl=TTL.minutes(5))
            return CacheHitResult.hit_l3(value)

        return CacheHitResult.miss()

    def put(
        self,
        key: CacheKey,
        value: CacheValue,
        ttl: TTL
    ) -> None:
        """Put in all cache levels with appropriate TTLs"""
        # L1: Short TTL (5 min cap)
        l1_ttl = min(ttl, TTL.minutes(5))
        self.l1.put(key, value, ttl=l1_ttl)

        # L2: Medium TTL (24 hour cap)
        l2_ttl = min(ttl, TTL.hours(24))
        self.l2.put(key, value, ttl=l2_ttl)

        # L3: Full TTL
        self.l3.put(key, value, ttl=ttl)

    def delete(self, key: CacheKey) -> None:
        """Delete from all cache levels"""
        self.l1.delete(key)
        self.l2.delete(key)
        self.l3.delete(key)

    def get_stats(self) -> Dict[str, int]:
        """Get cache statistics"""
        return {
            "l1_size": self.l1.size(),
            "l2_size": self.l2.size(),
            "l3_count": self.l3.count(),
            "l1_memory_bytes": self.l1.memory_usage()
        }
```

**TypeScript Equivalent:**

```typescript
enum CacheLevel {
  L1 = "L1",
  L2 = "L2",
  L3 = "L3"
}

interface CacheHitResult {
  hit: boolean;
  level?: CacheLevel;
  value?: CacheValue;
}

class MultiLevelCache {
  constructor(
    private l1: InMemoryCache,
    private l2: RedisCache,
    private l3: DatabaseCache
  ) {}

  get(key: CacheKey): CacheHitResult {
    // L1 check
    let value = this.l1.get(key);
    if (value && !value.isExpired()) {
      return { hit: true, level: CacheLevel.L1, value };
    }

    // L2 check
    value = this.l2.get(key);
    if (value && !value.isExpired()) {
      this.l1.put(key, value, TTL.minutes(5));
      return { hit: true, level: CacheLevel.L2, value };
    }

    // L3 check
    value = this.l3.get(key);
    if (value && !value.isExpired()) {
      this.l2.put(key, value, TTL.hours(24));
      this.l1.put(key, value, TTL.minutes(5));
      return { hit: true, level: CacheLevel.L3, value };
    }

    return { hit: false };
  }

  put(key: CacheKey, value: CacheValue, ttl: TTL): void {
    const l1Ttl = ttl.min(TTL.minutes(5));
    const l2Ttl = ttl.min(TTL.hours(24));

    this.l1.put(key, value, l1Ttl);
    this.l2.put(key, value, l2Ttl);
    this.l3.put(key, value, ttl);
  }

  delete(key: CacheKey): void {
    this.l1.delete(key);
    this.l2.delete(key);
    this.l3.delete(key);
  }

  getStats(): CacheStats {
    return {
      l1Size: this.l1.size(),
      l2Size: this.l2.size(),
      l3Count: this.l3.count(),
      l1MemoryBytes: this.l1.memoryUsage()
    };
  }
}
```

---

### CacheInvalidator

**Purpose:** Handle cache eviction and invalidation.

**Interface:**

```python
from typing import List, Pattern
import fnmatch

class CacheInvalidator:
    """Handle cache invalidation strategies"""

    def __init__(self, cache: MultiLevelCache):
        self.cache = cache

    def invalidate_key(self, key: CacheKey) -> None:
        """Invalidate specific key"""
        self.cache.delete(key)

    def invalidate_pattern(self, pattern: str) -> None:
        """Invalidate all keys matching pattern"""
        # L1
        l1_keys = self.cache.l1.keys()
        for key in l1_keys:
            if fnmatch.fnmatch(key, pattern):
                self.cache.l1.delete(key)

        # L2
        for key in self.cache.l2.scan_iter(match=pattern):
            self.cache.l2.delete(key)

        # L3
        self.cache.l3.delete_pattern(pattern)

    def invalidate_transcript(
        self,
        transcript_id: UUID
    ) -> None:
        """Invalidate all cache entries for transcript"""
        pattern = f"*:{transcript_id}:*"
        self.invalidate_pattern(pattern)

    def invalidate_user_data(self, user_id: UUID) -> None:
        """Invalidate all user-specific cache entries"""
        patterns = [
            f"transcript:{user_id}:*",
            f"embeddings:{user_id}:*",
            f"summary:{user_id}:*"
        ]
        for pattern in patterns:
            self.invalidate_pattern(pattern)

    def invalidate_expired(self) -> int:
        """Remove all expired entries from all levels"""
        total_removed = 0

        # L1
        total_removed += self.cache.l1.remove_expired()

        # L2
        total_removed += self.cache.l2.remove_expired()

        # L3
        total_removed += self.cache.l3.remove_expired()

        return total_removed

    def invalidate_l1_on_memory_pressure(self) -> int:
        """Evict L1 entries when memory is high"""
        target_size = 100  # Max L1 entries
        current_size = self.cache.l1.size()

        if current_size <= target_size:
            return 0

        # Remove least recently used entries
        excess = current_size - target_size
        return self.cache.l1.remove_lru(excess)
```

---

## Queue Context Services

### JobDispatcher

**Purpose:** Route jobs to appropriate workers.

**Interface:**

```python
from typing import Callable, Dict
from enum import Enum

class WorkerType(Enum):
    TRANSCRIPTION = "transcription"
    SUMMARIZATION = "summarization"
    INDEXING = "indexing"
    TRANSLATION = "translation"

class JobDispatcher:
    """Route jobs to appropriate worker queues"""

    def __init__(self, queue_repository: JobQueueRepository):
        self.queue_repo = queue_repository
        self.worker_capabilities: Dict[str, List[WorkerType]] = {}

    def register_worker(
        self,
        worker_id: str,
        capabilities: List[WorkerType]
    ) -> None:
        """Register worker capabilities"""
        self.worker_capabilities[worker_id] = capabilities

    def dispatch_job(self, job: Job) -> Optional[str]:
        """Dispatch job to appropriate worker"""
        # Find workers that can handle this job type
        worker_type = self._get_worker_type(job.type)
        capable_workers = [
            worker_id
            for worker_id, capabilities in self.worker_capabilities.items()
            if worker_type in capabilities
        ]

        if not capable_workers:
            return None

        # Select worker with least jobs
        selected_worker = self._select_least_loaded_worker(capable_workers)

        # Assign job to worker
        job.start_processing(selected_worker)

        return selected_worker

    def dispatch_batch(
        self,
        jobs: List[Job],
        max_per_worker: int = 5
    ) -> Dict[str, List[Job]]:
        """Dispatch multiple jobs across workers"""
        worker_jobs: Dict[str, List[Job]] = {}

        for job in jobs:
            worker_id = self.dispatch_job(job)
            if worker_id:
                worker_jobs.setdefault(worker_id, []).append(job)

                # Check worker limit
                if len(worker_jobs[worker_id]) >= max_per_worker:
                    del self.worker_capabilities[worker_id]

        return worker_jobs

    def _get_worker_type(self, job_type: JobType) -> WorkerType:
        """Map job type to worker type"""
        mapping = {
            JobType.TRANSCRIPTION: WorkerType.TRANSCRIPTION,
            JobType.SUMMARIZATION: WorkerType.SUMMARIZATION,
            JobType.INDEXING: WorkerType.INDEXING,
            JobType.TRANSLATION: WorkerType.TRANSLATION
        }
        return mapping[job_type]

    def _select_least_loaded_worker(
        self,
        worker_ids: List[str]
    ) -> str:
        """Select worker with fewest active jobs"""
        min_jobs = float('inf')
        selected = worker_ids[0]

        for worker_id in worker_ids:
            active_jobs = self.queue_repo.get_active_job_count(worker_id)
            if active_jobs < min_jobs:
                min_jobs = active_jobs
                selected = worker_id

        return selected
```

**TypeScript Equivalent:**

```typescript
enum WorkerType {
  Transcription = "transcription",
  Summarization = "summarization",
  Indexing = "indexing",
  Translation = "translation"
}

class JobDispatcher {
  private workerCapabilities: Map<string, WorkerType[]> = new Map();

  constructor(private queueRepo: JobQueueRepository) {}

  registerWorker(workerId: string, capabilities: WorkerType[]): void {
    this.workerCapabilities.set(workerId, capabilities);
  }

  dispatchJob(job: Job): string | null {
    const workerType = this.getWorkerType(job.type);
    const capableWorkers: string[] = [];

    for (const [workerId, capabilities] of this.workerCapabilities) {
      if (capabilities.includes(workerType)) {
        capableWorkers.push(workerId);
      }
    }

    if (capableWorkers.length === 0) return null;

    const selectedWorker = this.selectLeastLoadedWorker(capableWorkers);
    job.startProcessing(selectedWorker);

    return selectedWorker;
  }

  dispatchBatch(jobs: Job[], maxPerWorker: number = 5): Map<string, Job[]> {
    const workerJobs = new Map<string, Job[]>();

    for (const job of jobs) {
      const workerId = this.dispatchJob(job);
      if (workerId) {
        if (!workerJobs.has(workerId)) {
          workerJobs.set(workerId, []);
        }
        workerJobs.get(workerId)!.push(job);

        if (workerJobs.get(workerId)!.length >= maxPerWorker) {
          this.workerCapabilities.delete(workerId);
        }
      }
    }

    return workerJobs;
  }

  private getWorkerType(jobType: JobType): WorkerType {
    const mapping = {
      [JobType.Transcription]: WorkerType.Transcription,
      [JobType.Summarization]: WorkerType.Summarization,
      [JobType.Indexing]: WorkerType.Indexing,
      [JobType.Translation]: WorkerType.Translation
    };
    return mapping[jobType];
  }

  private selectLeastLoadedWorker(workerIds: string[]): string {
    let minJobs = Infinity;
    let selected = workerIds[0];

    for (const workerId of workerIds) {
      const activeJobs = this.queueRepo.getActiveJobCount(workerId);
      if (activeJobs < minJobs) {
        minJobs = activeJobs;
        selected = workerId;
      }
    }

    return selected;
  }
}
```

---

## Database Context Services

### ConnectionPoolManager

**Purpose:** Manage database connection pool lifecycle.

**Interface:**

```python
from sqlalchemy.pool import Pool, QueuePool
from typing import Optional

class PoolStats:
    """Connection pool statistics"""
    def __init__(
        self,
        size: int,
        checked_out: int,
        overflow: int,
        checked_in: int
    ):
        self.size = size
        self.checked_out = checked_out
        self.overflow = overflow
        self.checked_in = checked_in

    @property
    def utilization(self) -> float:
        """Pool utilization (0.0 to 1.0)"""
        return self.checked_out / self.size if self.size > 0 else 0

class ConnectionPoolManager:
    """Manage database connection pool lifecycle"""

    def __init__(
        self,
        pool: QueuePool,
        min_size: int = 5,
        max_size: int = 20
    ):
        self.pool = pool
        self.min_size = min_size
        self.max_size = max_size

    def get_stats(self) -> PoolStats:
        """Get current pool statistics"""
        return PoolStats(
            size=self.pool.size(),
            checked_out=self.pool.checkedout(),
            overflow=self.pool.overflow(),
            checked_in=self.pool.checkedin()
        )

    def ensure_min_connections(self) -> None:
        """Ensure minimum number of connections"""
        current_size = self.pool.size()
        needed = self.min_size - current_size

        if needed > 0:
            for _ in range(needed):
                self.pool.connect()

    def scale_to(self, target_size: int) -> None:
        """Scale pool to target size (within limits)"""
        target_size = max(self.min_size, min(target_size, self.max_size))
        current_size = self.pool.size()

        if target_size > current_size:
            # Add connections
            for _ in range(target_size - current_size):
                self.pool.connect()
        elif target_size < current_size:
            # Connections will be pruned naturally
            pass

    def scale_by_utilization(
        self,
        target_utilization: float = 0.7
    ) -> None:
        """Scale pool based on current utilization"""
        stats = self.get_stats()

        if stats.utilization > target_utilization:
            # Scale up
            new_size = min(
                self.max_size,
                int(stats.size * 1.5)
            )
            self.scale_to(new_size)
        elif stats.utilization < target_utilization / 2:
            # Scale down
            new_size = max(
                self.min_size,
                int(stats.size * 0.8)
            )
            self.scale_to(new_size)

    def close_all(self) -> None:
        """Close all connections in pool"""
        self.pool.close()
        self.pool.dispose()
```

**TypeScript Equivalent:**

```typescript
interface PoolStats {
  size: number;
  checkedOut: number;
  overflow: number;
  checkedIn: number;
  utilization: number;
}

class ConnectionPoolManager {
  constructor(
    private pool: any,
    private minSize: number = 5,
    private maxSize: number = 20
  ) {}

  getStats(): PoolStats {
    const stats = {
      size: this.pool.size(),
      checkedOut: this.pool.checkedout(),
      overflow: this.pool.overflow(),
      checkedIn: this.pool.checkedin()
    };
    return {
      ...stats,
      utilization: stats.size > 0 ? stats.checkedOut / stats.size : 0
    };
  }

  ensureMinConnections(): void {
    const currentSize = this.pool.size();
    const needed = this.minSize - currentSize;

    for (let i = 0; i < needed; i++) {
      this.pool.connect();
    }
  }

  scaleTo(targetSize: number): void {
    const clampedSize = Math.max(
      this.minSize,
      Math.min(targetSize, this.maxSize)
    );
    const currentSize = this.pool.size();

    if (clampedSize > currentSize) {
      for (let i = 0; i < clampedSize - currentSize; i++) {
        this.pool.connect();
      }
    }
  }

  scaleByUtilization(targetUtilization: number = 0.7): void {
    const stats = this.getStats();

    if (stats.utilization > targetUtilization) {
      const newSize = Math.min(this.maxSize, Math.floor(stats.size * 1.5));
      this.scaleTo(newSize);
    } else if (stats.utilization < targetUtilization / 2) {
      const newSize = Math.max(this.minSize, Math.floor(stats.size * 0.8));
      this.scaleTo(newSize);
    }
  }

  closeAll(): void {
    this.pool.close();
    this.pool.dispose();
  }
}
```

---

## Service Composition Patterns

### 1. Stateless Service Composition

Stateless services can be freely composed:

```python
class TranscriptCacheService:
    """Compose caching services for transcript caching"""

    def __init__(
        self,
        addresser: ContentAddresser,
        cache: MultiLevelCache,
        invalidator: CacheInvalidator
    ):
        self.addresser = addresser
        self.cache = cache
        self.invalidator = invalidator

    def get_transcript(
        self,
        file_hash: str,
        language: str
    ) -> Optional[Transcript]:
        key = self.addresser.generate_transcript_key(file_hash, language)
        result = self.cache.get(key)
        return result.value if result.hit else None

    def cache_transcript(
        self,
        file_hash: str,
        language: str,
        transcript: Transcript
    ) -> None:
        key = self.addresser.generate_transcript_key(file_hash, language)
        value = CacheValue.from_transcript(transcript)
        self.cache.put(key, value, ttl=TTL.days(7))
```

### 2. Stateful Service Pattern

Stateful services manage their own state:

```python
class ParallelProcessingService:
    """Stateful service managing active processing"""

    def __init__(
        self,
        orchestrator: ParallelOrchestrator,
        chunk_sizer: DynamicChunkSizer
    ):
        self.orchestrator = orchestrator
        self.chunk_sizer = chunk_sizer
        self.active_processings: Dict[ProcessingId, ParallelProcessor] = {}

    async def process_file(self, file: AudioFile) -> ProcessingId:
        recommendation = self.chunk_sizer.calculate_chunk_size(
            file,
            ConcurrencyLimit.default()
        )

        processor = ParallelProcessor(
            concurrency_limit=ConcurrencyLimit.default()
        )

        processing_id = processor.process_file(
            file,
            ProcessingStrategy.parallel()
        )

        self.active_processings[processing_id] = processor

        return processing_id

    def get_progress(self, processing_id: ProcessingId) -> float:
        processor = self.active_processings.get(processing_id)
        return processor.get_progress() if processor else 0.0
```

---

**Document Control**

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-02-03 | Performance Team | Initial domain services |
