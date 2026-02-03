# ADR-002: Multi-Level Redis Caching Strategy

**Status:** Accepted
**Date:** 2026-02-03
**Context:** Performance Optimization Feature

---

## Context

The STT application performs expensive operations that could benefit from caching:

1. **Transcription Results:** Cloud.ru API calls take 12-15 seconds
2. **Embeddings:** Vector generation is CPU-intensive
3. **Summaries:** LLM generation is slow and costly
4. **Translations:** Repeated requests for same content

Currently, no caching exists - every request hits the external APIs.

---

## Decision

Implement a **3-tier caching strategy** with content-addressed cache keys:

```
┌─────────────────────────────────────────────────────────────────┐
│                        Application Layer                        │
└────────────────────────────┬────────────────────────────────────┘
                             │
        ┌────────────────────┼────────────────────┐
        │                    │                    │
┌───────▼────────┐  ┌────────▼────────┐  ┌───────▼────────┐
│   L1 Cache     │  │   L2 Cache      │  │   L3 Cache      │
│  (In-Memory)   │  │   (Redis)       │  │  (PostgreSQL)   │
│                │  │                 │  │                 │
│  - Dict-based  │  │  - Redis        │  │  - Table:       │
│  - 5 min TTL   │  │  - 24 hour TTL  │  │    cache_entries │
│  - ~100MB      │  │  - ~5GB         │  │  - Permanent    │
│  - Fastest     │  │  - Fast         │  │  - Fallback     │
└────────────────┘  └─────────────────┘  └─────────────────┘
        │                    │                    │
        │                    │                    │
        └────────────────────┼────────────────────┘
                             │
                             ▼
                    Cache Key Format:
                    {type}:{hash}:{language}
                    e.g., "transcript:a1b2...:ru"
```

---

## Cache Key Design

### Content-Addressed Keys

Cache keys are based on **content hash** (SHA-256), not arbitrary IDs:

```python
import hashlib
from typing import Optional

class CacheKey:
    """Content-addressed cache key"""

    @staticmethod
    def for_transcript(file_hash: str, language: str) -> str:
        """Generate cache key for transcription"""
        return f"transcript:{file_hash}:{language}"

    @staticmethod
    def for_embeddings(text_hash: str) -> str:
        """Generate cache key for embeddings"""
        return f"embeddings:{text_hash}"

    @staticmethod
    def for_summary(text_hash: str, template: str) -> str:
        """Generate cache key for summary"""
        return f"summary:{text_hash}:{template}"

    @staticmethod
    def for_translation(text_hash: str, target_lang: str) -> str:
        """Generate cache key for translation"""
        return f"translation:{text_hash}:{target_lang}"

    @staticmethod
    def hash_content(content: bytes) -> str:
        """Generate SHA-256 hash of content"""
        return hashlib.sha256(content).hexdigest()

    @staticmethod
    def hash_file(file_path: str) -> str:
        """Generate hash of file content"""
        with open(file_path, 'rb') as f:
            return CacheKey.hash_content(f.read())
```

---

## Cache Levels

### L1: In-Memory Cache

**Purpose:** Ultra-fast access for repeated requests in same session

**Implementation:** Python dict with TTL

