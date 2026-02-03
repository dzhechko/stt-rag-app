# ADR-010: Redis Failure Handling and High Availability

**Status:** Accepted
**Date:** 2026-02-03
**Context:** Performance Optimization Feature

---

## Context

Redis is a critical dependency for the STT application after implementing ADR-001 (Celery) and ADR-002 (Caching):

1. **Celery Broker:** All async jobs flow through Redis
2. **Cache Storage:** Primary cache for transcriptions, embeddings, summaries
3. **Rate Limiting:** Token bucket state stored in Redis
4. **Session Storage:** User sessions (if implemented)

**Current Risk:** Redis is a **single point of failure**. If Redis fails:

| Component | Impact Without Redis |
|-----------|---------------------|
| Celery Workers | No jobs processed, queue unavailable |
| Transcription Cache | Cache misses, full API re-transcription |
| Rate Limiting | No protection, API abuse risk |
| Background Tasks | Jobs lost or stuck |

### Failure Scenarios

1. **Redis Outage:** Network issues, process crash, OOM
2. **Redis Maintenance:** Upgrades, configuration changes
3. **Redis Eviction:** Memory full, cache keys evicted
4. **Network Partition:** Backend can't reach Redis

### Impact Assessment

| Severity | Scenario | Duration Impact | Data Loss Risk |
|----------|----------|-----------------|----------------|
| Critical | Redis crash | Until restart | High (pending jobs) |
| High | Network partition | Until resolved | Medium (in-flight jobs) |
| Medium | Redis maintenance | Scheduled window | Low (planned) |
| Low | Redis eviction | None (cache miss) | None |

---

## Decision

Implement **Redis Sentinel** for high availability with **graceful degradation** to PostgreSQL when Redis is unavailable.

### Architecture

```
Normal Operation (Redis Available):
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Master    │ ←→ │   Sentinel  │ ←→ │   Sentinel  │
│  (Redis)    │     │   (Monitor) │     │   (Monitor) │
└──────┬──────┘     └─────────────┘     └─────────────┘
       │                                    │
       │ Failover                           │
       ▼                                    │
┌─────────────┐                             │
│   Replica   │ ←───────────────────────────┘
│  (Redis)    │      (Auto-promotion)
└─────────────┘

Degraded Operation (Redis Unavailable):
┌─────────────────────────────────────────────────────────┐
│                    Application Layer                    │
│                                                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐ │
│  │  Cache Layer │  │ Celery Tasks │  │ Rate Limit   │ │
│  │              │  │              │  │              │ │
│  │ Try Redis    │  │ Try Redis    │  │ Try Redis    │ │
│  │ ↓ Fail       │  │ ↓ Fail       │  │ ↓ Fail       │ │
│  │ PostgreSQL   │  │ Queue local  │  │ Allow all    │ │
│  │ (L3 fallback)│  │ (spool mode) │  │ (no limit)   │ │
│  └──────────────┘  └──────────────┘  └──────────────┘ │
└─────────────────────────────────────────────────────────┘
```

---

## Implementation

### Redis Sentinel Configuration

#### Docker Compose Setup

