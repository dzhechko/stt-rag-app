# Tactical Design - Entities and Value Objects

**Feature:** Performance Optimizations
**Version:** 1.0
**Date:** 2026-02-03

---

## Overview

This document defines the Entities and Value Objects for the Performance Optimization feature.

---

## Entities

### Job

**Identity:** `JobId` (UUID)

**Responsibility:** Represent a unit of work to be executed.

**Attributes:**
```python
@dataclass
class Job:
    """Represents a job in the queue"""
    id: JobId
    type: JobType  # TRANSCRIPTION, SUMMARIZATION, INDEXING, TRANSLATION
    payload: JobPayload  # Encrypted job data
    priority: JobPriority  # HIGH, MEDIUM, LOW
    status: JobStatus  # QUEUED, PROCESSING, COMPLETED, FAILED
    retry_count: int
    max_retries: int
    created_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    error_message: Optional[str]
    worker_id: Optional[str]
    result: Optional[JobResult]

    # Domain methods
    def start_processing(self, worker_id: str) -> None:
        """Transition to PROCESSING state"""
        if self.status != JobStatus.QUEUED:
            raise InvalidStateTransition(
                f"Cannot start job in {self.status} state"
            )
        self.status = JobStatus.PROCESSING
        self.started_at = datetime.utcnow()
        self.worker_id = worker_id

    def complete(self, result: JobResult) -> None:
        """Transition to COMPLETED state"""
        if self.status != JobStatus.PROCESSING:
            raise InvalidStateTransition(
                f"Cannot complete job in {self.status} state"
            )
        self.status = JobStatus.COMPLETED
        self.completed_at = datetime.utcnow()
        self.result = result

    def fail(self, error: str) -> None:
        """Transition to FAILED state"""
        self.status = JobStatus.FAILED
        self.completed_at = datetime.utcnow()
        self.error_message = error

    def can_retry(self) -> bool:
        """Check if job can be retried"""
        return self.retry_count < self.max_retries

    def schedule_retry(self, error: str) -> None:
        """Increment retry count and re-queue"""
        self.retry_count += 1
        self.status = JobStatus.QUEUED
        self.error_message = error
        self.started_at = None
        self.worker_id = None
```

---

### CacheEntry

**Identity:** `CacheKey` (content-addressed hash)

**Responsibility:** Represent a cached computation result.

**Attributes:**
```python
@dataclass
class CacheEntry:
    """Represents a cached value"""
    key: CacheKey
    value: CacheValue
    created_at: datetime
    accessed_at: datetime
    ttl: TTL  # Time to live
    access_count: int
    size_bytes: int

    # Domain methods
    def is_expired(self) -> bool:
        """Check if entry has expired"""
        return datetime.utcnow() > self.created_at + self.ttl

    def touch(self) -> None:
        """Update access time and count"""
        self.accessed_at = datetime.utcnow()
        self.access_count += 1

    def update_value(self, new_value: CacheValue, new_ttl: TTL) -> None:
        """Update cached value"""
        self.value = new_value
        self.ttl = new_ttl
        self.created_at = datetime.utcnow()
```

---

### ProcessingTask

**Identity:** `TaskId` (UUID)

**Responsibility:** Represent a single chunk processing task.

**Attributes:**
```python
@dataclass
class ProcessingTask:
    """Represents a chunk processing task"""
    id: TaskId
    processing_id: ProcessingId
    chunk: AudioChunk
    index: int  # Position in file
    total_chunks: int
    status: TaskStatus  # PENDING, PROCESSING, COMPLETED, FAILED
    retry_count: int
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    result: Optional[ChunkResult]
    error: Optional[str]

    # Domain methods
    def start(self) -> None:
        """Start processing"""
        if self.status != TaskStatus.PENDING:
            raise InvalidStateTransition()
        self.status = TaskStatus.PROCESSING
        self.started_at = datetime.utcnow()

    def complete(self, result: ChunkResult) -> None:
        """Mark as completed"""
        if self.status != TaskStatus.PROCESSING:
            raise InvalidStateTransition()
        self.status = TaskStatus.COMPLETED
        self.completed_at = datetime.utcnow()
        self.result = result

    def fail(self, error: str) -> None:
        """Mark as failed"""
        self.status = TaskStatus.FAILED
        self.completed_at = datetime.utcnow()
        self.error = error

    def get_progress(self) -> float:
        """Calculate progress contribution"""
        base_progress = self.index / self.total_chunks
        if self.status == TaskStatus.COMPLETED:
            return (self.index + 1) / self.total_chunks
        return base_progress
```

