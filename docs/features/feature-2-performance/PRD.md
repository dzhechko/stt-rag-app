# PRD: Feature 2 - Performance Optimizations

**Version:** 1.1
**Status:** Draft
**Author:** Performance Team
**Last Updated:** 2026-02-03

---

## Executive Summary

This PRD outlines comprehensive performance optimizations for the STT (Speech-to-Text) application to achieve 2-5x processing speedup through intelligent caching, parallel processing, connection pooling, async job queuing, and database optimization. The system currently processes large files (>50MB) sequentially with ~12-15 second latency per chunk to Cloud.ru API, creating significant bottlenecks.

**Target Performance Improvements:**
- **Overall Speedup:** 2-5x faster processing
- **API Latency Reduction:** 40-60% via parallel processing
- **Cache Hit Rate:** >70% for repeated content
- **Throughput:** 3-5x concurrent job capacity
- **Memory Efficiency:** 30-50% reduction in peak usage

---

## Problem Statement

### Current State
The STT application experiences significant performance limitations:

1. **Sequential Processing**: Large files split into chunks are processed one-by-one
2. **API Latency**: 12-15 seconds per Cloud.ru API call per chunk
3. **No Caching**: Repeated transcriptions of identical content waste API calls
4. **Connection Overhead**: New HTTP connections for each request
5. **Blocking Operations**: Background tasks use simple threading, not true async queues
6. **Database Queries**: N+1 queries and missing indexes slow down operations
7. **Frontend Bundle**: No code splitting causes slow initial loads

### Impact
- 100MB file with 4 chunks: 48-60 seconds processing time
- No reuse of previous transcriptions
- Limited concurrent processing capacity
- Poor user experience for large files

---

## Solution Overview

Implement an 8-pillar performance optimization strategy:

1. **Dynamic Chunk Size Optimization** - Smart sizing based on file characteristics
2. **Parallel Chunk Processing** - Concurrent API calls with controlled concurrency
3. **Multi-Level Caching** - Transcription and embedding caching
4. **HTTP/2 Connection Pooling** - Persistent connections with httpx
5. **Async Job Queue** - Celery + Redis for background processing
6. **Database Optimization** - Indexes, query optimization, connection pooling
7. **Frontend Optimization** - Lazy loading, code splitting, CDN
8. **CDN for Static Assets** - Serve audio files via CDN

---

## Performance Targets

### Primary Metrics

| Metric | Current | Target | Improvement |
|--------|---------|--------|-------------|
| 100MB File Processing | 48-60s | 12-24s | 2-5x |
| API Latency (per chunk) | 12-15s | 5-8s | 40-60% |
| Cache Hit Rate | 0% | >70% | New |
| Concurrent Jobs | 1-2 | 5-10 | 5x |
| Memory Peak (per job) | ~500MB | <350MB | 30% |
| Frontend Initial Load | ~3MB | <500KB | 6x |

### Secondary Metrics

| Metric | Target |
|--------|--------|
| Database Query Time (p95) | <100ms |
| API Response Time (p95) | <200ms |
| Frontend TTI (Time to Interactive) | <3s |
| CDN Cache Hit Rate | >90% |

---

## Functional Requirements

### FR-1: Dynamic Chunk Size Optimization

**Description:** System shall automatically determine optimal chunk size based on file characteristics.

**Requirements:**
- FR-1.1: Analyze audio duration and bitrate before splitting
- FR-1.2: Calculate optimal chunk size (10-30MB range) based on:
  - File size (larger files = larger chunks)
  - Audio quality (higher bitrate = larger chunks)
  - Language complexity (some languages need more context)
- FR-1.3: Adjust chunk size dynamically if API errors occur
- FR-1.4: Respect Cloud.ru API limits (25MB max)
- FR-1.5: Log chunk size decisions for optimization analysis

**Acceptance Criteria:**
- System automatically selects optimal chunk size without manual configuration
- Processing time reduced by 15-25% through optimal sizing
- No API errors due to oversized chunks

### FR-2: Parallel Chunk Processing

**Description:** System shall process multiple chunks concurrently with controlled parallelism.

**Requirements:**
- FR-2.1: Process up to 4 concurrent chunks (configurable)
- FR-2.2: Implement exponential backoff on API failures
- FR-2.3: Merge results maintaining timestamp order
- FR-2.4: Track progress for each chunk independently
- FR-2.5: Handle partial failures gracefully (reprocess failed chunks only)
- FR-2.6: Respect API rate limits