```yaml
# docker-compose.yml additions

services:
  # Redis Master
  redis-master:
    image: redis:7-alpine
    container_name: stt-redis-master
    command: >
      redis-server
      --appendonly yes
      --replica-announce-ip redis-master
      --replica-announce-port 6379
    volumes:
      - redis_master_data:/data
    ports:
      - "6379:6379"
    networks:
      - redis_network
    restart: unless-stopped

  # Redis Replica
  redis-replica:
    image: redis:7-alpine
    container_name: stt-redis-replica
    command: >
      redis-server
      --appendonly yes
      --replicaof redis-master 6379
      --replica-announce-ip redis-replica
      --replica-announce-port 6379
    volumes:
      - redis_replica_data:/data
    ports:
      - "6380:6379"
    depends_on:
      - redis-master
    networks:
      - redis_network
    restart: unless-stopped

  # Sentinel 1
  redis-sentinel-1:
    image: redis:7-alpine
    container_name: stt-sentinel-1
    command: redis-sentinel /etc/redis/sentinel.conf
    volumes:
      - ./config/redis/sentinel.conf:/etc/redis/sentinel.conf:ro
      - sentinel_1_data:/data
    ports:
      - "26379:26379"
    depends_on:
      - redis-master
    networks:
      - redis_network
    restart: unless-stopped

  # Sentinel 2
  redis-sentinel-2:
    image: redis:7-alpine
    container_name: stt-sentinel-2
    command: redis-sentinel /etc/redis/sentinel.conf
    volumes:
      - ./config/redis/sentinel.conf:/etc/redis/sentinel.conf:ro
      - sentinel_2_data:/data
    ports:
      - "26380:26379"
    depends_on:
      - redis-master
    networks:
      - redis_network
    restart: unless-stopped

  # Sentinel 3
  redis-sentinel-3:
    image: redis:7-alpine
    container_name: stt-sentinel-3
    command: redis-sentinel /etc/redis/sentinel.conf
    volumes:
      - ./config/redis/sentinel.conf:/etc/redis/sentinel.conf:ro
      - sentinel_3_data:/data
    ports:
      - "26381:26379"
    depends_on:
      - redis-master
    networks:
      - redis_network
    restart: unless-stopped

volumes:
  redis_master_data:
  redis_replica_data:
  sentinel_1_data:
  sentinel_2_data:
  sentinel_3_data:

networks:
  redis_network:
    driver: bridge
```

#### Sentinel Configuration

```conf
# config/redis/sentinel.conf

port 26379
dir /data
sentinel monitor mymaster redis-master 6379 2
sentinel down-after-milliseconds mymaster 5000
sentinel parallel-syncs mymaster 1
sentinel failover-timeout mymaster 10000
sentinel announce-ip sentinel-1
sentinel announce-port 26379

# Ensure master is authenticating (if password set)
# sentinel auth-pass mymaster your_password

# Log file
logfile /var/log/redis/sentinel.log
```

### Sentinel Client Connection

```python
# backend/app/redis_client.py
from redis import Sentinel
from redis.retry import Retry
from redis.backoff import ExponentialBackoff
from typing import Optional
import logging

logger = logging.getLogger(__name__)

class SentinelRedisClient:
    """Redis client with Sentinel support and automatic failover"""

    def __init__(
        self,
        sentinel_hosts: list[str],
        master_name: str = "mymaster",
        password: Optional[str] = None,
        socket_timeout: float = 5.0,
        socket_connect_timeout: float = 5.0
    ):
        # Parse sentinel hosts
        sentinel_list = [
            (host.split(":")[0], int(host.split(":")[1]))
            for host in sentinel_hosts
        ]

        # Create Sentinel with retry logic
        retry = Retry(ExponentialBackoff(), retries=3)

        self.sentinel = Sentinel(
            sentinel_list,
            socket_timeout=socket_timeout,
            socket_connect_timeout=socket_connect_timeout,
            retry=retry,
            password=password,
            decode_responses=True
        )

        self.master_name = master_name
        self._master = None
        self._slave = None

    def get_master(self) -> redis.Redis:
        """Get master connection (with auto-discovery)"""
        try:
            if self._master is None:
                self._master = self.sentinel.master_for(
                    self.master_name,
                    socket_timeout=5.0
                )
            return self._master
        except Exception as e:
            logger.error(f"Failed to get master: {e}")
            raise RedisConnectionError(f"Cannot connect to master: {e}")

    def get_slave(self) -> redis.Redis:
        """Get slave connection for reads"""
        try:
            if self._slave is None:
                self._slave = self.sentinel.slave_for(
                    self.master_name,
                    socket_timeout=5.0
                )
            return self._slave
        except Exception as e:
            logger.warning(f"Failed to get slave, using master: {e}")
            # Fallback to master
            return self.get_master()

    def health_check(self) -> bool:
        """Check if Redis is available"""
        try:
            master = self.get_master()
            return master.ping()
        except Exception as e:
            logger.error(f"Redis health check failed: {e}")
            return False

# Global instance
_sentinel_client: Optional[SentinelRedisClient] = None

def get_redis_client() -> redis.Redis:
    """Get Redis client with fallback"""
    global _sentinel_client

    if _sentinel_client is None:
        _sentinel_client = SentinelRedisClient(
            sentinel_hosts=[
                "redis-sentinel-1:26379",
                "redis-sentinel-2:26379",
                "redis-sentinel-3:26379"
            ],
            master_name="mymaster"
        )

    return _sentinel_client.get_master()
```

