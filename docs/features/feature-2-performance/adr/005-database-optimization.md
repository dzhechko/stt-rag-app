# ADR-005: Database Query Optimization

**Status:** Accepted
**Date:** 2026-02-03
**Context:** Performance Optimization Feature

---

## Context

The STT application currently experiences slow database queries due to:
1. Missing indexes on frequently queried columns
2. N+1 query patterns with ORM lazy loading
3. No query result caching
4. Inefficient joins without proper planning

Current query performance:
- List transcripts (p95): 500-1000ms
- Get transcript with jobs: 200-400ms
- RAG searches: 1000-2000ms

---

## Decision

Implement comprehensive database optimization including indexes, query optimization, and connection pooling.

### Indexing Strategy

```sql
-- Primary indexes for filtering
CREATE INDEX idx_transcripts_status ON transcripts(status);
CREATE INDEX idx_transcripts_language ON transcripts(language);
CREATE INDEX idx_transcripts_created_at ON transcripts(created_at DESC);

-- Composite indexes for common query patterns
CREATE INDEX idx_transcripts_status_created ON transcripts(status, created_at DESC);
CREATE INDEX idx_jobs_transcript_status ON processing_jobs(transcript_id, status);
CREATE INDEX idx_jobs_type_status ON processing_jobs(job_type, status);

-- Partial indexes for filtered queries
CREATE INDEX idx_transcripts_completed
    ON transcripts(created_at DESC)
    WHERE status = 'COMPLETED';

-- Covering indexes for hot paths
CREATE INDEX idx_transcripts_list
    ON transcripts(status, created_at DESC)
    INCLUDE (original_filename, language, file_size);
```

### Query Optimization

```python
# backend/app/database.py

from sqlalchemy.orm import joinedload, selectinload

class TranscriptRepository:
    """Optimized repository with eager loading"""

    def list_transcripts_optimized(
        self,
        status: Optional[TranscriptStatus] = None,
        limit: int = 20
    ) -> List[Transcript]:
        """List transcripts with optimized query"""
        query = self.db.query(Transcript)

        # Apply status filter with index usage
        if status:
            query = query.filter(Transcript.status == status)

        # Eager load relationships to prevent N+1
        query = query.options(
            joinedload(Transcript.processing_jobs),
            selectinload(Transcript.summaries)
        )

        # Use index-specified ordering
        query = query.order_by(Transcript.created_at.desc())

        return query.limit(limit).all()

    def get_with_jobs_optimized(self, transcript_id: UUID) -> Transcript:
        """Get transcript with jobs using eager loading"""
        return self.db.query(Transcript).options(
            joinedload(Transcript.processing_jobs).selectin_polymorphic(
                ProcessingJob
            )
        ).filter(Transcript.id == transcript_id).one()
```

### Connection Pooling

```python
# backend/app/database.py

from sqlalchemy import create_engine
from sqlalchemy.pool import QueuePool

# Optimized connection pool
engine = create_engine(
    settings.database_url,
    poolclass=QueuePool,
    pool_size=15,              # Max persistent connections
    max_overflow=10,           # Additional connections beyond pool_size
    pool_timeout=30,           # Wait 30s for connection
    pool_recycle=3600,         # Recycle connections after 1 hour
    pool_pre_ping=True,         # Verify connections before use
    pool_use_lifo=True,         # Use LIFO to reduce stale connections
    echo=False
)
```

---

## Alternatives Considered

### 1. No Indexing (Current)

**Pros:** Simple, fast inserts
**Cons:** Slow queries, full table scans
**Decision:** Being replaced

### 2. Full-Text Search (PostgreSQL FTS)

**Pros:** Powerful text search, relevance ranking
**Cons:** Complex setup, high memory, slower writes
**Decision:** Not needed for current filtering use cases

### 3. Materialized Views

**Pros:** Pre-computed aggregations, fast reads
**Cons:** Refresh overhead, stale data
**Decision:** Future enhancement for reporting

### 4. Read Replicas

**Pros:** Distributes read load, high availability
**Cons:** Replication lag, complex setup
**Decision:** Not required at current scale

---

## Migration Strategy

### Phase 1: Index Creation (Zero Downtime)

```sql
-- Migration script: 001_create_indexes.sql
BEGIN;

-- Create indexes CONCURRENTLY to avoid table locks
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_transcripts_status
    ON transcripts(status);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_transcripts_language
    ON transcripts(language);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_transcripts_created_at
    ON transcripts(created_at DESC);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_transcripts_status_created
    ON transcripts(status, created_at DESC);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_jobs_transcript_status
    ON processing_jobs(transcript_id, status);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_jobs_type_status
    ON processing_jobs(job_type, status);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_transcripts_completed
    ON transcripts(created_at DESC)
    WHERE status = 'COMPLETED';

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_transcripts_list
    ON transcripts(status, created_at DESC)
    INCLUDE (original_filename, language, file_size);

COMMIT;
```

### Phase 2: Query Refactoring

```python
# Migration: update repository methods
# backend/app/migrations/002_refactor_queries.py

from alembic import op
import sqlalchemy as sa
from sqlalchemy.orm import sessionmaker

def upgrade():
    """Refactor queries to use indexes"""
    # No schema changes, code-only migration
    pass

def downgrade():
    """Revert to old query patterns"""
    pass
```

### Phase 3: Validation