---

### MetricSeries

**Identity:** `SeriesId` (UUID)

**Responsibility:** Time-series of metric values.

**Attributes:**
```python
@dataclass
class MetricSeries:
    """Time-series of metric values"""
    id: SeriesId
    name: MetricName
    values: List[TimestampedValue]
    retention_period: timedelta

    # Domain methods
    def add_value(self, value: MetricValue, tags: Dict[str, str]) -> None:
        """Add new value to series"""
        timestamped = TimestampedValue(
            value=value,
            timestamp=datetime.utcnow(),
            tags=tags
        )
        self.values.append(timestamped)

        # Prune old values
        cutoff = datetime.utcnow() - self.retention_period
        self.values = [
            v for v in self.values
            if v.timestamp > cutoff
        ]

    def calculate_percentile(
        self,
        percentile: Percentile,
        window: timedelta
    ) -> float:
        """Calculate percentile over sliding window"""
        cutoff = datetime.utcnow() - window
        window_values = [
            v.value.value
            for v in self.values
            if v.timestamp > cutoff
        ]

        if not window_values:
            return 0.0

        return np.percentile(window_values, percentile.value)

    def get_average(self, window: timedelta) -> float:
        """Calculate average over sliding window"""
        cutoff = datetime.utcnow() - window
        window_values = [
            v.value.value
            for v in self.values
            if v.timestamp > cutoff
        ]

        if not window_values:
            return 0.0

        return sum(window_values) / len(window_values)
```

---

### AlertRule

**Identity:** `AlertRuleId` (UUID)

**Responsibility:** Define alert trigger conditions.

**Attributes:**
```python
@dataclass
class AlertRule:
    """Alert rule definition"""
    id: AlertRuleId
    name: str
    metric_name: MetricName
    threshold: Threshold
    severity: str  # INFO, WARNING, CRITICAL
    comparison: str  # GREATER_THAN, LESS_THAN, EQUAL
    window: timedelta
    enabled: bool
    last_triggered: Optional[datetime]
    notification_channels: List[str]

    # Domain methods
    def is_triggered(self, current_value: float) -> bool:
        """Check if alert should trigger"""
        if not self.enabled:
            return False

        if self.comparison == "GREATER_THAN":
            return current_value > self.threshold.value
        elif self.comparison == "LESS_THAN":
            return current_value < self.threshold.value
        elif self.comparison == "EQUAL":
            return current_value == self.threshold.value

        return False

    def trigger(self) -> None:
        """Mark alert as triggered"""
        self.last_triggered = datetime.utcnow()

    def reset(self) -> None:
        """Reset alert state"""
        self.last_triggered = None
```

---

## Value Objects

### JobId

**Immutable:** Yes

**Equality:** By value (UUID)

**Validation:** Valid UUID format

```python
@dataclass(frozen=True)
class JobId:
    """Job identifier"""
    value: UUID

    @classmethod
    def generate(cls) -> "JobId":
        return cls(value=uuid4())

    @classmethod
    def from_string(cls, s: str) -> "JobId":
        return cls(value=UUID(s))

    def __str__(self) -> str:
        return str(self.value)
```

---

### JobPriority

**Immutable:** Yes

**Equality:** By value

**Values:** HIGH(3), MEDIUM(2), LOW(1)