### Graceful Degradation

#### Cache Layer Degradation

```python
# backend/app/cache/degrading_cache.py
from typing import Optional, Any

class DegradingMultiLevelCache:
    """Multi-level cache that degrades gracefully on Redis failure"""

    def __init__(
        self,
        l1: InMemoryCache,
        l2: RedisCache,
        l3: DatabaseCache
    ):
        self.l1 = l1
        self.l2 = l2
        self.l3 = l3
        self.redis_available = True

    def get(self, key: str) -> Optional[Any]:
        """Get from cache with degradation"""
        # L1: Always available (in-memory)
        value = self.l1.get(key)
        if value:
            return self._wrap_result(value, "L1")

        # L2: Check Redis (may be unavailable)
        if self.redis_available:
            try:
                value = self.l2.get(key)
                if value:
                    # Promote to L1
                    self.l1.put(key, value, ttl=timedelta(minutes=5))
                    return self._wrap_result(value, "L2")
            except redis.RedisError as e:
                logger.warning(f"Redis unavailable, falling back to L3: {e}")
                self.redis_available = False

        # L3: Database (always available)
        value = self.l3.get(key)
        if value:
            # Promote to L1 (skip L2 if Redis down)
            self.l1.put(key, value, ttl=timedelta(minutes=5))
            return self._wrap_result(value, "L3")

        return None

    def put(
        self,
        key: str,
        value: Any,
        cache_type: str,
        ttl_seconds: int
    ) -> None:
        """Put in cache with degradation"""
        # L1: Always store
        self.l1.put(key, value, ttl=timedelta(minutes=5))

        # L2: Try Redis
        if self.redis_available:
            try:
                l2_ttl = min(ttl_seconds, 86400)
                self.l2.put(key, value, ttl_seconds=l2_ttl)
            except redis.RedisError as e:
                logger.warning(f"Redis write failed, using L3 only: {e}")
                self.redis_available = False

        # L3: Always store (fallback)
        self.l3.put(key, value, cache_type, ttl_seconds)

    def check_redis_health(self) -> None:
        """Periodically check if Redis has recovered"""
        try:
            client = get_redis_client()
            client.ping()
            if not self.redis_available:
                logger.info("Redis recovered, resuming L2 cache operations")
                self.redis_available = True
        except:
            self.redis_available = False
```

#### Celery Degradation

```python
# backend/app/celery_degrade.py
from celery import Celery
from kombu import Queue
import tempfile
import json
import os

class DegradableCeleryApp:
    """Celery app that degrades to local queue on Redis failure"""

    def __init__(self, redis_available: bool = True):
        self.redis_available = redis_available
        self.local_queue_path = "/tmp/celery_fallback"
        self.celery_app = None

        if redis_available:
            self._setup_with_redis()
        else:
            self._setup_local_fallback()

    def _setup_with_redis(self):
        """Setup normal Celery with Redis broker"""
        self.celery_app = Celery('stt_tasks')
        self.celery_app.conf.update(
            broker_url='redis://redis-master:6379/0',
            result_backend='redis://redis-master:6379/1',
            task_serializer='json',
            result_serializer='json',
            accept_content=['json']
        )

    def _setup_local_fallback(self):
        """Setup local queue fallback"""
        logger.warning("Redis unavailable, using local queue fallback")
        os.makedirs(self.local_queue_path, exist_ok=True)

    def send_task(
        self,
        task_name: str,
        args: list = None,
        kwargs: dict = None
    ) -> Optional[str]:
        """Send task with fallback"""
        if self.redis_available:
            try:
                return self.celery_app.send_task(
                    task_name,
                    args=args or [],
                    kwargs=kwargs or {}
                ).id
            except Exception as e:
                logger.error(f"Celery send failed: {e}, using fallback")
                self._setup_local_fallback()

        # Fallback: Write to local queue
        return self._fallback_enqueue(task_name, args, kwargs)

    def _fallback_enqueue(
        self,
        task_name: str,
        args: list,
        kwargs: dict
    ) -> str:
        """Enqueue task to local filesystem"""
        task_id = str(uuid.uuid4())
        task_file = os.path.join(
            self.local_queue_path,
            f"{task_id}.json"
        )

        with open(task_file, 'w') as f:
            json.dump({
                "task_id": task_id,
                "task_name": task_name,
                "args": args or [],
                "kwargs": kwargs or {},
                "enqueued_at": time.time()
            }, f)

        logger.info(f"Task {task_name} enqueued to local fallback: {task_id}")
        return task_id

    def recover_local_queue(self):
        """Recover tasks from local queue when Redis recovers"""
        if not os.path.exists(self.local_queue_path):
            return

        recovered = 0
        for filename in os.listdir(self.local_queue_path):
            if not filename.endswith('.json'):
                continue

            filepath = os.path.join(self.local_queue_path, filename)

            try:
                with open(filepath, 'r') as f:
                    task_data = json.load(f)

                # Re-submit to Celery
                self.celery_app.send_task(
                    task_data['task_name'],
                    args=task_data['args'],
                    kwargs=task_data['kwargs']
                )

                os.remove(filepath)
                recovered += 1

            except Exception as e:
                logger.error(f"Failed to recover task {filename}: {e}")

        logger.info(f"Recovered {recovered} tasks from local queue")
```

