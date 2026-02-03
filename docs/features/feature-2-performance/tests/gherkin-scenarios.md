# Gherkin Scenarios - Performance Tests

**Feature:** Performance Optimizations
**Version:** 1.0
**Date:** 2026-02-03

---

## Feature: Parallel Chunk Processing

### Scenario: Process 4 chunks in parallel

```gherkin
Feature: Parallel Chunk Processing
  As a user
  I want large files to be processed in parallel
  So that I don't have to wait long for results

  Scenario: Process 100MB file with 4 chunks in parallel
    Given a 100MB audio file
    And the file is split into 4 chunks
    And the concurrency limit is set to 4
    When the file is submitted for transcription
    Then processing should start for all 4 chunks within 1 second
    And all 4 chunks should be processed concurrently
    And processing should complete within 30 seconds
    And the results should be merged in correct order
    And the final transcript should contain all chunk text

  Scenario: Process 4 chunks with cache hits
    Given a 100MB audio file
    And the file was previously transcribed
    And the transcription is cached
    When the file is submitted for transcription again
    Then the response should be returned within 1 second
    And all chunks should be served from cache
    And no API calls should be made

  Scenario: Graceful degradation when API fails
    Given a 100MB audio file
    And the file is split into 4 chunks
    And chunk 2 fails with a transient error
    When the file is submitted for transcription
    Then chunk 2 should be retried up to 3 times
    And if all retries fail, the transcript should be marked as partial
    And the partial result should include successful chunks 0, 1, 3
    And an error message should indicate which chunk failed

  Scenario: Respect concurrency limit
    Given 3 files submitted simultaneously
    And each file has 4 chunks
    And the concurrency limit is 4
    When all files are processed
    Then no more than 4 chunks should be processed concurrently
    And each file should complete successfully
    And the total time should be approximately 3x single file time
```

---

## Feature: Multi-Level Caching

### Scenario: Cache lookup across levels

```gherkin
Feature: Multi-Level Caching
  As a system
  I want to store results in multiple cache levels
  So that frequently accessed data is retrieved quickly

  Scenario: Cache hit in L1 (Memory)
    Given a transcript was recently accessed
    And the transcript is cached in L1 memory
    When the transcript is requested again
    Then the response should be returned within 10ms
    And the cache should report "L1" as the source

  Scenario: Cache hit in L2 (Redis) after L1 miss
    Given a transcript was accessed 10 minutes ago
    And the transcript is not in L1 memory
    And the transcript is cached in L2 Redis
    When the transcript is requested
    Then the response should be returned within 100ms
    And the cache should report "L2" as the source
    And the transcript should be promoted to L1

  Scenario: Cache hit in L3 (PostgreSQL) after L1/L2 miss
    Given a transcript was accessed yesterday
    And the transcript is not in L1 or L2
    And the transcript is cached in L3 PostgreSQL
    When the transcript is requested
    Then the response should be returned within 500ms
    And the cache should report "L3" as the source
    And the transcript should be promoted to L2 and L1

  Scenario: Cache miss triggers API call
    Given a new transcript that has never been cached
    When the transcript is requested
    Then the API should be called
    And the result should be cached in L1, L2, and L3
    And subsequent requests should hit the cache

  Scenario: Cache invalidation cascades across levels
    Given a transcript is cached in L1, L2, and L3
    When the transcript is updated
    Then the cache entry should be removed from L1
    And the cache entry should be removed from L2
    And the cache entry should be removed from L3
    And the next request should fetch fresh data

  Scenario: TTL expiration
    Given a transcript with a 24-hour TTL
    And the transcript was cached 25 hours ago
    When the transcript is requested
    Then the cache should be considered expired
    And fresh data should be fetched
    And the TTL should be reset
```

---

## Feature: Connection Pooling

### Scenario: HTTP/2 connection reuse