**Acceptance Criteria:**
- 4-chunk file processed in 15-20s (vs 48-60s)
- Progress updates show per-chunk status
- Failed chunks automatically retried up to 3 times

### FR-3: Multi-Level Caching Strategy

**Description:** System shall cache transcription results and embeddings to avoid redundant processing.

**Requirements:**
- FR-3.1: **Content-Addressed Cache** - Cache by file hash (SHA-256)
- FR-3.2: **Cache Levels:**
  - L1: In-memory (transient, same-session results)
  - L2: Redis (persistent, 24-hour TTL)
  - L3: PostgreSQL (permanent, user-specific)
- FR-3.3: **Cache Keys:**
  - Transcription: `transcript:{file_hash}:{language}`
  - Embeddings: `embeddings:{chunk_hash}`
  - Summaries: `summary:{transcript_hash}:{template}`
- FR-3.4: Cache invalidation on explicit user request
- FR-3.5: Cache statistics dashboard
- FR-3.6: Warm cache for frequently accessed files

**Acceptance Criteria:**
- >70% cache hit rate for repeated uploads
- Sub-100ms response for cached transcriptions
- Cache uses <5GB storage for 10,000 transcriptions

### FR-4: HTTP/2 Connection Pooling

**Description:** System shall maintain persistent HTTP/2 connections to Cloud.ru API.

**Requirements:**
- FR-4.1: Use httpx with HTTP/2 support
- FR-4.2: Maintain connection pool (max 10 connections)
- FR-4.3: Keep-alive connections (30 second timeout)
- FR-4.4: Implement connection retry logic
- FR-4.5: Monitor connection pool metrics

**Acceptance Criteria:**
- Connection establishment time reduced by 80%
- No connection leaks under load
- Support 10+ concurrent requests on single connection

### FR-5: Async Job Queue (Celery + Redis)

**Description:** System shall use Celery with Redis broker for true async background processing.

**Requirements:**
- FR-5.1: **Job Types:**
  - Transcription (high priority)
  - Summarization (medium priority)
  - Translation (medium priority)
  - RAG Indexing (low priority)
- FR-5.2: **Worker Configuration:**
  - 4-8 worker processes
  - Prefetch multiplier: 1 (prevent hoarding)
  - Task time limit: 3600s
- FR-5.3: **Queue Configuration:**
  - Separate queues per priority level
  - Result backend: Redis
  - Task serialization: JSON
- FR-5.4: **Monitoring:**
  - Flower dashboard for job monitoring
  - Task status tracking
  - Worker health monitoring
- FR-5.5: **Retry Strategy:**
  - Max retries: 3
  - Exponential backoff
  - Dead letter queue for failed tasks

**Acceptance Criteria:**
- 5-10 concurrent jobs processed smoothly
- Job status visible via Flower dashboard
- Automatic retry on transient failures
- No lost jobs on worker restart

### FR-6: Database Optimization

**Description:** System shall optimize database queries and schema.

**Requirements:**
- FR-6.1: **Add Indexes:**
  - `transcripts.status`, `transcripts.language`, `transcripts.created_at`
  - `processing_jobs.transcript_id`, `processing_jobs.status`
  - `processing_jobs.job_type`, `processing_jobs.created_at`
- FR-6.2: **Connection Pooling:**
  - SQLAlchemy pool: 5-20 connections
  - Pool recycle: 3600s
  - Pool pre-ping: true
- FR-6.3: **Query Optimization:**
  - Eliminate N+1 queries with eager loading
  - Use `select_in` loading strategy
  - Add pagination for large result sets
- FR-6.4: **Schema Optimization:**
  - JSONB fields for metadata
  - Partial indexes for filtered queries
  - Covering indexes for common queries

**Acceptance Criteria:**
- Query time (p95) <100ms
- No N+1 queries in list endpoints
- Connection pool handles 20 concurrent requests

### FR-7: Frontend Optimization

**Description:** Frontend shall implement lazy loading and code splitting.

**Requirements:**
- FR-7.1: **Code Splitting:**
  - Route-based splitting (TranscriptDetail, RAG, etc.)
  - Vendor chunk splitting (React, etc.)
  - Dynamic imports for heavy components