```python
from datetime import datetime, timedelta
from typing import Any, Dict
import threading

class InMemoryCache:
    """L1 in-memory cache with TTL"""

    def __init__(self, max_size: int = 1000, default_ttl: timedelta = timedelta(minutes=5)):
        self.cache: Dict[str, tuple[Any, datetime]] = {}
        self.max_size = max_size
        self.default_ttl = default_ttl
        self.lock = threading.RLock()

    def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        with self.lock:
            if key not in self.cache:
                return None

            value, expiry = self.cache[key]

            # Check expiration
            if datetime.utcnow() > expiry:
                del self.cache[key]
                return None

            return value

    def put(self, key: str, value: Any, ttl: timedelta = None) -> None:
        """Put value in cache"""
        with self.lock:
            # Evict if at capacity
            if len(self.cache) >= self.max_size:
                self._evict_lru()

            expiry = datetime.utcnow() + (ttl or self.default_ttl)
            self.cache[key] = (value, expiry)

    def delete(self, key: str) -> None:
        """Delete from cache"""
        with self.lock:
            self.cache.pop(key, None)

    def clear(self) -> None:
        """Clear all cache entries"""
        with self.lock:
            self.cache.clear()

    def _evict_lru(self) -> None:
        """Evict least recently used entry"""
        # Simple LRU: sort by expiry time
        if not self.cache:
            return

        lru_key = min(self.cache.keys(), key=lambda k: self.cache[k][1])
        del self.cache[lru_key]

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        with self.lock:
            return {
                "size": len(self.cache),
                "max_size": self.max_size,
                "memory_usage_mb": sum(
                    len(str(v)) for v, _ in self.cache.values()
                ) / (1024 * 1024)
            }
```

---

### L2: Redis Cache

**Purpose:** Shared cache across all workers with persistence

**Implementation:** Redis with TTL

```python
import redis
import json
from typing import Optional, Any

class RedisCache:
    """L2 Redis cache"""

    def __init__(self, redis_url: str = "redis://redis:6379/0"):
        self.client = redis.from_url(
            redis_url,
            decode_responses=True,
            health_check_interval=30
        )

    def get(self, key: str) -> Optional[Any]:
        """Get value from Redis"""
        try:
            value = self.client.get(key)
            if value:
                return json.loads(value)
            return None
        except redis.RedisError as e:
            logger.error(f"Redis GET error: {e}")
            return None

    def put(self, key: str, value: Any, ttl_seconds: int) -> None:
        """Put value in Redis"""
        try:
            serialized = json.dumps(value)
            self.client.setex(
                key,
                ttl_seconds,
                serialized
            )
        except redis.RedisError as e:
            logger.error(f"Redis SET error: {e}")

    def delete(self, key: str) -> None:
        """Delete from Redis"""
        try:
            self.client.delete(key)
        except redis.RedisError as e:
            logger.error(f"Redis DELETE error: {e}")

    def get_many(self, keys: list[str]) -> Dict[str, Any]:
        """Get multiple values"""
        try:
            values = self.client.mget(keys)
            return {
                k: json.loads(v)
                for k, v in zip(keys, values)
                if v is not None
            }
        except redis.RedisError as e:
            logger.error(f"Redis MGET error: {e}")
            return {}

    def invalidate_pattern(self, pattern: str) -> None:
        """Delete all keys matching pattern"""
        try:
            keys = self.client.keys(pattern)
            if keys:
                self.client.delete(*keys)
        except redis.RedisError as e:
            logger.error(f"Redis pattern delete error: {e}")
```

---

### L3: PostgreSQL Cache

**Purpose:** Permanent cache storage, fallback when Redis unavailable

**Implementation:** Database table

```sql
-- Cache entries table
CREATE TABLE cache_entries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    cache_key VARCHAR(500) UNIQUE NOT NULL,
    cache_type VARCHAR(50) NOT NULL,  -- transcript, embeddings, summary
    value JSONB NOT NULL,
    language VARCHAR(10),
    file_hash VARCHAR(64),
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    accessed_at TIMESTAMP,
    access_count INTEGER NOT NULL DEFAULT 0,
    size_bytes INTEGER NOT NULL,
    ttl_seconds INTEGER,

    INDEX idx_cache_key (cache_key),
    INDEX idx_cache_type (cache_type),
    INDEX idx_file_hash (file_hash),
    INDEX idx_created_at (created_at)
);

-- Cache statistics table
CREATE TABLE cache_stats (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    date DATE NOT NULL DEFAULT CURRENT_DATE,
    cache_type VARCHAR(50) NOT NULL,
    hits INTEGER NOT NULL DEFAULT 0,
    misses INTEGER NOT NULL DEFAULT 0,

    UNIQUE (date, cache_type)
);
```

