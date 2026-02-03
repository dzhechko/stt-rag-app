# ADR-008: Monitoring and Observability Strategy

**Status:** Accepted
**Date:** 2026-02-03
**Context:** Performance Optimization Feature

---

## Context

The STT application performance optimizations (ADRs 001-007) introduce new infrastructure components that require comprehensive monitoring:

1. **Celery Workers:** Need task monitoring, queue depth, worker health
2. **Redis:** Need memory usage, cache hit rates, connection metrics
3. **Parallel Processing:** Need chunk progress, concurrency metrics
4. **Connection Pools:** Need pool utilization, connection health
5. **Database:** Need query performance, index usage, slow queries
6. **Frontend:** Need Core Web Vitals, bundle sizes, API latency

Currently, only basic logging exists - no structured metrics, alerting, or dashboards.

### Monitoring Requirements

| Component | Metrics Required | Alerts Required |
|-----------|------------------|-----------------|
| Celery | Task rate, success/failure, queue depth, worker health | Failed tasks, queue overflow, worker down |
| Redis | Memory, hit rate, connections, evictions | Memory high, hit rate low, connection errors |
| API | Request rate, latency, error rate, status codes | High error rate, slow responses |
| Database | Query time, connections, slow queries, index usage | Slow queries, connection pool exhausted |
| Frontend | Core Web Vitals, API latency, bundle size | Poor LCP, high TBT, large bundles |

---

## Decision

Implement a comprehensive observability stack using **Prometheus, Grafana, Sentry, and Celery Flower**.

### Architecture

```
                            +---------------------+
                            |   Grafana Dashboards|
                            |  - System Overview  |
                            |  - Celery Workers   |
                            |  - Redis Cache      |
                            |  - API Performance  |
                            |  - Frontend Vitals  |
                            +---------+-----------+
                                      |
                                      | Query
                                      v
+---------------+           +-------------------+           +---------------+
|   Application | +-------> |    Prometheus     | <--------+ |   Node/Worker |
|  (FastAPI)    | Metrics   |  - Time Series DB |  Scrape   |  Exporters    |
+---------------+           +-------------------+           +---------------+
       |                                                          |
       |                                                          |
       v                                                          v
+---------------+           +-------------------+           +---------------+
|   Celery      | +-------> |     Sentry        | <--------+ |   Redis       |
|   Flower      |   UI     |  - Error Tracking |  Events   |  Exporter     |
+---------------+           +-------------------+           +---------------+
```

---

## Component Details

### 1. Prometheus (Metrics Collection)

**Purpose:** Time-series database for metrics storage and querying

**Configuration:**

```yaml
# prometheus.yml
global:
  scrape_interval: 15s
  evaluation_interval: 15s
  external_labels:
    cluster: 'stt-production'
    environment: 'production'

alerting:
  alertmanagers:
    - static_configs:
        - targets: ['alertmanager:9093']

rule_files:
  - '/etc/prometheus/rules/*.yml'

scrape_configs:
  # FastAPI backend
  - job_name: 'fastapi-backend'
    static_configs:
      - targets: ['backend:8000']
    metrics_path: '/metrics'
    scrape_interval: 10s

  # Celery workers
  - job_name: 'celery-workers'
    static_configs:
      - targets: ['worker-high:9540', 'worker-medium:9541', 'worker-low:9542']
    scrape_interval: 15s

  # Redis
  - job_name: 'redis'
    static_configs:
      - targets: ['redis-exporter:9121']
    scrape_interval: 10s

  # PostgreSQL
  - job_name: 'postgres'
    static_configs:
      - targets: ['postgres-exporter:9187']
    scrape_interval: 30s

  # Node exporters
  - job_name: 'node'
    static_configs:
      - targets: ['node-exporter:9100']
    scrape_interval: 15s
```

**Instrumentation:**

