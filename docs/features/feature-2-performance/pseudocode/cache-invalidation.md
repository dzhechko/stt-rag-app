# Pseudocode: Cache Invalidation

**Feature:** Performance Optimizations
**Algorithm:** Multi-Level Cache Invalidation

---

## Overview

Invalidate cached entries across L1 (Memory), L2 (Redis), and L3 (PostgreSQL) with proper cascade and consistency.

---

## Algorithm: Cache Invalidation

```
FUNCTION invalidate_cache(key, scope="all", reason="manual"):
    INPUT:
        key: Cache key pattern or exact key
        scope: Which levels to clear (l1, l2, l3, all)
        reason: Reason for invalidation

    OUTPUT:
        stats: Invalidation statistics

    stats = {
        "l1_deleted": 0,
        "l2_deleted": 0,
        "l3_deleted": 0,
        "total_deleted": 0
    }

    # Step 1: Invalidate L1 (In-Memory)
    IF scope IN ["l1", "all"]:
        deleted = cache_l1_delete_pattern(key)
        stats.l1_deleted = deleted

    # Step 2: Invalidate L2 (Redis)
    IF scope IN ["l2", "all"]:
        deleted = cache_l2_delete_pattern(key)
        stats.l2_deleted = deleted

    # Step 3: Invalidate L3 (PostgreSQL)
    IF scope IN ["l3", "all"]:
        deleted = cache_l3_delete_pattern(key)
        stats.l3_deleted = deleted

    stats.total_deleted = (
        stats.l1_deleted +
        stats.l2_deleted +
        stats.l3_deleted
    )

    # Step 4: Log invalidation event
    LOG "Cache invalidation: {key} ({reason}) - {stats.total_deleted} entries deleted"

    # Step 5: Publish invalidation event
    PUBLISH_EVENT(
        event_type="cache_invalidated",
        cache_key=key,
        scope=scope,
        reason=reason,
        entries_deleted=stats.total_deleted
    )

    RETURN stats


FUNCTION cache_l1_delete_pattern(pattern):
    INPUT:
        pattern: Key pattern to delete (supports wildcards)

    OUTPUT:
        deleted: Number of keys deleted

    cache = get_l1_cache_instance()
    deleted = 0

    # Get all keys
    all_keys = cache.keys()

    # Filter matching keys
    IF pattern CONTAINS "*":
        # Wildcard matching
        regex = wildcard_to_regex(pattern)
        matching_keys = [key FOR key IN all_keys IF regex.match(key)]
    ELSE:
        # Exact match
        matching_keys = [key FOR key IN all_keys IF key == pattern]

    # Delete matching keys
    FOR EACH key IN matching_keys:
        cache.delete(key)
        deleted += 1

    RETURN deleted


FUNCTION cache_l2_delete_pattern(pattern):
    INPUT:
        pattern: Key pattern to delete

    OUTPUT:
        deleted: Number of keys deleted

    redis = get_redis_client()
    deleted = 0

    # Use SCAN to find matching keys (non-blocking)
    cursor = 0
    pattern = pattern.replace("*", "*")

    WHILE cursor != 0:
        cursor, keys = redis.scan(
            cursor=cursor,
            match=pattern,
            count=1000
        )

        IF keys NOT EMPTY:
            # Delete found keys
            deleted += redis.delete(*keys)

    RETURN deleted


FUNCTION cache_l3_delete_pattern(pattern):
    INPUT:
        pattern: Key pattern to delete

    OUTPUT:
        deleted: Number of rows deleted

    db = get_db_session()

    # Convert pattern to SQL LIKE pattern
    sql_pattern = pattern.replace("*", "%")

    # Delete matching entries
    deleted = db.query(CacheEntry).filter(
        CacheEntry.cache_key.like(sql_pattern)
    ).delete()

    db.commit()

    RETURN deleted


FUNCTION invalidate_by_transcript_id(transcript_id, reason="manual"):
    INPUT:
        transcript_id: ID of transcript to invalidate
        reason: Reason for invalidation

    OUTPUT:
        stats: Invalidation statistics

    # Invalidate all cached data for this transcript
    patterns = [
        f"transcript:{transcript_id}:*",        # All transcriptions
        f"summary:{transcript_id}:*",           # All summaries
        f"embeddings:{transcript_id}:*",        # All embeddings
        f"translation:{transcript_id}:*"       # All translations
    ]

    total_stats = {"total_deleted": 0}

    FOR EACH pattern IN patterns:
        stats = invalidate_cache(pattern, scope="all", reason=reason)
        total_stats.total_deleted += stats.total_deleted

    RETURN total_stats


FUNCTION invalidate_by_file_hash(file_hash, reason="file_changed"):
    INPUT:
        file_hash: SHA-256 hash of file content
        reason: Reason for invalidation

    OUTPUT:
        stats: Invalidation statistics

    # Invalidate all cache entries for this file hash
    pattern = f"*:{file_hash}:*"
    stats = invalidate_cache(pattern, scope="all", reason=reason)

    RETURN stats


FUNCTION invalidate_ttl_expired():
    INPUT:
        None (runs as periodic task)

    OUTPUT:
        stats: TTL expiration statistics

    stats = {
        "l1_expired": 0,
        "l2_expired": 0,
        "l3_expired": 0,
        "total_expired": 0
    }

    # L1: In-memory cache (automatic eviction on access)
    # Just collect stats, no explicit cleanup needed
    stats.l1_expired = count_l1_expired()

    # L2: Redis (TTL is automatic)
    # Just get count of expiring keys
    stats.l2_expired = count_l2_expiring_soon()

    # L3: PostgreSQL (manual cleanup needed)
    expired_entries = db.query(CacheEntry).filter(
        CacheEntry.created_at + CacheEntry.ttl_seconds < NOW()
    ).all()

    FOR EACH entry IN expired_entries:
        db.delete(entry)
        stats.l3_expired += 1

    db.commit()

    stats.total_expired = stats.l1_expired + stats.l2_expired + stats.l3_expired

    LOG "TTL expiration cleanup: {stats.total_expired} entries removed"

    RETURN stats


FUNCTION warm_cache(transcript_ids):
    INPUT:
        transcript_ids: List of transcript IDs to warm

    OUTPUT:
        stats: Warming statistics

    stats = {
        "attempted": 0,
        "warmed": 0,
        "skipped": 0,
        "failed": 0
    }

    FOR EACH transcript_id IN transcript_ids:
        stats.attempted += 1

        # Check if already cached
        cache_key = f"transcript:{transcript_id}:*"

        # Try L1 first
        IF cache_l1_exists(cache_key):
            stats.skipped += 1
            CONTINUE

        # Try L2
        IF cache_l2_exists(cache_key):
            # Promote to L1
            data = cache_l2_get(cache_key)
            cache_l1_put(cache_key, data)
            stats.warmed += 1
            CONTINUE

        # Try L3
        IF cache_l3_exists(cache_key):
            data = cache_l3_get(cache_key)

            # Promote to L2 and L1
            cache_l2_put(cache_key, data, ttl=86400)
            cache_l1_put(cache_key, data, ttl=300)
            stats.warmed += 1
            CONTINUE

        # Not in any cache - skip (would require recomputation)
        stats.skipped += 1

    LOG "Cache warming: {stats.warmed}/{stats.attempted} entries warmed"

    RETURN stats


FUNCTION invalidate_on_file_update(transcript_id, new_file_hash):
    INPUT:
        transcript_id: ID of transcript being updated
        new_file_hash: New file hash

    OUTPUT:
        None

    # Step 1: Invalidate old cache entries (by file hash if known)
    # For now, invalidate by transcript_id
    invalidate_by_transcript_id(transcript_id, reason="file_updated")

    # Step 2: Pre-compute cache key for new file
    new_cache_key = f"transcript:{new_file_hash}:auto"

    # Step 3: Optionally pre-fetch and cache
    IF CONFIG.prewarm_on_update == TRUE:
        # Submit async job to process and cache
        SUBMIT_TASK(
            task="prewarm_transcript",
            transcript_id=transcript_id,
            cache_key=new_cache_key
        )

    LOG "Invalidated cache for transcript {transcript_id} on file update"


FUNCTION cache_invalidation_cascade(source_key, cascade_depth=1):
    INPUT:
        source_key: Original key that was invalidated
        cascade_depth: How many levels to cascade (default: 1)

    OUTPUT:
        cascaded_keys: List of keys that were invalidated

    cascaded_keys = []

    # Level 1: Direct dependencies
    dependencies = find_cache_dependencies(source_key)

    FOR EACH dep_key IN dependencies:
        invalidate_cache(dep_key, scope="all", reason="cascade")
        cascaded_keys.append(dep_key)

        # Level 2: Indirect dependencies (if cascade_depth > 1)
        IF cascade_depth > 1:
            sub_keys = cache_invalidation_cascade(dep_key, cascade_depth - 1)
            cascaded_keys.extend(sub_keys)

    RETURN cascaded_keys


FUNCTION find_cache_dependencies(cache_key):
    INPUT:
        cache_key: Cache key to find dependencies for

    OUTPUT:
        dependencies: List of dependent cache keys

    dependencies = []

    # Parse cache key components
    parts = cache_key.split(":")

    IF parts[0] == "transcript":
        # Transcript dependencies:
        # - Summaries derived from this transcript
        # - Embeddings derived from this transcript
        # - Translations derived from this transcript

        transcript_id = parts[1]

        dependencies.extend([
            f"summary:{transcript_id}:*",
            f"embeddings:{transcript_id}:*",
            f"translation:{transcript_id}:*"
        ])

    ELSE IF parts[0] == "summary":
        # Summaries don't have direct dependencies
        PASS

    ELSE IF parts[0] == "embeddings":
        # Embeddings don't have direct dependencies
        PASS

    RETURN dependencies
```

