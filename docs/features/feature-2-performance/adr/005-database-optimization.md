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

## Consequences

**Positive:**
- Query time reduced by 80-90%
- N+1 queries eliminated
- Better connection pool utilization

**Negative:**
- Slightly slower inserts (index maintenance)
- More storage for indexes
- Query planning complexity

---

**Document Control**

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-02-03 | Performance Team | Initial ADR |