```python
# backend/app/metrics.py
from prometheus_client import Counter, Histogram, Gauge, Summary
import time

# Request metrics
http_requests_total = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

http_request_duration_seconds = Histogram(
    'http_request_duration_seconds',
    'HTTP request latency',
    ['method', 'endpoint'],
    buckets=[0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
)

# Database metrics
db_query_duration_seconds = Histogram(
    'db_query_duration_seconds',
    'Database query duration',
    ['operation', 'table'],
    buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0]
)

db_connections_active = Gauge(
    'db_connections_active',
    'Active database connections'
)

# Redis metrics
redis_cache_hits = Counter(
    'redis_cache_hits_total',
    'Redis cache hits',
    ['cache_type']
)

redis_cache_misses = Counter(
    'redis_cache_misses_total',
    'Redis cache misses',
    ['cache_type']
)

redis_memory_usage_bytes = Gauge(
    'redis_memory_usage_bytes',
    'Redis memory usage in bytes'
)

# Celery metrics
celery_task_duration_seconds = Histogram(
    'celery_task_duration_seconds',
    'Celery task duration',
    ['task_name', 'status'],
    buckets=[1, 5, 10, 30, 60, 300, 600, 1800, 3600]
)

celery_queue_depth = Gauge(
    'celery_queue_depth',
    'Celery queue depth',
    ['queue_name']
)

# Processing metrics
processing_chunks_total = Counter(
    'processing_chunks_total',
    'Total chunks processed',
    ['status', 'from_cache']
)

processing_file_duration_seconds = Histogram(
    'processing_file_duration_seconds',
    'File processing duration',
    ['file_size_mb'],
    buckets=[10, 30, 60, 120, 300, 600, 1200]
)

# Middleware
from fastapi import Request
import time

@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    start_time = time.time()

    response = await call_next(request)

    duration = time.time() - start_time
    http_requests_total.labels(
        method=request.method,
        endpoint=request.url.path,
        status=response.status_code
    ).inc()

    http_request_duration_seconds.labels(
        method=request.method,
        endpoint=request.url.path
    ).observe(duration)

    return response
```

---

### 2. Grafana (Dashboards)

**Purpose:** Visualization and alerting UI

**Dashboard Configuration:**

```json
{
  "dashboard": {
    "title": "STT Performance Overview",
    "panels": [
      {
        "title": "Request Rate",
        "targets": [
          {
            "expr": "rate(http_requests_total[5m])",
            "legendFormat": "{{method}} {{endpoint}}"
          }
        ]
      },
      {
        "title": "P95 Latency",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))",
            "legendFormat": "{{endpoint}}"
          }
        ]
      },
      {
        "title": "Celery Queue Depth",
        "targets": [
          {
            "expr": "celery_queue_depth",
            "legendFormat": "{{queue_name}}"
          }
        ]
      },
      {
        "title": "Cache Hit Rate",
        "targets": [
          {
            "expr": "rate(redis_cache_hits_total[5m]) / (rate(redis_cache_hits_total[5m]) + rate(redis_cache_misses_total[5m]))",
            "legendFormat": "{{cache_type}}"
          }
        ]
      },
      {
        "title": "Database Query Duration",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, rate(db_query_duration_seconds_bucket[5m]))",
            "legendFormat": "{{table}}"
          }
        ]
      },
      {
        "title": "Processing Time by File Size",
        "targets": [
          {
            "expr": "avg(processing_file_duration_seconds) by (file_size_mb)",
            "legendFormat": "{{file_size_mb}}MB"
          }
        ]
      }
    ]
  }
}
```

**Key Dashboards:**

1. **System Overview:** Request rate, error rate, latency, CPU/memory
2. **Celery Workers:** Task rate, queue depth, worker health, task duration
3. **Redis Cache:** Hit rate, memory usage, connections, eviction rate
4. **Database Performance:** Query duration, slow queries, connection pool
5. **Processing Jobs:** File processing time, chunk success rate, cache efficiency
6. **Frontend Vitals:** LCP, FID, CLS, TTI

---

### 3. Sentry (Error Tracking)

**Purpose:** Real-time error tracking and alerting

**Configuration:**