---

## Inactivation Scenarios

### 1. Manual Invalidation

User explicitly clears cache for a transcript:

```
POST /api/transcripts/{id}/cache/clear
→ invalidate_by_transcript_id(id, "manual")
```

### 2. File Updated

Original file is replaced:

```
PUT /api/transcripts/{id}
→ invalidate_on_file_update(id, new_hash)
```

### 3. TTL Expired

Periodic cleanup task:

```
Celery Beat Task: cleanup_expired_cache
→ invalidate_ttl_expired()
→ Runs every hour
```

### 4. Cascade Invalidation

Related data invalidated together:

```
Transcript changed
→ invalidate cache
→ cascade to summaries
→ cascade to embeddings
```

---

## Data Structures

### Cache Entry

```
STRUCT CacheEntry:
    id: UUID
    cache_key: STRING           # "transcript:abc123:ru"
    cache_type: STRING          # "transcript", "summary", etc.
    value: JSONB                # Cached data
    language: STRING            # "ru", "en", "auto"
    file_hash: STRING           # SHA-256 hash
    created_at: TIMESTAMP
    accessed_at: TIMESTAMP
    access_count: INTEGER
    ttl_seconds: INTEGER
    size_bytes: INTEGER
```

### Invalidation Event

```
STRUCT InvalidationEvent:
    event_id: UUID
    timestamp: TIMESTAMP
    cache_key: STRING
    scope: STRING               # "l1", "l2", "l3", "all"
    reason: STRING             # "manual", "ttl", "cascade", etc.
    entries_deleted: INTEGER
    cascade_depth: INTEGER      # If cascade invalidation
```