- FR-7.2: **Lazy Loading:**
  - Audio player lazy loads
  - RAG components lazy loads
  - Large transcript pages virtualize
- FR-7.3: **Bundle Optimization:**
  - Initial bundle <500KB (compressed, <1.5MB uncompressed)
  - Brotli (Level 5): Target 70% reduction
  - Gzip fallback: Target 60% reduction
  - Tree shaking enabled
  - Verified via: gzip -9, brotli -q 5
- FR-7.4: **Bundle Composition:**
  - Initial bundle (<500KB compressed) includes:
    - Core React libraries
    - Router
    - Authentication module
    - Basic UI components
  - Lazy loaded bundles:
    - TranscriptDetail (~200KB)
    - RAG interface (~300KB)
    - Admin dashboard (~250KB)
- FR-7.5: **Code Splitting Strategy:**
  - Route-based: /transcripts, /rag, /admin
  - Vendor split: React, DOM utilities
  - Dynamic imports: Heavy components (audio player, charts)
- FR-7.6: **Asset Optimization:**
  - WebP images with fallback
  - Minified CSS/JS
  - Source maps for production
- FR-7.7: **Network Baselines:**
  - Desktop: 25 Mbps down, 5 Mbps up (WiFi)
  - Mobile: 4G (10 Mbps down, 5 Mbps up)
  - Test throttling: Chrome DevTools Network presets
- FR-7.8: **Lighthouse Targets:**
  - Performance: >90
  - Accessibility: >85
  - Best Practices: >90
  - SEO: >85 (if applicable)
  - Tested on: Chrome Desktop, Mobile Emulation (iPhone 12)

**Acceptance Criteria:**
- Initial load <500KB (compressed, <1.5MB uncompressed)
- Time to Interactive <3s on desktop WiFi, <5s on mobile 4G
- First Contentful Paint <1.5s on desktop
- Lighthouse Performance score >90 (Desktop and Mobile)
- Lighthouse Accessibility score >85
- Lighthouse Best Practices score >90

**Test Scenarios:**
```gherkin
Scenario: Initial load on desktop WiFi
  Given user on Chrome Desktop with 25 Mbps WiFi
  When navigating to app root
  Then Initial bundle <500KB (compressed)
  And Time to Interactive <3 seconds
  And First Contentful Paint <1.5s
  Measured via Lighthouse with 4x CPU throttling

Scenario: Route-based lazy load
  Given user on app homepage
  When clicking "Transcripts" navigation
  Then lazy-loaded transcript bundle fetched
  And route transition <500ms after bundle cached
  Measured via Chrome DevTools Network panel

Scenario: Mobile 4G performance
  Given user on mobile device with 4G connection (10 Mbps)
  When accessing app for first time
  Then Time to Interactive <5 seconds
  And Lighthouse Performance score >85 on Mobile Emulation
```

### FR-8: CDN for Static Assets

**Description:** System shall serve audio files via CDN.

**Requirements:**
- FR-8.1: **CDN Provider Specification:**
  - Primary: Cloudflare R2 (S3-compatible)
  - Edge locations: 200+ globally
  - Max file size: 5GB (sufficient for audio)
  - Upload processed audio to CDN via S3-compatible API
- FR-8.2: **Cost Structure:**
  - Storage: $0.015/GB/month (vs S3 $0.023)
  - Egress: Free (vs S3 $0.09/GB)
  - Cost estimates (1000 transcriptions/month, avg 50MB):
    - Storage: 50GB * $0.015 = $0.75/month
    - Egress: 1000 * 50MB * $0 = $0 (Cloudflare R2)
    - Total: <$1/month for 1000 transcriptions
- FR-8.3: **Cache Strategy:**
  - Serve transcriptions and audio files from CDN edge
  - TTL: 365 days for immutable audio
  - Cache-Control: public, max-age=31536000, immutable
  - Invalidation: DELETE request on file deletion
  - Purge propagation: <30 seconds globally
- FR-8.4: **Cache Hit Rate Targets:**
  - Hourly: >85% (after initial warmup)
  - Daily: >90%
  - Weekly: >95%
  - Measured via Cloudflare Analytics