```python
from sqlalchemy.orm import Session
from datetime import datetime, timedelta

class DatabaseCache:
    """L3 PostgreSQL cache"""

    def __init__(self, db_session: Session):
        self.db = db_session

    def get(self, key: str) -> Optional[Any]:
        """Get value from database"""
        entry = self.db.query(CacheEntry).filter_by(
            cache_key=key
        ).first()

        if not entry:
            self._record_miss(key)
            return None

        # Check TTL
        if entry.is_expired():
            self.db.delete(entry)
            self.db.commit()
            return None

        # Update access stats
        entry.accessed_at = datetime.utcnow()
        entry.access_count += 1
        self.db.commit()

        self._record_hit(key)
        return entry.value

    def put(
        self,
        key: str,
        value: Any,
        cache_type: str,
        ttl_seconds: int
    ) -> None:
        """Put value in database"""
        entry = CacheEntry(
            cache_key=key,
            cache_type=cache_type,
            value=value,
            ttl_seconds=ttl_seconds,
            created_at=datetime.utcnow(),
            size_bytes=len(json.dumps(value))
        )

        self.db.merge(entry)
        self.db.commit()

    def delete(self, key: str) -> None:
        """Delete from database"""
        self.db.query(CacheEntry).filter_by(
            cache_key=key
        ).delete()
        self.db.commit()

    def cleanup_expired(self) -> int:
        """Remove expired entries"""
        deleted = self.db.query(CacheEntry).filter(
            CacheEntry.created_at + CacheEntry.ttl_seconds < datetime.utcnow()
        ).delete()
        self.db.commit()
        return deleted

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        total = self.db.query(CacheEntry).count()
        by_type = self.db.query(
            CacheEntry.cache_type,
            func.count(CacheEntry.id)
        ).group_by(CacheEntry.cache_type).all()

        return {
            "total_entries": total,
            "by_type": {t: c for t, c in by_type},
            "total_size_mb": self.db.query(
                func.sum(CacheEntry.size_bytes)
            ).scalar() / (1024 * 1024) or 0
        }

    def _record_hit(self, key: str) -> None:
        """Record cache hit"""
        cache_type = key.split(':')[0]
        today = datetime.utcnow().date()

        stat = self.db.query(CacheStats).filter_by(
            date=today,
            cache_type=cache_type
        ).first()

        if stat:
            stat.hits += 1
        else:
            stat = CacheStats(date=today, cache_type=cache_type, hits=1)
            self.db.add(stat)

        self.db.commit()

    def _record_miss(self, key: str) -> None:
        """Record cache miss"""
        cache_type = key.split(':')[0]
        today = datetime.utcnow().date()

        stat = self.db.query(CacheStats).filter_by(
            date=today,
            cache_type=cache_type
        ).first()

        if stat:
            stat.misses += 1
        else:
            stat = CacheStats(date=today, cache_type=cache_type, misses=1)
            self.db.add(stat)

        self.db.commit()
```

---

## Multi-Level Cache Manager