#### Rate Limiting Degradation

```python
# backend/app/rate_limit_degrade.py
from enum import Enum

class DegradationMode(Enum):
    NORMAL = "normal"  # Full rate limiting
    DEGRADED = "degraded"  # In-memory only
    DISABLED = "disabled"  # No rate limiting

class DegradableRateLimiter:
    """Rate limiter that degrades gracefully"""

    def __init__(
        self,
        redis_client: redis.Redis,
        config: RateLimitConfig
    ):
        self.redis = redis_client
        self.config = config
        self.mode = DegradationMode.NORMAL
        self.fallback_store: dict[str, dict] = {}

    def acquire(
        self,
        identifier: str,
        tokens: int = 1,
        wait: bool = True,
        timeout: float = 60.0
    ) -> bool:
        """Acquire tokens with degradation"""

        if self.mode == DegradationMode.NORMAL:
            try:
                return self._acquire_from_redis(
                    identifier, tokens, wait, timeout
                )
            except redis.RedisError:
                logger.warning("Redis unavailable, degrading to in-memory")
                self.mode = DegradationMode.DEGRADED

        if self.mode == DegradationMode.DEGRADED:
            return self._acquire_from_memory(identifier, tokens)

        # Disabled mode: allow all
        return True

    def _acquire_from_redis(
        self,
        identifier: str,
        tokens: int,
        wait: bool,
        timeout: float
    ) -> bool:
        """Normal Redis-based rate limiting"""
        # Implementation from ADR-009
        pass

    def _acquire_from_memory(
        self,
        identifier: str,
        tokens: int
    ) -> bool:
        """Fallback in-memory rate limiting (per-process)"""
        now = time.time()

        if identifier not in self.fallback_store:
            self.fallback_store[identifier] = {
                "tokens": self.config.burst_size,
                "last_refill": now
            }

        bucket = self.fallback_store[identifier]

        # Refill tokens
        elapsed = now - bucket["last_refill"]
        tokens_to_add = int(elapsed * self.config.tokens_per_minute / 60)
        bucket["tokens"] = min(
            self.config.burst_size,
            bucket["tokens"] + tokens_to_add
        )
        bucket["last_refill"] = now

        # Check tokens
        if bucket["tokens"] >= tokens:
            bucket["tokens"] -= tokens
            return True

        return False

    def check_redis_health(self):
        """Check if Redis has recovered"""
        try:
            self.redis.ping()
            if self.mode != DegradationMode.NORMAL:
                logger.info("Redis recovered, resuming normal rate limiting")
                self.mode = DegradationMode.NORMAL
        except:
            pass
```

### Health Monitoring