- FR-8.5: **Latency Targets (p95):**
  - Same continent: <50ms
  - Cross-continent: <100ms
  - Asia-Pacific: <150ms
  - Measured from 5 regions: US-East, US-West, EU-West, EU-Central, Asia-Pacific
- FR-8.6: **Fallback Behavior:**
  - If CDN unavailable: Serve from local storage (PostgreSQL)
  - Fallback timeout: 2 seconds
  - Fallback triggers: 503 error, timeout >5s
  - Automatic retry after 60 seconds
- FR-8.7: **CDN Purge:**
  - Automatic CDN purge on file deletion
  - Invalidation API integration
  - Purge verification logging

**Acceptance Criteria:**
- >90% CDN cache hit rate (daily, after initial warmup)
- Audio files served <100ms globally (p95, cross-continent)
- <50ms same continent (p95)
- Automatic CDN purge on delete within 30 seconds
- Fallback to local storage within 2 seconds if CDN unavailable

**Test Scenarios:**
```gherkin
Scenario: CDN cache hit from US-East
  Given audio file "test.mp3" uploaded and stored in CDN
  When user requests file from US-East region
  Then response returned in <50ms (p95)
  And X-Cache: HIT header present
  And served from Cloudflare edge

Scenario: CDN fallback on failure
  Given CDN service unavailable (503 error)
  When user requests audio file
  Then request times out after 2 seconds
  And automatic fallback to PostgreSQL storage
  And user sees "Degraded performance" notification
  And CDN retry attempted after 60 seconds

Scenario: CDN purge on deletion
  Given audio file stored in CDN
  When user deletes file
  Then CDN PURGE request sent
  And file inaccessible from all edges within 30 seconds
  And database record deleted

Scenario: Geographic latency validation
  Given audio file "test.mp3" stored in CDN
  When user requests file from 5 geographic regions
  Then US-East latency <50ms (p95)
  And US-West latency <50ms (p95)
  And EU-West latency <50ms (p95)
  And EU-Central latency <50ms (p95)
  And Asia-Pacific latency <150ms (p95)
```

### FR-9: Performance Monitoring

**Description:** System shall monitor performance metrics.

**Requirements:**
- FR-9.1: Track processing times per operation
- FR-9.2: Monitor cache hit/miss ratios
- FR-9.3: Alert on performance degradation
- FR-9.4: Dashboard for performance metrics
- FR-9.5: Export metrics for analysis

**Acceptance Criteria:**
- All critical metrics tracked
- Alerts fire within 1 minute of degradation
- Dashboard accessible via `/api/metrics`

### FR-10: Graceful Degradation

**Description:** System shall degrade gracefully if optimizations fail.

**Requirements:**
- FR-10.1: **Minimum Viable Functionality:**
  - MANDATORY (always available):
    - File upload (sequential processing)
    - Transcription results display
    - User authentication
    - Basic navigation
  - DEGRADED (reduced performance):
    - Progress updates: polling every 30s (no WebSocket)
    - Concurrent uploads: max 1 (vs 5)
    - Caching: bypassed (direct API calls)
    - Search: basic only (no RAG)
  - UNAVAILABLE (admin can disable):
    - Real-time progress
    - Batch processing
    - RAG queries
    - Advanced search
- FR-10.2: **Fallback Mechanisms:**
  - Fallback to sequential processing if parallel fails
  - Bypass cache if cache unavailable
  - Use direct DB if Redis unavailable
- FR-10.3: **Notification Specification:**
  - In-app banner: "Performance mode: Some features unavailable"
  - Color: Yellow (warning), not red (error)
  - Dismissible: Yes, with "Don't show again for 1 hour"
  - Persistence: Session storage (reset on refresh)
  - Detail: "Learn more" link to status page
  - Clear error messages for degradation
- FR-10.4: **Recovery Triggers:**
  - Health check: Every 30 seconds
  - Recovery criteria: All systems healthy for 2 minutes
  - Recovery notification: "Full performance restored"
  - Auto-retry: Queued jobs process automatically
- FR-10.5: **State Persistence:**
  - In-flight jobs: Continue to completion
  - Failed jobs: Retry after recovery (max 3 attempts)
  - User preferences: Persisted to localStorage
  - Draft transcripts: Auto-save to database