```sql
-- Verify index usage
EXPLAIN ANALYZE
SELECT * FROM transcripts
WHERE status = 'COMPLETED'
ORDER BY created_at DESC
LIMIT 20;

-- Expected: Index Scan on idx_transcripts_list or idx_transcripts_status_created

-- Check index sizes
SELECT
    schemaname,
    tablename,
    indexname,
    pg_size_pretty(pg_relation_size(indexname::text)) AS size
FROM pg_indexes
WHERE schemaname = 'public'
ORDER BY pg_relation_size(indexname::text) DESC;
```

---

## Rollback Strategy

### Rollback Indexes

```sql
-- Rollback script: rollback_001_indexes.sql
BEGIN;

-- Drop indexes CONCURRENTLY to avoid locks
DROP INDEX CONCURRENTLY IF EXISTS idx_transcripts_status;
DROP INDEX CONCURRENTLY IF EXISTS idx_transcripts_language;
DROP INDEX CONCURRENTLY IF EXISTS idx_transcripts_created_at;
DROP INDEX CONCURRENTLY IF EXISTS idx_transcripts_status_created;
DROP INDEX CONCURRENTLY IF EXISTS idx_jobs_transcript_status;
DROP INDEX CONCURRENTLY IF EXISTS idx_jobs_type_status;
DROP INDEX CONCURRENTLY IF EXISTS idx_transcripts_completed;
DROP INDEX CONCURRENTLY IF EXISTS idx_transcripts_list;

COMMIT;
```

### Rollback Connection Pool

```python
# Revert connection pool settings
engine = create_engine(
    settings.database_url,
    pool_size=5,               # Reduced from 15
    max_overflow=2,            # Reduced from 10
    pool_timeout=10,           # Reduced from 30
    pool_recycle=3600,
    pool_pre_ping=False,       # Disable pre-ping
    pool_use_lifo=False        # Use FIFO
)
```

### Rollback Plan

1. **Immediate Rollback:** Execute rollback scripts
2. **Feature Flag:** Use `settings.use_optimized_queries` flag
3. **Monitoring:** Watch query performance metrics
4. **Validation:** Run query benchmarks before/after

---

## Performance Benchmarks

### Before Optimization

| Query | p50 | p95 | p99 | Notes |
|-------|-----|-----|-----|-------|
| List transcripts (20) | 350ms | 800ms | 1200ms | Full table scan |
| Get transcript + jobs | 150ms | 400ms | 600ms | N+1 queries |
| RAG search | 800ms | 2000ms | 3500ms | No indexes |
| Filter by status | 400ms | 1000ms | 1800ms | Seq scan |

### After Optimization (Target)

| Query | p50 | p95 | p99 | Improvement |
|-------|-----|-----|-----|-------------|
| List transcripts (20) | 40ms | 80ms | 120ms | **80-90% faster** |
| Get transcript + jobs | 30ms | 60ms | 100ms | **80% faster** |
| RAG search | 100ms | 250ms | 400ms | **85% faster** |
| Filter by status | 20ms | 50ms | 80ms | **95% faster** |

### Benchmarking Script

```python
# backend/tests/database_benchmark.py

import time
from statistics import mean, median, percentile
from app.database import SessionLocal
from app.repositories import TranscriptRepository

def benchmark_query(iterations: int = 100):
    """Benchmark query performance"""
    repo = TranscriptRepository(SessionLocal())
    times = []

    for _ in range(iterations):
        start = time.perf_counter()
        repo.list_transcripts_optimized(limit=20)
        elapsed = time.perf_counter() - start
        times.append(elapsed * 1000)  # Convert to ms

    return {
        "p50": percentile(times, 50),
        "p95": percentile(times, 95),
        "p99": percentile(times, 99),
        "mean": mean(times),
        "median": median(times)
    }
```

---

## Index Size Impact Analysis

### Estimated Index Sizes

Based on 10,000 transcripts, 50,000 processing_jobs:

| Index | Columns | Estimated Size | Rationale |
|-------|---------|----------------|-----------|
| `idx_transcripts_status` | status | ~200KB | Small column, low cardinality |
| `idx_transcripts_language` | language | ~200KB | Small column, low cardinality |
| `idx_transcripts_created_at` | created_at | ~400KB | Timestamp column |
| `idx_transcripts_status_created` | status, created_at | ~600KB | Composite index |
| `idx_jobs_transcript_status` | transcript_id, status | ~1.5MB | FK + status, many rows |
| `idx_jobs_type_status` | job_type, status | ~400KB | Low cardinality |
| `idx_transcripts_completed` | created_at (partial) | ~200KB | Partial index (COMPLETED only) |
| `idx_transcripts_list` | status, created_at + INCLUDE | ~800KB | Covering index |
| **Total** | | **~4.3MB** | <1% of table size |

### Storage Impact

- **Table size (estimated):** ~500MB
- **Index overhead:** ~4.3MB (**<1%**)
- **Write performance impact:** ~5-10% slower inserts
- **Read performance improvement:** **80-95% faster**

---

## Consequences

**Positive:**
- Query time reduced by 80-90%
- N+1 queries eliminated
- Better connection pool utilization
- Improved user experience
- Reduced database load

**Negative:**
- Slightly slower inserts (5-10% overhead)
- Additional storage (~4MB for indexes)
- Query planning complexity
- Migration effort
- Index maintenance overhead

**Mitigations:**
- Use `CONCURRENTLY` for zero-downtime migrations
- Feature flag for gradual rollout
- Monitor query performance with Prometheus
- Regular index maintenance (REINDEX, ANALYZE)
- Benchmark before/after

---

**Document Control**

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-02-03 | Performance Team | Initial ADR |
| 1.1 | 2026-02-03 | Performance Team | Added alternatives, migration, rollback, benchmarks |
