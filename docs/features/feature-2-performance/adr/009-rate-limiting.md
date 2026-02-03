# ADR-009: Rate Limiting and API Throttling

**Status:** Accepted
**Date:** 2026-02-03
**Context:** Performance Optimization Feature

---

## Context

ADR-003 (Parallel Chunk Processing) increases the API call rate from **1 request/15s to 4 requests/15s** (4x increase) when processing multi-chunk files. This introduces several risks:

1. **API Rate Limits:** Cloud.ru API may have undisclosed rate limits
2. **Resource Exhaustion:** Parallel processing could overwhelm downstream services
3. **Cost Overrun:** Exceeded rate limits may incur premium pricing
4. **Queue Backlog:** Failed requests could accumulate in Celery queues
5. **Thundering Herd:** Multiple concurrent files could spike API calls

### Current Behavior

```
Sequential Processing (Before):
Chunk 1 (15s) → Chunk 2 (15s) → Chunk 3 (15s) → Chunk 4 (15s)
API Calls: 1 per 15 seconds
Rate: 4 requests/minute

Parallel Processing (After):
Chunk 1 (15s) ─┐
Chunk 2 (15s) ─┼─→ 4 concurrent requests
Chunk 3 (15s) ─┤
Chunk 4 (15s) ─┘
API Calls: 4 per ~15 seconds
Rate: 16 requests/minute (4x increase)
```

### Risks

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| API rate limit exceeded | Failed jobs, user impact | Medium | Rate limiting |
| Queue overflow | Delayed processing, memory issues | Low | Queue monitoring |
| Cost overrun | Unexpected billing | Low | Usage caps |
| Downstream overload | Slow responses, timeouts | Low | Connection pooling |

---

## Decision

Implement a **token bucket rate limiter** with per-IP throttling, global API limits, and queue prioritization.

### Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Rate Limiter                             │
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │ Per-IP Limit │  │ Global Limit │  │ Queue Limit  │         │
│  │ 10 req/min   │  │ 100 req/min  │  │ 50 pending   │         │
│  └──────────────┘  └──────────────┘  └──────────────┘         │
│         │                  │                  │                 │
│         └──────────────────┼──────────────────┘                 │
│                            ▼                                    │
│              ┌─────────────────────────┐                        │
│              │   Token Bucket Engine   │                        │
│              │  - Refill rate: 10/min  │                        │
│              │  - Burst: 5 tokens      │                        │
│              │  - Storage: Redis       │                        │
│              └─────────────────────────┘                        │
└────────────────────────────┬───────────────────────────────────┘
                             │
                             ▼
        ┌───────────────────────────────────────────────┐
        │           Request Handling                    │
        │                                               │
        │  ┌──────────┐    ┌──────────┐    ┌────────┐ │
        │  │ Allow    │    │ Queue    │    │ Reject │ │
        │  │ (token)  │    │ (wait)   │    │ (429)   │ │
        │  └──────────┘    └──────────┘    └────────┘ │
        └───────────────────────────────────────────────┘
```

---

## Implementation

### Token Bucket Algorithm

```python
# backend/app/rate_limiter.py
from dataclasses import dataclass
from typing import Optional
import time
import redis
from app.config import settings

@dataclass
class RateLimitConfig:
    """Rate limit configuration"""
    tokens_per_minute: int
    burst_size: int
    key_prefix: str