```python
class MultiLevelCache:
    """Orchestrates L1, L2, L3 cache levels"""

    def __init__(
        self,
        l1: InMemoryCache,
        l2: RedisCache,
        l3: DatabaseCache
    ):
        self.l1 = l1
        self.l2 = l2
        self.l3 = l3

    def get(self, key: str) -> Optional[Any]:
        """Get from cache (L1 -> L2 -> L3)"""
        # L1: Check in-memory
        value = self.l1.get(key)
        if value:
            return self._wrap_result(value, "L1")

        # L2: Check Redis
        value = self.l2.get(key)
        if value:
            # Promote to L1
            self.l1.put(key, value, ttl=timedelta(minutes=5))
            return self._wrap_result(value, "L2")

        # L3: Check database
        value = self.l3.get(key)
        if value:
            # Promote to L2, then L1
            self.l2.put(key, value, ttl_seconds=86400)  # 24 hours
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
        """Put in all cache levels"""
        # L1: Cap at 5 minutes
        self.l1.put(key, value, ttl=timedelta(minutes=5))

        # L2: Cap at 24 hours
        l2_ttl = min(ttl_seconds, 86400)
        self.l2.put(key, value, ttl_seconds=l2_ttl)

        # L3: Full TTL
        self.l3.put(key, value, cache_type, ttl_seconds)

    def delete(self, key: str) -> None:
        """Delete from all cache levels"""
        self.l1.delete(key)
        self.l2.delete(key)
        self.l3.delete(key)

    def invalidate_pattern(self, pattern: str) -> None:
        """Invalidate matching keys in all levels"""
        self.l1.clear()  # Clear all L1
        self.l2.invalidate_pattern(f"*{pattern}*")
        self.l3.invalidate_pattern(pattern)

    def get_stats(self) -> Dict[str, Any]:
        """Get aggregate cache statistics"""
        return {
            "l1": self.l1.get_stats(),
            "l2": {
                "keys": self.l2.client.dbsize(),
                "memory_mb": self.l2.client.info()["used_memory"] / (1024 * 1024)
            },
            "l3": self.l3.get_stats()
        }

    def _wrap_result(
        self,
        value: Any,
        source: str
    ) -> Dict[str, Any]:
        """Wrap result with metadata"""
        return {
            "value": value,
            "source": source,
            "timestamp": datetime.utcnow().isoformat()
        }
```

---

## Integration Example

```python
# backend/app/services/transcription_service.py

class TranscriptionService:
    def __init__(self, cache: MultiLevelCache):
        self.cache = cache
        self.client = OpenAI(...)

    def transcribe_file(
        self,
        file_path: str,
        language: Optional[str] = None
    ) -> Dict[str, Any]:
        # Generate cache key
        file_hash = CacheKey.hash_file(file_path)
        cache_key = CacheKey.for_transcript(file_hash, language or "auto")

        # Check cache
        cached = self.cache.get(cache_key)
        if cached:
            logger.info(f"Cache hit: {cache_key} (from {cached['source']})")
            return cached["value"]

        # Transcribe via API
        result = self._call_api(file_path, language)

        # Cache result
        self.cache.put(
            key=cache_key,
            value=result,
            cache_type="transcript",
            ttl_seconds=86400  # 24 hours
        )

        return result
```

---

## TTL Configuration

| Cache Type | L1 TTL | L2 TTL | L3 TTL | Rationale |
|------------|--------|--------|--------|-----------|
| Transcript | 5 min | 24 hours | 7 days | Rarely changes |
| Embeddings | 5 min | 7 days | 30 days | Static vectors |
| Summary | 5 min | 24 hours | 7 days | May regenerate |
| Translation | 5 min | 24 hours | 7 days | Language-specific |

---

## Consequences

### Positive

1. **Performance:** >70% hit rate for repeated content
2. **Cost:** Reduced API usage = lower cloud bills
3. **Reliability:** Graceful degradation if Redis unavailable
4. **Flexibility:** Content-addressed keys deduplicate automatically

### Negative

1. **Complexity:** Three-tier system to manage
2. **Storage:** Additional storage requirements
3. **Staleness:** Cached data may be outdated
4. **Invalidation:** Manual invalidation required for updates

### Mitigations

- Configurable TTL per cache type
- Automatic expiration
- Admin endpoints for manual invalidation
- Cache hit/miss monitoring

---

## References

- Redis Caching: https://redis.io/docs/manual/patterns/caching/
- Cache Patterns: https://docs.aws.amazon.com/whitepapers/latest/database-caching-strategies-using-redis/
- Content Addressing: https://en.wikipedia.org/wiki/Content-addressable_storage

---

**Document Control**

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-02-03 | Performance Team | Initial ADR |
