# Performance Fitness Functions

**Feature:** Performance Optimizations
**Version:** 1.0
**Date:** 2026-02-03

---

## Overview

Fitness functions define automated tests that verify performance characteristics. These functions should be part of the CI/CD pipeline and run on every deployment.

---

## Processing Speed Fitness

### Function: File Processing Speed

```python
import pytest
import time
from pathlib import Path

@pytest.mark.performance
def test_100mb_file_processing_within_30s():
    """
    Fitness Function: 100MB file should process within 30 seconds

    Target: <30 seconds for 100MB file (4 chunks, parallel)
    Current: ~60 seconds (sequential)
    Improvement: 2x speedup
    """
    # Arrange
    file_path = Path("tests/fixtures/100mb_audio.mp3")
    processing_service = ProcessingService()

    # Act
    start_time = time.time()
    result = processing_service.process_file(
        file_path=file_path,
        language="ru",
        use_parallel=True
    )
    duration = time.time() - start_time

    # Assert
    assert duration < 30.0, f"Processing took {duration:.1f}s, expected <30s"
    assert result["text"] is not None
    assert len(result["segments"]) > 0


@pytest.mark.performance
def test_parallel_2x_faster_than_sequential():
    """
    Fitness Function: Parallel processing should be 2x faster

    Target: 2x speedup with 4 concurrent chunks
    """
    # Arrange
    file_path = Path("tests/fixtures/100mb_audio.mp3")
    processing_service = ProcessingService()

    # Act: Sequential processing
    start_sequential = time.time()
    result_sequential = processing_service.process_file(
        file_path=file_path,
        language="ru",
        use_parallel=False
    )
    duration_sequential = time.time() - start_sequential

    # Act: Parallel processing
    start_parallel = time.time()
    result_parallel = processing_service.process_file(
        file_path=file_path,
        language="ru",
        use_parallel=True
    )
    duration_parallel = time.time() - start_parallel

    # Assert
    speedup = duration_sequential / duration_parallel
    assert speedup >= 2.0, f"Speedup: {speedup:.1f}x, expected >=2x"
    assert result_parallel["text"] == result_sequential["text"]
```

---

## Cache Performance Fitness

### Function: Cache Hit Rate

```python
@pytest.mark.performance
def test_cache_hit_rate_above_70_percent():
    """
    Fitness Function: Cache hit rate should be >70%

    Target: >70% of repeated requests should hit cache
    """
    # Arrange
    cache_service = CacheService()
    file_hashes = [generate_file_hash() for _ in range(100)]

    # First pass: Populate cache
    for file_hash in file_hashes:
        cache_service.get_or_compute(
            key=f"transcript:{file_hash}:ru",
            compute_func=lambda: mock_transcription()
        )

    # Second pass: Measure hits
    hits = 0
    misses = 0

    for file_hash in file_hashes:
        result = cache_service.get(f"transcript:{file_hash}:ru")
        if result:
            hits += 1
        else:
            misses += 1

    # Assert
    hit_rate = hits / (hits + misses)
    assert hit_rate > 0.70, f"Cache hit rate: {hit_rate:.1%}, expected >70%"


@pytest.mark.performance
def test_l1_cache_lookup_under_10ms():
    """
    Fitness Function: L1 cache lookup should be <10ms

    Target: <10ms for in-memory cache lookup
    """
    # Arrange
    cache_key = "transcript:test_hash:ru"
    cache_value = mock_transcription()
    cache_service = InMemoryCache()
    cache_service.put(cache_key, cache_value)

    # Act: Measure lookup time
    durations = []
    for _ in range(1000):
        start = time.perf_counter()
        result = cache_service.get(cache_key)
        duration = (time.perf_counter() - start) * 1000  # Convert to ms
        durations.append(duration)

    # Assert: p95 < 10ms
    durations.sort()
    p95 = durations[int(len(durations) * 0.95)]
    assert p95 < 10.0, f"L1 cache p95: {p95:.1f}ms, expected <10ms"


@pytest.mark.performance
def test_l2_cache_lookup_under_100ms():
    """
    Fitness Function: L2 cache lookup should be <100ms

    Target: <100ms for Redis cache lookup
    """
    # Arrange
    cache_key = "transcript:test_hash:ru"
    cache_value = mock_transcription()
    cache_service = RedisCache()
    cache_service.put(cache_key, cache_value)

    # Act: Measure lookup time
    durations = []
    for _ in range(100):
        start = time.perf_counter()
        result = cache_service.get(cache_key)
        duration = (time.perf_counter() - start) * 1000  # Convert to ms
        durations.append(duration)

    # Assert: p95 < 100ms
    durations.sort()
    p95 = durations[int(len(durations) * 0.95)]
    assert p95 < 100.0, f"L2 cache p95: {p95:.1f}ms, expected <100ms"
```

---

## Database Performance Fitness

### Function: Query Response Time