```python
@dataclass(frozen=True)
class JobPriority:
    """Job priority level"""
    value: int

    HIGH: ClassVar["JobPriority"] = None
    MEDIUM: ClassVar["JobPriority"] = None
    LOW: ClassVar["JobPriority"] = None

    def __post_init__(self):
        if self.value not in [1, 2, 3]:
            raise ValueError("Priority must be 1 (LOW), 2 (MEDIUM), or 3 (HIGH)")

    @classmethod
    def high(cls) -> "JobPriority":
        return cls(value=3)

    @classmethod
    def medium(cls) -> "JobPriority":
        return cls(value=2)

    @classmethod
    def low(cls) -> "JobPriority":
        return cls(value=1)

    def __gt__(self, other: "JobPriority") -> bool:
        return self.value > other.value
```

---

### JobStatus

**Immutable:** Yes

**Equality:** By value

**Values:** QUEUED, PROCESSING, COMPLETED, FAILED

```python
@dataclass(frozen=True)
class JobStatus:
    """Job status"""
    value: str

    QUEUED: ClassVar["JobStatus"] = None
    PROCESSING: ClassVar["JobStatus"] = None
    COMPLETED: ClassVar["JobStatus"] = None
    FAILED: ClassVar["JobStatus"] = None

    def __post_init__(self):
        valid = ["QUEUED", "PROCESSING", "COMPLETED", "FAILED"]
        if self.value not in valid:
            raise ValueError(f"Status must be one of {valid}")

    @classmethod
    def queued(cls) -> "JobStatus":
        return cls(value="QUEUED")

    @classmethod
    def processing(cls) -> "JobStatus":
        return cls(value="PROCESSING")

    @classmethod
    def completed(cls) -> "JobStatus":
        return cls(value="COMPLETED")

    @classmethod
    def failed(cls) -> "JobStatus":
        return cls(value="FAILED")

    def is_terminal(self) -> bool:
        return self.value in ["COMPLETED", "FAILED"]
```

---

### CacheKey

**Immutable:** Yes

**Equality:** By value (content hash)

**Validation:** SHA-256 hash

```python
@dataclass(frozen=True)
class CacheKey:
    """Content-addressed cache key"""
    hash: str  # SHA-256 hex
    prefix: str  # e.g., "transcript", "embeddings"

    def __str__(self) -> str:
        return f"{self.prefix}:{self.hash}"

    @classmethod
    def from_content(
        cls,
        content: bytes,
        prefix: str
    ) -> "CacheKey":
        """Generate key from content"""
        import hashlib
        hash_obj = hashlib.sha256(content)
        return cls(hash=hash_obj.hexdigest(), prefix=prefix)

    @classmethod
    def from_parts(
        cls,
        file_hash: str,
        language: str,
        prefix: str = "transcript"
    ) -> "CacheKey":
        """Generate key from file hash + language"""
        combined = f"{file_hash}:{language}".encode()
        return cls.from_content(combined, prefix)
```

---

### TTL

**Immutable:** Yes

**Equality:** By value (duration)

**Validation:** Positive duration

```python
@dataclass(frozen=True)
class TTL:
    """Time to live duration"""
    value: timedelta

    def __post_init__(self):
        if self.value.total_seconds() <= 0:
            raise ValueError("TTL must be positive")

    @classmethod
    def minutes(cls, minutes: int) -> "TTL":
        return cls(value=timedelta(minutes=minutes))

    @classmethod
    def hours(cls, hours: int) -> "TTL":
        return cls(value=timedelta(hours=hours))

    @classmethod
    def days(cls, days: int) -> "TTL":
        return cls(value=timedelta(days=days))

    def to_seconds(self) -> int:
        return int(self.value.total_seconds())
```

---

### ChunkSize

**Immutable:** Yes

**Equality:** By value (MB)

**Validation:** 10-25 MB range