```gherkin
Feature: HTTP/2 Connection Pooling
  As a system
  I want to reuse HTTP connections across requests
  So that connection overhead is minimized

  Scenario: First request establishes connection
    Given no existing HTTP connections
    When an API request is made
    Then a new HTTP/2 connection should be established
    And the connection should take approximately 200ms to establish
    And the request should use the new connection

  Scenario: Subsequent requests reuse connection
    Given an existing HTTP/2 connection
    When 4 API requests are made concurrently
    Then all requests should use the existing connection
    And no new connections should be established
    And requests should be multiplexed over HTTP/2

  Scenario: Connection pool limit respected
    Given a connection pool with max 10 connections
    When 15 concurrent requests are made
    Then 10 connections should be established
    And 5 requests should wait for available connections
    And all requests should complete successfully

  Scenario: Dead connection is replaced
    Given a connection that has been idle for 31 seconds
    When a new request is made
    Then the old connection should be closed
    And a new connection should be established
    And the request should complete successfully
```

---

## Feature: Celery Job Queue

### Scenario: Priority-based job execution

```gherkin
Feature: Celery Job Queue
  As a system
  I want to process jobs with different priorities
  So that important jobs are processed first

  Scenario: High priority job processed first
    Given 3 low priority jobs are queued
    When a high priority transcription job is submitted
    Then the high priority job should start processing before low priority jobs
    And the high priority job should complete first

  Scenario: Job retry with exponential backoff
    Given a job that fails with a transient error
    And the job has max_retries=3
    When the job is executed
    Then it should be retried after 1 second
    And if it fails again, retry after 2 seconds
    And if it fails again, retry after 4 seconds
    And after 3 retries, the job should be marked as failed

  Scenario: Job progress tracking
    Given a transcription job processing 4 chunks
    When the job is processing
    Then progress should be updated after each chunk
    And progress should be 25% after chunk 0
    And progress should be 50% after chunk 1
    And progress should be 75% after chunk 2
    And progress should be 100% after chunk 3

  Scenario: Worker health monitoring
    Given a Celery worker is running
    When the worker processes 10 jobs successfully
    Then the worker should be reported as healthy in Flower
    And the worker should show correct queue assignment
    And the worker should show current task count
```

---

## Feature: Database Optimization

### Scenario: Query performance with indexes

```gherkin
Feature: Database Optimization
  As a system
  I want database queries to be fast
  So that API response time is minimized

  Scenario: Index usage for status queries
    Given 10,000 transcripts in the database
    And an index on the status column
    When querying for transcripts with status="COMPLETED"
    Then the query should use the status index
    And the query should complete within 100ms
    And an EXPLAIN should show "Index Scan" not "Seq Scan"

  Scenario: N+1 query elimination with eager loading
    Given 100 transcripts with summaries
    When fetching all transcripts with summaries
    Then only 2 queries should be executed (1 for transcripts, 1 for summaries)
    And not 101 queries (N+1 problem)
    And the response should be returned within 500ms

  Scenario: Connection pool handles concurrent requests
    Given a database connection pool with max 20 connections
    When 50 concurrent requests query the database
    Then 20 connections should be active
    And 30 requests should wait for available connections
    And all requests should complete successfully
    And no connection timeout errors should occur

  Scenario: Pagination for large result sets
    Given 10,000 transcripts in the database
    When requesting page 1 with limit=20
    Then only 20 records should be returned
    And the query should use LIMIT and OFFSET
    And the response should be returned within 100ms
```

---

## Feature: Frontend Optimization

### Scenario: Code splitting and lazy loading

```gherkin
Feature: Frontend Optimization
  As a user
  I want the application to load quickly
  So that I can start using it immediately

  Scenario: Initial bundle is small
    Given the application uses code splitting
    When the application is loaded for the first time
    Then the initial JavaScript bundle should be less than 500KB
    And only critical code should be in the initial bundle
    And non-critical code should be split into separate chunks

  Scenario: Route-based code splitting
    Given the application has routes for /transcripts and /rag
    When navigating to /transcripts
    Then only the transcripts chunk should be loaded
    And the RAG chunk should not be loaded
    And navigating to /rag should load the RAG chunk on demand

  Scenario: Lazy loading of heavy components
    Given a transcript detail page with audio player
    When the page loads
    Then the audio player should not be in the initial bundle
    And the audio player should load when scrolled into view
    And the initial page load should be under 2 seconds

  Scenario: Tree shaking removes unused code
    Given the application imports lodash but only uses 2 functions
    When the production bundle is built
    Then only the 2 used functions should be included
    And unused lodash functions should be excluded
    And the bundle size should be minimized
```