class TokenBucketRateLimiter:
    """Token bucket rate limiter using Redis"""

    def __init__(
        self,
        redis_client: redis.Redis,
        config: RateLimitConfig
    ):
        self.redis = redis_client
        self.config = config

    def acquire(
        self,
        identifier: str,
        tokens: int = 1,
        wait: bool = True,
        timeout: float = 60.0
    ) -> bool:
        """
        Acquire tokens from the bucket.

        Args:
            identifier: Unique key (IP, user_id, etc.)
            tokens: Number of tokens to acquire
            wait: If True, wait for tokens; if False, return immediately
            timeout: Max wait time in seconds (only if wait=True)

        Returns:
            True if tokens acquired, False otherwise
        """
        key = f"{self.config.key_prefix}:{identifier}"

        start_time = time.time()

        while True:
            # Try to acquire tokens atomically
            acquired = self._try_acquire(key, tokens)

            if acquired:
                return True

            if not wait:
                return False

            # Calculate wait time
            wait_time = self._calculate_wait_time(key, tokens)

            if time.time() - start_time + wait_time > timeout:
                return False

            # Wait before retry
            time.sleep(min(wait_time, 1.0))

    def _try_acquire(self, key: str, tokens: int) -> bool:
        """Try to acquire tokens using Redis Lua script"""
        lua_script = """
        local key = KEYS[1]
        local tokens = tonumber(ARGV[1])
        local now = tonumber(ARGV[2])
        local interval = 60  -- 1 minute
        local rate = tonumber(ARGV[3])
        local burst = tonumber(ARGV[4])

        -- Get current bucket state
        local bucket = redis.call('HMGET', key, 'tokens', 'last_refill')
        local current_tokens = tonumber(bucket[1]) or burst
        local last_refill = tonumber(bucket[2]) or now

        -- Calculate tokens to add based on time elapsed
        local elapsed = now - last_refill
        local tokens_to_add = math.floor(elapsed * rate / interval)

        -- Refill tokens (up to burst size)
        current_tokens = math.min(burst, current_tokens + tokens_to_add)

        -- Check if enough tokens available
        if current_tokens >= tokens then
            -- Consume tokens
            current_tokens = current_tokens - tokens
            redis.call('HMSET', key, 'tokens', current_tokens, 'last_refill', now)
            redis.call('EXPIRE', key, interval * 2)
            return 1
        else
            -- Update state anyway (tokens added but not enough)
            redis.call('HMSET', key, 'tokens', current_tokens, 'last_refill', now)
            redis.call('EXPIRE', key, interval * 2)
            return 0
        end
        """

        result = self.redis.eval(
            lua_script,
            1,
            key,
            tokens,
            time.time(),
            self.config.tokens_per_minute,
            self.config.burst_size
        )

        return bool(result)

    def _calculate_wait_time(self, key: str, tokens: int) -> float:
        """Calculate time needed to acquire tokens"""
        bucket = self.redis.hmget(key, 'tokens', 'last_refill')
        current_tokens = float(bucket[0] or self.config.burst_size)
        last_refill = float(bucket[1] or time.time())

        # Calculate refill rate
        tokens_per_second = self.config.tokens_per_minute / 60.0

        # Calculate needed tokens
        needed = tokens - current_tokens

        if needed <= 0:
            return 0.0

        return needed / tokens_per_second

    def get_status(self, identifier: str) -> dict:
        """Get current rate limit status"""
        key = f"{self.config.key_prefix}:{identifier}"
        bucket = self.redis.hmget(key, 'tokens', 'last_refill')

        current_tokens = float(bucket[0] or self.config.burst_size)
        last_refill = float(bucket[1] or time.time())

        return {
            "tokens_available": current_tokens,
            "tokens_per_minute": self.config.tokens_per_minute,
            "burst_size": self.config.burst_size,
            "last_refill": last_refill
        }
```

### Rate Limit Configurations

```python
# backend/app/config.py
from dataclasses import dataclass
from app.rate_limiter import RateLimitConfig

@dataclass
class RateLimitingConfig:
    # Per-IP limits (prevent abuse)
    ip_limit: RateLimitConfig = RateLimitConfig(
        tokens_per_minute=10,
        burst_size=5,
        key_prefix="ratelimit:ip"
    )

    # Global API limits (protect Cloud.ru)
    api_limit: RateLimitConfig = RateLimitConfig(
        tokens_per_minute=100,
        burst_size=20,
        key_prefix="ratelimit:api"
    )

    # User-based limits (fair usage)
    user_limit: RateLimitConfig = RateLimitConfig(
        tokens_per_minute=20,
        burst_size=10,
        key_prefix="ratelimit:user"
    )

    # Celery task limits (queue management)
    task_limit: RateLimitConfig = RateLimitConfig(
        tokens_per_minute=50,
        burst_size=15,
        key_prefix="ratelimit:task"
    )