- FR-10.6: **Manual Override:**
  - Admin endpoint: POST /admin/degradation/override
  - Parameters: {"mode": "full" | "degraded", "reason": "string"}
  - Audit log: All overrides logged with user/timestamp
  - Auto-recovery disabled: When manual override active
- FR-10.7: **Degraded Mode Performance Targets:**
  - Sequential processing: 2-3x slower than normal
  - API latency: +50% (account for single-threading)
  - Cache bypass: All calls to external API
  - Queue: Disabled (synchronous processing)

**Acceptance Criteria:**
- System remains functional during cache/queue failures
- User informed of degraded mode via in-app banner
- Automatic recovery when services restored (2-minute health window)
- Manual override capability for admins
- Degraded mode performance within 2-3x of normal

**Test Scenarios:**
```gherkin
Scenario: Redis cache failure - degrade gracefully
  Given Redis service unavailable (connection refused)
  When user uploads file for transcription
  Then cache bypassed
  And notification displayed: "Cache unavailable, using direct processing"
  And transcription completes (slower, no error)
  And cache health check every 30s
  When Redis recovers
  Then notification: "Full performance restored"
  And cache re-enabled for new uploads

Scenario: Manual degradation override
  Given all systems operational
  When admin POSTs to /admin/degradation/override
  And body: {"mode": "degraded", "reason": "Emergency maintenance"}
  Then system enters degraded mode
  And users see: "Scheduled maintenance: Some features unavailable"
  And cache disabled
  And queue processing paused
  And override logged to audit trail
  And auto-recovery disabled

Scenario: Celery queue failure - sequential processing
  Given Celery workers unavailable
  When user uploads file for transcription
  Then sequential processing activated
  And notification: "Processing in sequential mode - may be slower"
  And file processes successfully (2-3x slower)
  And progress updates via polling (every 30s)
  When Celery workers recover
  Then automatic recovery after 2-minute health window
  And notification: "Full performance restored"
```

---

## Non-Functional Requirements

### NFR-1: Performance

| Requirement | Metric | Target |
|-------------|--------|--------|
| Processing Throughput | Files/hour | 20+ (100MB files) |
| API Latency (p95) | Response time | <200ms |
| Cache Lookup (p99) | Time | <50ms |
| Database Query (p95) | Time | <100ms |
| Concurrent Users | Active users | 50+ |

### NFR-2: Scalability

| Requirement | Metric | Target |
|-------------|--------|--------|
| Horizontal Scaling | Workers | 1-20 workers |
| Vertical Scaling | Memory | <2GB per worker |
| Queue Throughput | Jobs/hour | 100+ |
| Database Connections | Pool size | 20-50 |

### NFR-3: Reliability

| Requirement | Metric | Target |
|-------------|--------|--------|
| Job Success Rate | Completed jobs | >99% |
| Retry Success Rate | After retry | >95% |
| System Availability | Uptime | >99.5% |
| Data Loss | Lost jobs | 0 |

### NFR-4: Resource Efficiency

| Requirement | Metric | Target |
|-------------|--------|--------|
| Memory Per Job | Peak usage | <500MB |
| CPU Per Worker | Utilization | <80% |
| Storage Growth | Per transcript | <10MB |
| Network | API calls | -40% with cache |

### NFR-5: Observability

| Requirement | Metric | Target |
|-------------|----------------|
| Metrics Collection | Coverage | 100% of operations |
| Log Retention | Time | 30 days |
| Alert Latency | Detection | <1 minute |
| Dashboard Refresh | Rate | 10 seconds |

---

## User Stories

### Epic 1: Faster Processing

**US-1: As a user, I want large files to process quickly so I don't have to wait long**
- **Priority:** High
- **Acceptance:** 100MB file completes in <30 seconds

**US-2: As a user, I want to see real-time progress so I know when processing will complete**
- **Priority:** Medium
- **Acceptance:** Progress bar updates every chunk

**US-3: As a user, I want to upload multiple files concurrently so I can process batches**
- **Priority:** Medium
- **Acceptance:** 5 files process simultaneously

### Epic 2: Reduce Redundancy

**US-4: As a user, I want re-uploaded files to use cached results**
- **Priority:** High
- **Acceptance:** Same file returns cached result in <1 second

**US-5: As an admin, I want to see cache statistics so I can monitor efficiency**
- **Priority:** Low
- **Acceptance:** Dashboard shows hit rate, size, keys