---

## Feature: CDN for Static Assets

### Scenario: CDN delivery of audio files

```gherkin
Feature: CDN Static Assets
  As a user
  I want audio files to be served from edge locations
  So that playback starts quickly

  Scenario: Audio file served from CDN
    Given an audio file is uploaded to the CDN
    When a user requests the audio file
    Then the request should be served from the nearest CDN edge
    And the response should include a Cache-Control header
    And the response time should be under 100ms globally

  Scenario: CDN cache hit
    Given an audio file is cached on the CDN
    When multiple users request the same file
    Then the CDN cache hit rate should be above 90%
    And the origin server should not be contacted for cached files

  Scenario: CDN invalidation on file deletion
    Given an audio file is cached on the CDN
    When the file is deleted from the system
    Then the CDN should be purged of the file
    And subsequent requests should return 404

  Scenario: Fallback to origin when CDN unavailable
    Given the CDN is experiencing an outage
    When a user requests an audio file
    Then the request should fall back to the origin server
    And the user should still receive the file
    And an error should be logged for monitoring
```

---

## Feature: Performance Monitoring

### Scenario: Metrics collection

```gherkin
Feature: Performance Monitoring
  As an operator
  I want to track performance metrics
  So that I can identify and fix issues

  Scenario: Processing duration is tracked
    Given a file transcription completes
    Then the processing duration should be recorded
    And the duration should be categorized by file size
    And percentiles (p50, p95, p99) should be calculated

  Scenario: Cache hit rate is monitored
    Given 100 cache lookups occur
    And 70 of them hit the cache
    Then the cache hit rate should be reported as 70%
    And the metric should be labeled by cache level (L1, L2, L3)

  Scenario: Alert on performance degradation
    Given the average processing time increases by 2x
    When the degradation is detected
    Then an alert should be triggered
    And the alert should include the metric name and current value
    And the alert should be sent to configured channels

  Scenario: Dashboard displays real-time metrics
    Given the monitoring dashboard is open
    When viewing the performance dashboard
    Then the following should be displayed:
      | Processing duration chart |
      | Cache hit rate gauge |
      | Active workers count |
      | Queue depth by priority |
      | Error rate percentage |
    And metrics should update every 10 seconds
```

---

## Feature: Graceful Degradation

### Scenario: Fallback behavior

```gherkin
Feature: Graceful Degradation
  As a user
  I want the system to remain functional when components fail
  So that I can still use the application

  Scenario: Fallback to sequential when parallel fails
    Given parallel processing is enabled
    And a parallel processing error occurs
    When the error is detected
    Then the system should fall back to sequential processing
    And the user should be informed of degraded performance
    And the transcript should still be completed

  Scenario: Bypass cache when Redis unavailable
    Given the Redis cache is unavailable
    When a cached result is requested
    Then the system should bypass the cache
    And fetch data directly from the source
    And return the result successfully

  Scenario: Use direct DB when queue unavailable
    Given the Celery queue is unavailable
    When a job is submitted
    Then the job should be processed synchronously
    And the result should be returned to the user
    And an error should be logged

  Scenario: Partial results on chunk failure
    Given a file with 4 chunks
    And chunk 2 fails permanently
    When processing completes
    Then the transcript should be marked as partial
    And successful chunks (0, 1, 3) should be included
    And the user should be informed of the failure
```

---

## Test Data Setup

### Background: Common Setup

```gherkin
Background:
  Given the application is running
  And the database contains test data
  And Redis is available for caching
  And Celery workers are running
  And the Cloud.ru API is mocked
```

---

## Performance Benchmarks

### Expected Performance

| Metric | Target | Test Criteria |
|--------|--------|---------------|
| 100MB file processing | <30s | Complete within 30 seconds |
| Cache lookup (L1) | <10ms | Return within 10ms |
| Cache lookup (L2) | <100ms | Return within 100ms |
| API response (p95) | <200ms | 95% under 200ms |
| Database query (p95) | <100ms | 95% under 100ms |
| Frontend initial load | <3s | Interactive in 3 seconds |
| CDN cache hit rate | >90% | 90%+ hits for cached assets |

---

**Document Control**

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-02-03 | Performance Team | Initial scenarios |