```python
@dataclass(frozen=True)
class ChunkSize:
    """Optimal chunk size in MB"""
    value_mb: int

    MIN_MB: int = 10
    MAX_MB: int = 25

    def __post_init__(self):
        if not (self.MIN_MB <= self.value_mb <= self.MAX_MB):
            raise ValueError(
                f"Chunk size must be between {self.MIN_MB} and {self.MAX_MB} MB"
            )

    @classmethod
    def from_file_size(cls, file_size_mb: int) -> "ChunkSize":
        """Calculate optimal chunk size from file size"""
        # Larger files get larger chunks
        if file_size_mb < 50:
            return cls(value_mb=15)
        elif file_size_mb < 100:
            return cls(value_mb=20)
        else:
            return cls(value_mb=25)

    def to_bytes(self) -> int:
        return self.value_mb * 1024 * 1024
```

---

### ConcurrencyLimit

**Immutable:** Yes

**Equality:** By value

**Validation:** 1-10 concurrent tasks

```python
@dataclass(frozen=True)
class ConcurrencyLimit:
    """Maximum concurrent processing tasks"""
    value: int

    MIN: int = 1
    MAX: int = 10

    def __post_init__(self):
        if not (self.MIN <= self.value <= self.MAX):
            raise ValueError(
                f"Concurrency must be between {self.MIN} and {self.MAX}"
            )

    @classmethod
    def default(cls) -> "ConcurrencyLimit":
        return cls(value=4)

    @classmethod
    def from_api_limit(cls, api_limit: int) -> "ConcurrencyLimit":
        """Calculate safe concurrency from API rate limit"""
        # Use 50% of API limit as safe concurrency
        safe = max(1, min(api_limit // 2, cls.MAX))
        return cls(value=safe)
```

---

### MetricValue

**Immutable:** Yes

**Equality:** By value

**Types:** Counter, Gauge, Histogram

```python
@dataclass(frozen=True)
class MetricValue:
    """Metric value with type"""
    value: float
    metric_type: str  # counter, gauge, histogram

    @classmethod
    def counter(cls, value: float) -> "MetricValue":
        return cls(value=value, metric_type="counter")

    @classmethod
    def gauge(cls, value: float) -> "MetricValue":
        return cls(value=value, metric_type="gauge")

    @classmethod
    def histogram(cls, value: float) -> "MetricValue":
        return cls(value=value, metric_type="histogram")
```

---

### Percentile

**Immutable:** Yes

**Equality:** By value

**Common:** p50, p95, p99

```python
@dataclass(frozen=True)
class Percentile:
    """Percentile value"""
    value: float

    P50: ClassVar["Percentile"] = None
    P95: ClassVar["Percentile"] = None
    P99: ClassVar["Percentile"] = None

    def __post_init__(self):
        if not (0 <= self.value <= 100):
            raise ValueError("Percentile must be 0-100")

    @classmethod
    def p50(cls) -> "Percentile":
        return cls(value=50.0)

    @classmethod
    def p95(cls) -> "Percentile":
        return cls(value=95.0)

    @classmethod
    def p99(cls) -> "Percentile":
        return cls(value=99.0)

    def __str__(self) -> str:
        return f"p{int(self.value)}"
```

---

### Threshold

**Immutable:** Yes

**Equality:** By value

**Purpose:** Alert trigger threshold

```python
@dataclass(frozen=True)
class Threshold:
    """Alert threshold value"""
    value: float
    comparison: str  # GREATER_THAN, LESS_THAN, EQUAL

    @classmethod
    def greater_than(cls, value: float) -> "Threshold":
        return cls(value=value, comparison="GREATER_THAN")

    @classmethod
    def less_than(cls, value: float) -> "Threshold":
        return cls(value=value, comparison="LESS_THAN")

    @classmethod
    def equal(cls, value: float) -> "Threshold":
        return cls(value=value, comparison="EQUAL")

    def check(self, actual: float) -> bool:
        """Check if threshold is met"""
        if self.comparison == "GREATER_THAN":
            return actual > self.value
        elif self.comparison == "LESS_THAN":
            return actual < self.value
        elif self.comparison == "EQUAL":
            return actual == self.value
        return False
```