```

### FastAPI Integration

```python
# backend/app/main.py
from fastapi import Request, HTTPException
from app.rate_limiter import TokenBucketRateLimiter
from app.config import settings

# Initialize rate limiters
ip_rate_limiter = TokenBucketRateLimiter(
    redis_client=settings.redis_client,
    config=settings.rate_limit_config.ip_limit
)

api_rate_limiter = TokenBucketRateLimiter(
    redis_client=settings.redis_client,
    config=settings.rate_limit_config.api_limit
)

@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    """Rate limit middleware for API endpoints"""

    # Skip rate limiting for health checks
    if request.url.path.startswith("/health"):
        return await call_next(request)

    # Get client IP
    client_ip = request.client.host

    # Check IP-based rate limit
    if not ip_rate_limiter.acquire(
        identifier=client_ip,
        tokens=1,
        wait=False
    ):
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded. Please try again later.",
            headers={
                "X-RateLimit-Limit": str(settings.rate_limit_config.ip_limit.tokens_per_minute),
                "X-RateLimit-Remaining": "0",
                "X-RateLimit-Reset": str(int(time.time() + 60))
            }
        )

    # Check global API rate limit
    if not api_rate_limiter.acquire(
        identifier="global",
        tokens=1,
        wait=False
    ):
        raise HTTPException(
            status_code=429,
            detail="API rate limit exceeded. Please try again later."
        )

    # Add rate limit headers
    response = await call_next(request)

    ip_status = ip_rate_limiter.get_status(client_ip)
    response.headers["X-RateLimit-Limit"] = str(settings.rate_limit_config.ip_limit.tokens_per_minute)
    response.headers["X-RateLimit-Remaining"] = str(int(ip_status["tokens_available"]))
    response.headers["X-RateLimit-Reset"] = str(int(ip_status["last_refill"] + 60))

    return response
```

### Celery Task Rate Limiting

```python
# backend/app/tasks.py
from celery import shared_task
from app.rate_limiter import TokenBucketRateLimiter

# Task rate limiter
task_rate_limiter = TokenBucketRateLimiter(
    redis_client=settings.redis_client,
    config=settings.rate_limit_config.task_limit
)

@shared_task(bind=True, max_retries=3)
def transcribe_chunk_with_rate_limit(
    self,
    chunk_id: str,
    file_path: str,
    language: str = None
):
    """Transcribe chunk with rate limiting"""

    # Acquire rate limit token
    if not task_rate_limiter.acquire(
        identifier="transcribe",
        tokens=1,
        wait=True,
        timeout=300  # Wait up to 5 minutes
    ):
        # Rate limit exceeded, requeue with backoff
        raise self.retry(countdown=60)

    try:
        # Proceed with transcription
        service = TranscriptionService()
        result = service.transcribe_file(file_path, language)
        return result

    except Exception as exc:
        logger.error(f"Chunk transcription failed: {exc}")
        raise self.retry(exc=exc, countdown=2 ** self.request.retries)
```

### Queue Management

```python
# backend/app/queue_manager.py
from celery import current_app
from app.rate_limiter import TokenBucketRateLimiter

class QueueManager:
    """Manage Celery queues based on rate limits"""

    def __init__(self, rate_limiter: TokenBucketRateLimiter):
        self.rate_limiter = rate_limiter

    def can_submit_task(self, queue_name: str) -> bool:
        """Check if task can be submitted to queue"""
        # Get current queue depth
        inspect = current_app.control.inspect()
        active_queues = inspect.active_queues()

        queue_depth = 0
        for worker, queues in (active_queues or {}).items():
            for queue in queues:
                if queue["name"] == queue_name:
                    queue_depth += queue.get("pending", 0)

        # Check if queue depth exceeds threshold
        if queue_depth > 50:
            logger.warning(f"Queue {queue_name} depth high: {queue_depth}")
            return False

        # Check rate limit
        return self.rate_limiter.acquire(
            identifier=queue_name,
            tokens=1,
            wait=False
        )

    def get_queue_status(self) -> dict:
        """Get status of all queues"""
        inspect = current_app.control.inspect()

        return {
            "active_queues": inspect.active_queues(),
            "scheduled": inspect.scheduled(),
            "active": inspect.active(),
            "reserved": inspect.reserved()
        }