---

## Optimization Strategies

### 1. Batch Invalidation

```
FUNCTION invalidate_batch(keys):
    # Group by cache level for efficient deletion
    l1_keys = [key FOR key IN keys IF is_l1_key(key)]
    l2_keys = [key FOR key IN keys IF is_l2_key(key)]
    l3_keys = [key FOR key IN keys IF is_l3_key(key)]

    # Delete in batch
    cache_l1_delete_many(l1_keys)
    cache_l2_delete_many(l2_keys)
    cache_l3_delete_many(l3_keys)
```

### 2. Lazy Invalidation

```
# Instead of immediate deletion, mark as invalid
FUNCTION mark_invalid(key):
    SET key:valid = FALSE
    SET key:invalidated_at = NOW()

# Actual cleanup happens on next access
FUNCTION get_with_cleanup(key):
    entry = cache.get(key)
    IF entry.valid == FALSE:
        cache.delete(key)
        RETURN NULL
    RETURN entry.value
```

### 3. Predictive Invalidation

```
# Predict which entries will be accessed soon
FUNCTION predict_access_patterns():
    recent_accesses = get_recent_access_patterns()

    FOR EACH pattern IN recent_accesses:
        IF pattern.frequency > threshold:
            warm_cache(pattern.transcript_ids)
```

---

**Document Control**

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-02-03 | Performance Team | Initial pseudocode |