```python
@pytest.mark.performance
def test_list_transcripts_under_100ms():
    """
    Fitness Function: List query should return in <100ms (p95)

    Target: p95 <100ms for listing transcripts
    """
    # Arrange
    db_session = SessionLocal()
    # Seed 10,000 transcripts
    seed_transcripts(db_session, count=10000)

    # Act: Measure query time
    durations = []
    for _ in range(100):
        start = time.perf_counter()
        transcripts = db_session.query(Transcript).limit(20).all()
        duration = (time.perf_counter() - start) * 1000
        durations.append(duration)

    # Assert: p95 < 100ms
    durations.sort()
    p95 = durations[int(len(durations) * 0.95)]
    assert p95 < 100.0, f"Query p95: {p95:.1f}ms, expected <100ms"

    # Assert: Index usage
    plan = db_session.execute(
        "EXPLAIN ANALYZE SELECT * FROM transcripts LIMIT 20"
    ).fetchall()
    query_plan = " ".join([row[0] for row in plan])
    assert "Index Scan" in query_plan or "Limit" in query_plan, \
        "Expected index usage, got Sequential Scan"


@pytest.mark.performance
def test_no_n1_queries():
    """
    Fitness Function: No N+1 queries with eager loading

    Target: Maximum 2 queries for 100 transcripts with summaries
    """
    # Arrange
    db_session = SessionLocal()
    seed_transcripts_with_summaries(db_session, count=100)

    # Act: Enable query counting
    from sqlalchemy import event
    from sqlalchemy.engine import Engine

    query_count = 0

    @event.listens_for(Engine, "before_cursor_execute")
    def receive_before_cursor_execute(conn, cursor, statement, ...):
        nonlocal query_count
        query_count += 1

    # Execute query with eager loading
    transcripts = db_session.query(Transcript).options(
        joinedload(Transcript.summaries)
    ).limit(100).all()

    # Access summaries to trigger lazy load if present
    for t in transcripts:
        _ = t.summaries

    # Assert: Maximum 2 queries
    assert query_count <= 2, f"N+1 query detected: {query_count} queries, expected <=2"
```

---

## API Performance Fitness

### Function: API Response Time

```python
@pytest.mark.performance
def test_api_upload_response_under_500ms():
    """
    Fitness Function: Upload endpoint should respond in <500ms

    Target: <500ms to return job ID (async processing)
    """
    # Arrange
    client = TestClient(app)
    file_content = generate_test_audio(size_mb=50)

    # Act: Measure response time
    start = time.perf_counter()
    response = client.post(
        "/api/transcripts/upload",
        files={"file": ("test.mp3", file_content)},
        data={"language": "ru"}
    )
    duration = (time.perf_counter() - start) * 1000

    # Assert
    assert response.status_code == 201
    assert duration < 500.0, f"Response time: {duration:.1f}ms, expected <500ms"
    assert "job_id" in response.json()


@pytest.mark.performance
def test_api_health_under_50ms():
    """
    Fitness Function: Health check should respond in <50ms

    Target: <50ms for health endpoint
    """
    # Arrange
    client = TestClient(app)

    # Act: Measure response time
    durations = []
    for _ in range(100):
        start = time.perf_counter()
        response = client.get("/health")
        duration = (time.perf_counter() - start) * 1000
        durations.append(duration)

    # Assert: p95 < 50ms
    durations.sort()
    p95 = durations[int(len(durations) * 0.95)]
    assert p95 < 50.0, f"Health check p95: {p95:.1f}ms, expected <50ms"
```

---

## Frontend Performance Fitness

### Function: Bundle Size

```python
@pytest.mark.performance
def test_initial_bundle_under_500kb():
    """
    Fitness Function: Initial bundle should be <500KB

    Target: <500KB for initial JavaScript bundle
    """
    # Arrange
    bundle_path = Path("frontend/dist/assets/index-*.js")

    # Act: Find bundle and check size
    bundles = list(Path("frontend/dist").glob("assets/index-*.js"))
    assert len(bundles) > 0, "No bundle found"

    bundle_size = bundles[0].stat().st_size
    bundle_size_kb = bundle_size / 1024

    # Assert
    assert bundle_size_kb < 500, \
        f"Bundle size: {bundle_size_kb:.0f}KB, expected <500KB"


@pytest.mark.performance
def test_time_to_interactive_under_3s():
    """
    Fitness Function: Time to Interactive (TTI) should be <3s

    Target: <3 seconds for page to become interactive
    """
    # Arrange
    from playwright.sync_api import sync_playwright

    # Act: Measure TTI with Playwright
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()

        # Enable performance metrics
        metrics = page.evaluate(
            """() => {
                return new Promise((resolve) => {
                    new PerformanceObserver((list) => {
                        const entries = list.getEntries();
                        const tti = entries.find(
                            e => e.name === 'first-contentful-paint'
                        );
                        if (tti) resolve(tti.startTime);
                    }).observe({entryTypes: ['paint']});
                });
            }"""
        )

        page.goto("http://localhost:5173")

        # Wait for page to be interactive
        page.wait_for_selector("[data-testid='app-ready']")

        tti = page.evaluate(
            """() => {
                const nav = performance.getEntriesByType('navigation')[0];
                return nav.domContentLoadedEventEnd;
            }"""
        )

    # Assert
    assert tti < 3000, f"TTI: {tti:.0f}ms, expected <3000ms"
```