```

---

## Rate Limit Strategies

### 1. Per-IP Rate Limiting

**Purpose:** Prevent abuse from single source

**Configuration:**
- Rate: 10 requests/minute
- Burst: 5 requests
- Storage: Redis (key: `ratelimit:ip:{ip_address}`)

**Use Cases:**
- Upload endpoint
- Transcription requests
- API calls from frontend

### 2. Global API Rate Limiting

**Purpose:** Protect Cloud.ru API from overload

**Configuration:**
- Rate: 100 requests/minute
- Burst: 20 requests
- Storage: Redis (key: `ratelimit:api:global`)

**Use Cases:**
- All transcription API calls
- Parallel chunk processing
- Celery tasks

### 3. User-Based Rate Limiting

**Purpose:** Fair usage per authenticated user

**Configuration:**
- Rate: 20 requests/minute
- Burst: 10 requests
- Storage: Redis (key: `ratelimit:user:{user_id}`)

**Use Cases:**
- Authenticated API calls
- Resource-intensive operations

---

## Alternatives Considered

### 1. Fixed Window Counter

**Pros:** Simple implementation
**Cons:** Burst at window boundaries, unfair
**Decision:** Token bucket provides smoother rate limiting

### 2. Sliding Window Log

**Pros:** Accurate rate limiting
**Cons:** High memory usage, O(n) complexity
**Decision:** Token bucket is more efficient

### 3. Leaky Bucket

**Pros:** Smooth output rate
**Cons:** Hard to implement, burst handling
**Decision:** Token bucket is simpler and effective

### 4. No Rate Limiting

**Pros:** No complexity
**Cons:** Risk of API abuse, cost overrun
**Decision:** Risk too high without rate limiting

---

## Configuration Options

```python
# backend/app/config.py
class RateLimitingConfig:
    # Per-IP limits
    IP_REQUESTS_PER_MINUTE: int = 10
    IP_BURST_SIZE: int = 5

    # Global API limits
    API_REQUESTS_PER_MINUTE: int = 100
    API_BURST_SIZE: int = 20

    # User limits
    USER_REQUESTS_PER_MINUTE: int = 20
    USER_BURST_SIZE: int = 10

    # Queue limits
    QUEUE_MAX_DEPTH: int = 50
    QUEUE_RETRY_DELAY_SECONDS: int = 60

    # Backoff
    RATE_LIMIT_RETRY_MAX_ATTEMPTS: int = 3
    RATE_LIMIT_RETRY_BACKOFF_MULTIPLIER: float = 2.0
```

---

## Monitoring

### Metrics

```python
# Prometheus metrics
rate_limit_hits_total = Counter(
    'rate_limit_hits_total',
    'Rate limit hits',
    ['type', 'identifier']
)

rate_limit_waits_total = Counter(
    'rate_limit_waits_total',
    'Rate limit waits (queued requests)',
    ['type']
)

rate_limit_wait_duration_seconds = Histogram(
    'rate_limit_wait_duration_seconds',
    'Time spent waiting for rate limit',
    ['type'],
    buckets=[0.1, 0.5, 1, 5, 10, 30, 60]
)
```

### Dashboards

**Grafana Panels:**
1. Rate limit hits by type
2. Average wait time
3. Queue depth over time
4. Tokens available per bucket

---

## Consequences

### Positive

1. **Protection:** Prevents API abuse and cost overrun
2. **Stability:** Smooths out request spikes
3. **Fairness:** Ensures equitable resource allocation
4. **Control:** Predictable API usage patterns

### Negative

1. **Complexity:** Additional infrastructure logic
2. **Latency:** Queued requests add delay
3. **Tuning:** Requires ongoing threshold adjustments
4. **Eviction:** Redis failures require fallback

### Mitigations

- Start with conservative limits
- Monitor and adjust based on usage
- Provide clear error messages
- Use feature flags for disabling
- Graceful degradation on Redis failures

---

**Document Control**

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-02-03 | Performance Team | Initial ADR |