---

### RetryConfig

**Immutable:** Yes

**Equality:** By value

**Purpose:** Retry configuration for jobs

```python
@dataclass(frozen=True)
class RetryConfig:
    """Retry configuration"""
    max_retries: int
    backoff_strategy: str  # EXPONENTIAL, LINEAR, FIXED
    base_delay_ms: int
    max_delay_ms: int

    @classmethod
    def exponential(
        cls,
        max_retries: int = 3,
        base_delay_ms: int = 1000
    ) -> "RetryConfig":
        return cls(
            max_retries=max_retries,
            backoff_strategy="EXPONENTIAL",
            base_delay_ms=base_delay_ms,
            max_delay_ms=60000  # 1 minute
        )

    @classmethod
    def fixed(
        cls,
        max_retries: int = 3,
        delay_ms: int = 5000
    ) -> "RetryConfig":
        return cls(
            max_retries=max_retries,
            backoff_strategy="FIXED",
            base_delay_ms=delay_ms,
            max_delay_ms=delay_ms
        )

    def calculate_delay(self, attempt: int) -> int:
        """Calculate delay for retry attempt"""
        if self.backoff_strategy == "EXPONENTIAL":
            delay = self.base_delay_ms * (2 ** attempt)
        elif self.backoff_strategy == "LINEAR":
            delay = self.base_delay_ms * (attempt + 1)
        else:  # FIXED
            delay = self.base_delay_ms

        return min(delay, self.max_delay_ms)
```

---

## Entity Relationships

```
┌─────────────────────────────────────────────────────────────┐
│                        Aggregate Root                       │
└─────────────────────────────────────────────────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        │                   │                   │
┌───────▼────────┐  ┌───────▼────────┐  ┌───────▼────────┐
│  Job           │  │  CacheEntry    │  │  ProcessingTask │
│  (Entity)      │  │  (Entity)      │  │  (Entity)       │
│                │  │                │  │                 │
│ - id: JobId    │  │ - key: CacheKey│  │ - id: TaskId    │
│ - priority:    │  │ - value:       │  │ - chunk:        │
│   JobPriority  │  │   CacheValue   │  │   AudioChunk    │
│ - status:      │  │ - ttl: TTL     │  │ - status:       │
│   JobStatus    │  │                │  │   TaskStatus    │
└───────┬────────┘  └───────┬────────┘  └───────┬────────┘
        │                   │                   │
        │                   │                   │
┌───────▼────────┐  ┌───────▼────────┐  ┌───────▼────────┐
│ Value Objects  │  │ Value Objects  │  │ Value Objects  │
│                │  │                │  │                │
│ - JobPriority  │  │ - CacheKey     │  │ - ChunkSize    │
│ - JobStatus    │  │ - TTL          │  │ - Concurrency  │
│ - RetryConfig  │  │                │  │   Limit        │
└────────────────┘  └────────────────┘  └────────────────┘
```

---

## Design Patterns Used

### 1. Self-Encapsulation

Entity methods enforce business rules:

```python
# Good: Self-encapsulated
job.start_processing(worker_id)

# Bad: Direct state manipulation
job.status = JobStatus.PROCESSING
job.worker_id = worker_id
```

### 2. Immutable Value Objects

All value objects are frozen (immutable):

```python
@dataclass(frozen=True)
class JobPriority:
    value: int
```

### 3. Value Object Equality

Value objects compare by value, not identity:

```python
priority1 = JobPriority.high()
priority2 = JobPriority.high()
assert priority1 == priority2  # True (same value)
```

### 4. Entity Identity

Entities compare by identity, not attributes:

```python
job1 = Job(id=JobId.generate(), ...)
job2 = Job(id=job1.id, ...)
assert job1 == job2  # True (same identity)
```

---

**Document Control**

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-02-03 | Performance Team | Initial entities and VOs |