```python
# backend/app/health.py
from fastapi import APIRouter
from typing import Dict

router = APIRouter()

@router.get("/health/redis")
async def redis_health() -> Dict:
    """Check Redis health"""
    try:
        client = get_redis_client()
        info = client.info()

        return {
            "status": "healthy",
            "mode": "master" if info.get("role") == "master" else "replica",
            "connected_clients": info.get("connected_clients"),
            "used_memory_human": info.get("used_memory_human"),
            "uptime_in_days": info.get("uptime_in_days")
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }

@router.get("/health/sentinel")
async def sentinel_health() -> Dict:
    """Check Sentinel health"""
    try:
        sentinel = get_redis_client().sentinel
        masters = sentinel.masters

        return {
            "status": "healthy",
            "masters": [
                {
                    "name": master["name"],
                    "ip": master["ip"],
                    "port": master["port"],
                    "flags": master["flags"]
                }
                for master in masters.values()
            ]
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }
```

---

## Alternatives Considered

### 1. Redis Cluster

**Pros:** Horizontal scaling, automatic sharding
**Cons:** Complex setup, cross-slot operations, requires 6+ nodes
**Decision:** Overkill for current scale, Sentinel sufficient

### 2. Redis Standalone (Current)

**Pros:** Simple, no overhead
**Cons:** Single point of failure
**Decision:** Too risky for production

### 3. Memcached Fallback

**Pros:** Simple cache layer
**Cons:** No persistence, no Celery support
**Decision:** PostgreSQL fallback provides persistence

### 4. AWS ElastiCache

**Pros:** Managed service, automatic failover
**Cons:** Vendor lock-in, cost
**Decision:** Self-host for cost control

---

## Failover Process

### Automatic Failover (Sentinel)

```
1. Master failure detected (down-after-milliseconds: 5000)
2. Sentinels agree master is down (quorum: 2/3)
3. Sentinel leader elected
4. Replica promoted to master
5. Other replicas reconfigured
6. Applications reconnect to new master
7. Total time: ~10-15 seconds
```

### Application Reconnection

```python
# Auto-reconnection logic
def execute_with_retry(
    operation: callable,
    max_retries: int = 3,
    base_delay: float = 1.0
):
    """Execute Redis operation with auto-retry on failover"""
    for attempt in range(max_retries):
        try:
            return operation()
        except redis.ConnectionError as e:
            if attempt < max_retries - 1:
                delay = base_delay * (2 ** attempt)
                logger.warning(f"Redis connection error, retry in {delay}s")
                time.sleep(delay)
                # Force reconnection
                get_redis_client(force_new=True)
            else:
                raise
```

---

## Monitoring

### Sentinel Metrics

```python
# Prometheus metrics
sentinel_master_changes_total = Counter(
    'sentinel_master_changes_total',
    'Number of Sentinel master failovers'
)

redis_failover_events = Gauge(
    'redis_failover_events',
    'Redis failover events',
    ['from', 'to']
)

degradation_mode = Gauge(
    'redis_degradation_mode',
    'Current degradation mode (0=normal, 1=degraded, 2=disabled)'
)
```

### Health Checks

```bash
# Sentinel CLI commands
redis-cli -p 26379 SENTINEL masters
redis-cli -p 26379 SENTINEL slaves mymaster
redis-cli -p 26379 SENTINEL sentinels mymaster
redis-cli -p 26379 SENTINEL ckquorum mymaster
```

---

## Rollback Strategies

### Rollback to Standalone Redis

```yaml
# docker-compose.yml
redis:
  image: redis:7-alpine
  command: redis-server --appendonly yes
  ports:
    - "6379:6379"
  volumes:
    - redis_data:/data
```

### Rollback Steps

1. Update `backend/app/config.py` to use standalone Redis
2. Disable Sentinel client
3. Remove graceful degradation (use direct Redis errors)
4. Monitor for Redis failures

---

## Consequences

### Positive

1. **High Availability:** Automatic failover in 10-15 seconds
2. **Graceful Degradation:** App continues with reduced functionality
3. **No Data Loss:** Redis replication prevents data loss
4. **Operational Excellence:** Clear health monitoring

### Negative

1. **Complexity:** Sentinel requires 3+ additional containers
2. **Eventual Consistency:** During failover, brief inconsistency possible
3. **Resource Usage:** Replica doubles Redis memory usage
4. **Operational Overhead:** Monitoring and maintenance

### Mitigations

- Use Docker Compose for easy deployment
- Implement comprehensive health checks
- Document failover procedures
- Regular failover drills
- Monitor degradation mode metrics

---

**Document Control**

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-02-03 | Performance Team | Initial ADR |