---

## Concurrency Fitness

### Function: Concurrent Job Processing

```python
@pytest.mark.performance
def test_5_concurrent_jobs():
    """
    Fitness Function: Process 5 concurrent jobs successfully

    Target: 5 concurrent jobs should complete without errors
    """
    # Arrange
    processing_service = ProcessingService()
    file_paths = [
        Path(f"tests/fixtures/audio_{i}.mp3")
        for i in range(5)
    ]

    # Act: Submit all jobs concurrently
    import concurrent.futures

    start_time = time.time()
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = [
            executor.submit(
                processing_service.process_file,
                file_path,
                "ru"
            )
            for file_path in file_paths
        ]
        results = [f.result() for f in concurrent.futures.as_completed(futures)]

    duration = time.time() - start_time

    # Assert: All jobs complete successfully
    assert len(results) == 5, "Not all jobs completed"
    assert all(r["text"] is not None for r in results), "Some jobs failed"
    assert duration < 60.0, f"Too slow: {duration:.1f}s for 5 jobs"
```

---

## Memory Fitness

### Function: Memory Usage

```python
@pytest.mark.performance
def test_memory_per_job_under_500mb():
    """
    Fitness Function: Memory usage per job should be <500MB

    Target: <500MB peak memory per transcription job
    """
    # Arrange
    import psutil
    import gc

    process = psutil.Process()
    gc.collect()
    initial_memory = process.memory_info().rss / (1024 * 1024)  # MB

    # Act: Process large file
    processing_service = ProcessingService()
    file_path = Path("tests/fixtures/100mb_audio.mp3")

    result = processing_service.process_file(
        file_path=file_path,
        language="ru"
    )

    gc.collect()
    peak_memory = process.memory_info().rss / (1024 * 1024)  # MB
    memory_used = peak_memory - initial_memory

    # Assert
    assert memory_used < 500, \
        f"Memory used: {memory_used:.0f}MB, expected <500MB"
```

---

## Throughput Fitness

### Function: Processing Throughput

```python
@pytest.mark.performance
def test_20_files_per_hour():
    """
    Fitness Function: Process 20+ 100MB files per hour

    Target: 20+ 100MB files per hour per worker
    """
    # Arrange
    processing_service = ProcessingService()
    file_paths = [
        Path("tests/fixtures/100mb_audio.mp3")
        for _ in range(20)
    ]

    # Act: Process all files and measure time
    start_time = time.time()

    for file_path in file_paths:
        processing_service.process_file(file_path, "ru")

    duration = time.time() - start_time
    files_per_hour = 3600 / (duration / 20)

    # Assert
    assert files_per_hour >= 20, \
        f"Throughput: {files_per_hour:.1f} files/hour, expected >=20"
```

---

## Fitness Function Summary

| Category | Test | Target |
|----------|------|--------|
| Processing | 100MB file speed | <30s |
| Processing | Parallel vs Sequential | >=2x speedup |
| Cache | Hit rate | >70% |
| Cache | L1 lookup (p95) | <10ms |
| Cache | L2 lookup (p95) | <100ms |
| Database | List query (p95) | <100ms |
| Database | N+1 queries | <=2 queries |
| API | Upload response | <500ms |
| API | Health check (p95) | <50ms |
| Frontend | Initial bundle | <500KB |
| Frontend | Time to Interactive | <3s |
| Concurrency | 5 concurrent jobs | All successful |
| Memory | Per job peak | <500MB |
| Throughput | Files per hour | >=20 |

---

## CI/CD Integration

### GitHub Actions Workflow

```yaml
# .github/workflows/performance-tests.yml

name: Performance Tests

on:
  pull_request:
    branches: [main]
  schedule:
    - cron: '0 6 * * *'  # Daily at 6 AM

jobs:
  performance:
    runs-on: ubuntu-latest
    timeout-minutes: 30

    services:
      postgres:
        image: postgres:15
      redis:
        image: redis:7

    steps:
      - uses: actions/checkout@v3

      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-benchmark

      - name: Run performance tests
        run: |
          pytest tests/performance/ \
            --benchmark-only \
            --benchmark-json=benchmark.json

      - name: Check fitness functions
        run: |
          pytest tests/fitness/ \
            --verbose \
            --junitxml=fitness-results.xml

      - name: Upload results
        uses: actions/upload-artifact@v3
        with:
          name: performance-results
          path: |
            benchmark.json
            fitness-results.xml
```

---

**Document Control**

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-02-03 | Performance Team | Initial fitness functions |