```python
# backend/app/main.py
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.celery import CeleryIntegration
from sentry_sdk.integrations.redis import RedisIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

sentry_sdk.init(
    dsn=settings.sentry_dsn,
    integrations=[
        FastApiIntegration(),
        CeleryIntegration(),
        RedisIntegration(),
        SqlalchemyIntegration(),
    ],
    traces_sample_rate=0.1,  # 10% of transactions
    profiles_sample_rate=0.1,  # 10% of profiles
    environment=settings.environment,
    release=settings.version,
    before_send_transaction=event_filter,
)

def event_filter(event, hint):
    # Filter out health check transactions
    if event.get("transaction", "").startswith("/health"):
        return None
    return event
```

**Error Context:**

```python
# Add context to errors
try:
    result = transcribe_file(file_path)
except Exception as e:
    sentry_sdk.set_context("transcription", {
        "file_path": file_path,
        "file_size_mb": os.path.getsize(file_path) / (1024 * 1024),
        "language": language,
        "chunk_count": len(chunks)
    })
    sentry_sdk.capture_exception(e)
    raise
```

---

### 4. Celery Flower (Worker Monitoring)

**Purpose:** Real-time Celery task monitoring

**Configuration:**

```bash
# docker-compose.yml
flower:
  image: mher/flower:latest
  container_name: stt-flower
  command: celery -A app.celery_config flower --port=5555 --broker=redis://redis:6379/0
  ports:
    - "5555:5555"
  environment:
    - CELERY_BROKER_URL=redis://redis:6379/0
    - FLOWER_BASIC_AUTH=admin:${FLOWER_PASSWORD}
  depends_on:
    - redis
  restart: unless-stopped
```

**Features:**
- Real-time task status
- Worker information
- Queue depth visualization
- Task execution time
- Success/failure rates
- Task parameters and results

---

## Alerting Rules

### Prometheus Alert Rules

```yaml
# prometheus/rules/alerts.yml
groups:
  - name: stt_alerts
    interval: 30s
    rules:
      # API alerts
      - alert: HighErrorRate
        expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.05
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "High error rate detected"
          description: "Error rate is {{ $value }} errors/sec"

      - alert: SlowAPIResponses
        expr: histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m])) > 2
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Slow API responses"
          description: "P95 latency is {{ $value }} seconds"

      # Celery alerts
      - alert: CeleryQueueOverflow
        expr: celery_queue_depth > 100
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "Celery queue depth high"
          description: "Queue {{ $labels.queue_name }} has {{ $value }} tasks"

      - alert: CeleryWorkerDown
        expr: up{job="celery-workers"} == 0
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "Celery worker down"
          description: "Worker {{ $labels.instance }} is not responding"

      # Redis alerts
      - alert: RedisMemoryHigh
        expr: redis_memory_usage_bytes / redis_memory_max_bytes > 0.9
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Redis memory usage high"
          description: "Redis using {{ $value | humanizePercentage }} of max memory"

      - alert: LowCacheHitRate
        expr: rate(redis_cache_hits_total[10m]) / (rate(redis_cache_hits_total[10m]) + rate(redis_cache_misses_total[10m])) < 0.5
        for: 15m
        labels:
          severity: warning
        annotations:
          summary: "Low cache hit rate"
          description: "Hit rate is {{ $value | humanizePercentage }}"

      # Database alerts
      - alert: SlowDatabaseQueries
        expr: histogram_quantile(0.95, rate(db_query_duration_seconds_bucket[5m])) > 1
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "Slow database queries"
          description: "P95 query time is {{ $value }} seconds"

      - alert: DatabaseConnectionPoolExhausted
        expr: db_connections_active / db_connections_max > 0.9
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "Database connection pool nearly full"
          description: "{{ $value | humanizePercentage }} of connections in use"
```

---

## Docker Compose Integration