### Epic 3: Better UX

**US-6: As a user, I want the app to load quickly so I can start working immediately**
- **Priority:** High
- **Acceptance:** Initial load <3 seconds

**US-7: As a user, I want audio files to load from CDN so they play smoothly**
- **Priority:** Medium
- **Acceptance:** Audio starts in <500ms

### Epic 4: Monitoring

**US-8: As a dev, I want to see job queue status so I can troubleshoot issues**
- **Priority:** Low
- **Acceptance:** Flower dashboard accessible

**US-9: As a dev, I want performance alerts so I can fix degradations**
- **Priority:** Low
- **Acceptance:** Alerts on >2x slowdown

---

## Technical Architecture

### High-Level Components

```
┌─────────────────────────────────────────────────────────────────┐
│                         Frontend (React)                        │
│  Code Splitting | Lazy Loading | CDN Assets | Virtual Scrolling │
└────────────────────────────┬────────────────────────────────────┘
                             │ HTTP/WebSocket
┌────────────────────────────┴────────────────────────────────────┐
│                      FastAPI Backend                            │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │              API Layer (CORS, Validation)                │  │
│  └──────────────────────┬───────────────────────────────────┘  │
│  ┌──────────────────────┴───────────────────────────────────┐  │
│  │              Service Layer (Business Logic)              │  │
│  │  Transcription | Summarization | RAG | Translation       │  │
│  └──────────────────────┬───────────────────────────────────┘  │
│  ┌──────────────────────┴───────────────────────────────────┐  │
│  │              Cache Layer (Multi-Level)                   │  │
│  │  L1: Memory | L2: Redis | L3: PostgreSQL                │  │
│  └──────────────────────┬───────────────────────────────────┘  │
│  ┌──────────────────────┴───────────────────────────────────┐  │
│  │              Queue Layer (Celery)                        │  │
│  │  High | Medium | Low Priority Queues                     │  │
│  └──────────────────────┬───────────────────────────────────┘  │
└─────────────────────────┼───────────────────────────────────────┘
                          │
        ┌─────────────────┼─────────────────┐
        │                 │                 │
┌───────▼────────┐ ┌─────▼──────┐ ┌───────▼────────┐
│  PostgreSQL    │ │   Redis    │ │  Cloud.ru API  │
│  (Data)        │ │  (Cache)   │ │  (STT/LLM)     │
│                │ │            │ │  HTTP/2 Pool   │
└────────────────┘ └────────────┘ └────────────────┘
```

---

## Dependencies

### External Services

| Service | Purpose | Criticality |
|---------|---------|-------------|
| Cloud.ru API | STT processing | Critical |
| Redis | Cache + Queue | Critical |
| PostgreSQL | Data storage | Critical |
| Celery | Job queue | Critical |
| Flower | Job monitoring | Optional |
| CDN (R2/S3) | Asset serving | Optional |

### Internal Services

| Service | Dependency |
|---------|------------|
| Transcription | Cache, Queue |
| Summarization | Transcription, Queue |
| RAG | Transcription, Embeddings |
| Translation | Transcription, Queue |

---

## Implementation Phases

### Phase 1: Quick Wins (Week 1-2)
- FR-4: Connection pooling with httpx
- FR-6.1: Add database indexes
- FR-7.1: Basic code splitting

**Expected Impact:** 20-30% speedup

### Phase 2: Parallel Processing (Week 3-4)
- FR-1: Dynamic chunk sizing
- FR-2: Parallel chunk processing
- FR-9: Performance monitoring

**Expected Impact:** 2-3x speedup for large files

### Phase 3: Caching Layer (Week 5-6)
- FR-3: Multi-level caching
- FR-10: Graceful degradation

**Expected Impact:** >70% cache hit rate for repeats

### Phase 4: Job Queue (Week 7-8)
- FR-5: Celery + Redis implementation
- FR-5.4: Flower monitoring

**Expected Impact:** 5-10x concurrent capacity

### Phase 5: Frontend + CDN (Week 9-10)
- FR-7: Complete frontend optimization
- FR-8: CDN integration

**Expected Impact:** 6x faster initial load

---

## Testing Strategy

### Performance Tests

```gherkin
Feature: Parallel Chunk Processing
  Scenario: Process 4 chunks in parallel
    Given a 100MB audio file
    When the file is uploaded for transcription
    Then processing should complete within 20 seconds
    And all 4 chunks should be processed
    And results should be merged correctly

Feature: Caching
  Scenario: Cache hit on repeated upload
    Given a file was previously transcribed
    When the same file is uploaded again
    Then response should be returned within 1 second
    And cache hit should be recorded

Feature: Concurrent Jobs
  Scenario: Process 5 files simultaneously
    Given 5 audio files are uploaded
    When all files are processed
    Then each file should process within expected time
    And no jobs should fail
```

### Load Tests

- **Normal Load:** 5 concurrent users, 100MB files
- **Peak Load:** 20 concurrent users, mix of file sizes
- **Stress Test:** 50 concurrent users, sustained for 1 hour

---

## Success Metrics

### Phase 1 Success Criteria
- [ ] Connection pooling reduces latency by 20%
- [ ] Database queries (p95) <100ms
- [ ] Initial bundle size <1MB

### Phase 2 Success Criteria
- [ ] 100MB file processes in <30s
- [ ] Parallel chunks process without errors
- [ ] Progress tracking accurate

### Phase 3 Success Criteria
- [ ] Cache hit rate >70%
- [ ] Cache lookup <50ms
- [ ] Storage growth <10GB for 10K transcripts

### Phase 4 Success Criteria
- [ ] 5-10 concurrent jobs processed
- [ ] Flower dashboard operational
- [ ] Job retry success rate >95%

### Phase 5 Success Criteria
- [ ] Initial load <3s
- [ ] CDN cache hit >90%
- [ ] Lighthouse score >90

---

## Risks and Mitigations

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| API rate limiting | Medium | High | Implement exponential backoff |
| Cache stamping | Low | Medium | Rate limit cache keys |
| Worker memory leaks | Low | High | Monitor memory, restart workers |
| CDN costs | Medium | Medium | Cache optimization, lifecycle rules |
| Celery complexity | Medium | Medium | Thorough testing, monitoring |

---

## Open Questions

1. **Celery Workers:** How many workers for initial deployment?
   - **Recommendation:** Start with 4, scale based on metrics

2. **Cache TTL:** What TTL for Redis cache?
   - **Recommendation:** 24 hours for transcripts, 7 days for embeddings

3. **CDN Provider:** Which CDN to use?
   - **Recommendation:** Cloudflare R2 for S3-compatible, cost-effective

4. **Monitoring:** What metrics to track?
   - **Recommendation:** See FR-9 for full list

---

## Appendix

### A. Performance Benchmarks

#### Baseline (Current)
- 25MB file: 15 seconds
- 50MB file: 30 seconds (2 chunks)
- 100MB file: 60 seconds (4 chunks)
- 200MB file: 120 seconds (8 chunks)

#### Target (After Optimization)
- 25MB file: 5 seconds (cached)
- 50MB file: 8 seconds (2 parallel chunks)
- 100MB file: 15 seconds (4 parallel chunks)
- 200MB file: 30 seconds (8 parallel chunks)

### B. Configuration Examples

```python
# Celery Configuration
CELERY_CONFIG = {
    "broker_url": "redis://redis:6379/0",
    "result_backend": "redis://redis:6379/1",
    "task_routes": {
        "app.tasks.transcribe": {"queue": "high"},
        "app.tasks.summarize": {"queue": "medium"},
        "app.tasks.index_rag": {"queue": "low"},
    },
    "worker_prefetch_multiplier": 1,
    "task_acks_late": True,
    "task_time_limit": 3600,
}

# Connection Pool Configuration
HTTP_CONFIG = {
    "limits": httpx.Limits(
        max_keepalive_connections=10,
        max_connections=20,
        keepalive_expiry=30
    ),
    "timeout": httpx.Timeout(120.0, connect=30.0),
    "http2": True,
}
```

### C. Monitoring Dashboard Metrics

- Processing time (p50, p95, p99)
- Cache hit rate
- Queue depth
- Worker utilization
- Memory usage
- API error rate
- Database query time

---

**Document Control**

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.1 | 2026-02-03 | Performance Team | Critical PRD updates based on validation analysis (FR-7, FR-8, FR-10) |
| 1.0 | 2026-02-03 | Performance Team | Initial PRD |