```yaml
# docker-compose.yml additions

services:
  # Prometheus
  prometheus:
    image: prom/prometheus:latest
    container_name: stt-prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--web.console.libraries=/usr/share/prometheus/console_libraries'
      - '--web.console.templates=/usr/share/prometheus/consoles'
    volumes:
      - ./config/prometheus.yml:/etc/prometheus/prometheus.yml:ro
      - ./config/prometheus/rules:/etc/prometheus/rules:ro
      - prometheus_data:/prometheus
    ports:
      - "9090:9090"
    restart: unless-stopped

  # Grafana
  grafana:
    image: grafana/grafana:latest
    container_name: stt-grafana
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=${GRAFANA_PASSWORD}
      - GF_USERS_ALLOW_SIGN_UP=false
    volumes:
      - grafana_data:/var/lib/grafana
      - ./config/grafana/provisioning:/etc/grafana/provisioning:ro
    ports:
      - "3001:3000"
    restart: unless-stopped

  # Redis exporter
  redis-exporter:
    image: oliver006/redis_exporter:latest
    container_name: stt-redis-exporter
    environment:
      - REDIS_ADDR=redis://redis:6379
    ports:
      - "9121:9121"
    depends_on:
      - redis
    restart: unless-stopped

  # PostgreSQL exporter
  postgres-exporter:
    image: prometheuscommunity/postgres-exporter:latest
    container_name: stt-postgres-exporter
    environment:
      - DATA_SOURCE_NAME=postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@postgres:5432/${POSTGRES_DB}
    ports:
      - "9187:9187"
    depends_on:
      - postgres
    restart: unless-stopped

  # Node exporter
  node-exporter:
    image: prom/node-exporter:latest
    container_name: stt-node-exporter
    ports:
      - "9100:9100"
    restart: unless-stopped

  # AlertManager
  alertmanager:
    image: prom/alertmanager:latest
    container_name: stt-alertmanager
    command:
      - '--config.file=/etc/alertmanager/alertmanager.yml'
    volumes:
      - ./config/alertmanager.yml:/etc/alertmanager/alertmanager.yml:ro
      - alertmanager_data:/alertmanager
    ports:
      - "9093:9093"
    restart: unless-stopped

volumes:
  prometheus_data:
  grafana_data:
  alertmanager_data:
```

---

## Alternatives Considered

### 1. CloudWatch (AWS)

**Pros:** Managed service, AWS integration
**Cons:** Vendor lock-in, expensive, complex setup
**Decision:** Open-source preferred for flexibility

### 2. DataDog

**Pros:** All-in-one, excellent UI
**Cons:** Expensive, overkill for current scale
**Decision:** Not justified at current scale

### 3. Grafana Cloud

**Pros:** Managed Grafana, easy setup
**Cons:** Cost scales with metrics
**Decision:** Self-host for cost control

### 4. Basic Logging Only

**Pros:** Simple, no infrastructure
**Cons:** No dashboards, no alerting, reactive only
**Decision:** Insufficient for production

---

## Migration Strategy

### Phase 1: Infrastructure Setup (Week 1)

1. Deploy Prometheus and Grafana
2. Configure scrape targets
3. Set up basic dashboards

### Phase 2: Application Instrumentation (Week 2)

1. Add prometheus_client to FastAPI
2. Instrument critical paths
3. Add Sentry error tracking

### Phase 3: Alerting (Week 3)

1. Define alert thresholds
2. Configure AlertManager
3. Set up notifications (Slack/Email)

### Phase 4: Validation (Week 4)

1. Verify metrics collection
2. Test alerting
3. Tune thresholds

---

## Consequences

### Positive

1. **Visibility:** Real-time insight into system health
2. **Proactive:** Alert on issues before users notice
3. **Debugging:** Rich context for troubleshooting
4. **Optimization:** Data-driven performance improvements
5. **Reliability:** Track trends and prevent regressions

### Negative

1. **Complexity:** Additional infrastructure to maintain
2. **Cost:** Resources for monitoring stack
3. **Learning Curve:** Team needs Prometheus/Grafana knowledge
4. **Alert Fatigue:** Poorly tuned alerts cause noise

### Mitigations

- Start with critical alerts only
- Use managed services where appropriate
- Document dashboard usage
- Regular alert tuning reviews

---

**Document Control**

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-02-03 | Performance Team | Initial ADR |
