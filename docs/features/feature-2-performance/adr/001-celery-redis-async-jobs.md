# ADR-001: Celery + Redis for Async Job Processing

**Status:** Accepted
**Date:** 2026-02-03
**Context:** Performance Optimization Feature

---

## Context

The STT application currently uses FastAPI's `BackgroundTasks` for asynchronous processing. This approach has several limitations:

1. **No Persistence:** Jobs lost if worker restarts
2. **No Priority Queues:** All jobs treated equally
3. **No Retry Logic:** Custom retry required
4. **No Monitoring:** No job visibility dashboard
5. **Limited Scalability:** Tied to FastAPI process

We need a robust async job queue system that supports:
- Priority-based job routing
- Persistent job storage
- Automatic retry with exponential backoff
- Worker monitoring and metrics
- Horizontal scalability

---

## Decision

Use **Celery** with **Redis** as the message broker for async job processing.

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      FastAPI Backend                        │
│                                                               │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              API Endpoints                           │   │
│  └──────────────────────┬──────────────────────────────┘   │
│                         │                                   │
│                         ▼                                   │
│  ┌─────────────────────────────────────────────────────┐   │
│  │            Celery Client (python-celery)            │   │
│  │                                                     │   │
│  │  - high_priority_queue (transcription)              │   │
│  │  - medium_priority_queue (summarization)            │   │
│  │  - low_priority_queue (indexing, translation)       │   │
│  └──────────────────────┬──────────────────────────────┘   │
└─────────────────────────┼───────────────────────────────────┘
                          │
                          │ (Redis Protocol)
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                    Redis Message Broker                      │
│                                                               │
│  Queue: high    Queue: medium   Queue: low                  │
│  ┌───────────┐ ┌─────────────┐ ┌───────────────┐           │
│  │ Job 1     │ │ Job 3       │ │ Job 5         │           │
│  │ Job 2     │ │ Job 4       │ │ Job 6         │           │
│  └───────────┘ └─────────────┘ └───────────────┘           │
└─────────────────────────────┬───────────────────────────────┘
                              │
                              │
                  ┌───────────┴───────────┐
                  │                       │
                  ▼                       ▼
┌─────────────────────────────┐ ┌─────────────────────────────┐
│   Celery Worker 1           │ │   Celery Worker 2           │
│  - 4 concurrency            │  - 4 concurrency            │
│  - consumes: high, medium   │  - consumes: medium, low     │
│  - processes: transcription │  - processes: summarization  │
└─────────────────────────────┘ └─────────────────────────────┘
                  │                       │
                  └───────────┬───────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                     Flower (Monitoring)                      │
│  Web UI for:                                                 │
│  - Job status                                               │
│  - Worker health                                             │
│  - Queue depth                                              │
│  - Task progress                                            │
└─────────────────────────────────────────────────────────────┘
```

---

## Configuration

### Celery Configuration

```python
# backend/app/celery_config.py

from celery import Celery
from celery.schedules import crontab

# Create Celery app
celery_app = Celery('stt_tasks')

# Redis broker configuration
celery_app.conf.update(
    # Broker settings
    broker_url='redis://redis:6379/0',
    result_backend='redis://redis:6379/1',

    # Task routing
    task_routes={
        'app.tasks.transcribe_chunk': {
            'queue': 'high_priority',
            'routing_key': 'high_priority.transcribe'
        },
        'app.tasks.transcribe_full': {
            'queue': 'high_priority',
            'routing_key': 'high_priority.transcribe'
        },
        'app.tasks.summarize': {
            'queue': 'medium_priority',
            'routing_key': 'medium_priority.summarize'
        },
        'app.tasks.translate': {
            'queue': 'medium_priority',
            'routing_key': 'medium_priority.translate'
        },
        'app.tasks.index_rag': {
            'queue': 'low_priority',
            'routing_key': 'low_priority.index'
        },
    },

    # Worker settings
    worker_prefetch_multiplier=1,  # Don't hoard tasks
    task_acks_late=True,           # Ack only after completion
    task_time_limit=3600,          # 1 hour max per task
    task_soft_time_limit=3300,     # Soft limit at 55 minutes
    task_reject_on_worker_lost=True,

    # Retry settings
    task_autoretry_for=(Exception,),
    task_retry_kwargs={'max_retries': 3, 'countdown': 60},
    task_retry_delay=30,           # Initial retry delay

    # Result settings
    result_expires=86400,          # Results expire in 24 hours
    result_extended=True,

    # Serialization
    task_serializer='json',
    result_serializer='json',
    accept_content=['json'],

    # Timezone
    timezone='UTC',
    enable_utc=True,

    # Security
    broker_transport_options={'visibility_timeout': 3600},
)

# Scheduled tasks
celery_app.conf.beat_schedule = {
    'cleanup-old-results': {
        'task': 'app.tasks.cleanup_old_results',
        'schedule': crontab(hour=2, minute=0),  # 2 AM daily
    },
    'cleanup-failed-jobs': {
        'task': 'app.tasks.cleanup_failed_jobs',
        'schedule': crontab(hour=3, minute=0),  # 3 AM daily
    },
}
```

### Task Definitions

```python
# backend/app/tasks.py

from celery import shared_task
from app.services.transcription_service import TranscriptionService
from app.database import SessionLocal
import logging

logger = logging.getLogger(__name__)

@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60
)
def transcribe_full_file(
    self,
    transcript_id: str,
    file_path: str,
    language: str = None
):
    """Transcribe full file (Celery task)"""
    db = SessionLocal()
    try:
        # Update job status
        job = db.query(ProcessingJob).filter_by(
            transcript_id=transcript_id,
            job_type=JobType.TRANSCRIPTION
        ).first()

        if job:
            job.status = JobStatus.PROCESSING
            job.worker_id = self.request.id
            db.commit()

        # Process transcription
        service = TranscriptionService()
        result = service.transcribe_file(
            file_path=file_path,
            language=language
        )

        # Update transcript
        transcript = db.query(Transcript).get(transcript_id)
        transcript.transcription_text = result["text"]
        transcript.transcription_json = result.get("full_response")
        transcript.status = TranscriptStatus.COMPLETED

        # Update job
        if job:
            job.status = JobStatus.COMPLETED
            job.progress = 1.0

        db.commit()
        return {"success": True, "transcript_id": transcript_id}

    except Exception as exc:
        logger.error(f"Transcription failed: {exc}")
        self.retry(exc=exc, countdown=2 ** self.request.retries)
    finally:
        db.close()

@shared_task
def transcribe_chunk(
    chunk_id: str,
    file_path: str,
    language: str = None
):
    """Transcribe single chunk (for parallel processing)"""
    # Similar structure, optimized for chunk processing
    pass

@shared_task(
    bind=True,
    max_retries=2
)
def summarize_transcript(
    self,
    transcript_id: str,
    template: str = None
):
    """Summarize transcript (Celery task)"""
    db = SessionLocal()
    try:
        # Get transcript
        transcript = db.query(Transcript).get(transcript_id)
        if not transcript or not transcript.transcription_text:
            raise ValueError("Transcript not found or empty")

        # Summarize
        service = SummarizationService()
        summary = service.summarize(
            text=transcript.transcription_text,
            template=template
        )

        # Save summary
        summary_record = Summary(
            transcript_id=transcript_id,
            summary_text=summary["summary_text"],
            summary_template=template
        )
        db.add(summary_record)
        db.commit()

        return {"success": True, "summary_id": str(summary_record.id)}

    except Exception as exc:
        logger.error(f"Summarization failed: {exc}")
        self.retry(exc=exc)
    finally:
        db.close()
```

### Worker Commands

```bash
# Start high-priority worker (transcription)
celery -A app.celery_config worker \
    --loglevel=info \
    --queues=high_priority \
    --concurrency=4 \
    --hostname=worker-high@%h \
    --max-tasks-per-child=100

# Start medium-priority worker (summarization, translation)
celery -A app.celery_config worker \
    --loglevel=info \
    --queues=medium_priority \
    --concurrency=2 \
    --hostname=worker-medium@%h

# Start low-priority worker (indexing)
celery -A app.celery_config worker \
    --loglevel=info \
    --queues=low_priority \
    --concurrency=2 \
    --hostname=worker-low@%h

# Start beat scheduler (for periodic tasks)
celery -A app.celery_config beat \
    --loglevel=info \
    --pidfile=/tmp/celerybeat.pid

# Start Flower (monitoring)
celery -A app.celery_config flower \
    --port=5555 \
    --broker=redis://redis:6379/0
```

---

## Docker Compose Integration

```yaml
# docker-compose.yml additions

services:
  redis:
    image: redis:7-alpine
    container_name: stt-redis
    command: redis-server --appendonly yes
    volumes:
      - redis_data:/data
    ports:
      - "6379:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

  celery-worker-high:
    build:
      context: ./backend
      dockerfile: Dockerfile
    container_name: stt-worker-high
    command: celery -A app.celery_config worker --loglevel=info --queues=high_priority --concurrency=4
    environment:
      - CELERY_BROKER_URL=redis://redis:6379/0
      - CELERY_RESULT_BACKEND=redis://redis:6379/1
    depends_on:
      - redis
      - postgres
    restart: unless-stopped

  celery-worker-medium:
    build:
      context: ./backend
      dockerfile: Dockerfile
    container_name: stt-worker-medium
    command: celery -A app.celery_config worker --loglevel=info --queues=medium_priority --concurrency=2
    environment:
      - CELERY_BROKER_URL=redis://redis:6379/0
      - CELERY_RESULT_BACKEND=redis://redis:6379/1
    depends_on:
      - redis
      - postgres
    restart: unless-stopped

  celery-beat:
    build:
      context: ./backend
      dockerfile: Dockerfile
    container_name: stt-celery-beat
    command: celery -A app.celery_config beat --loglevel=info
    environment:
      - CELERY_BROKER_URL=redis://redis:6379/0
    depends_on:
      - redis
    restart: unless-stopped

  flower:
    build:
      context: ./backend
      dockerfile: Dockerfile
    container_name: stt-flower
    command: celery -A app.celery_config flower --port=5555 --broker=redis://redis:6379/0
    ports:
      - "5555:5555"
    environment:
      - CELERY_BROKER_URL=redis://redis:6379/0
    depends_on:
      - redis
    restart: unless-stopped

volumes:
  redis_data:
```

---

## API Integration

```python
# backend/app/main.py

from app.tasks import transcribe_full_file

@app.post("/api/transcripts/upload")
async def upload_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    language: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    # Create transcript record
    transcript = Transcript(...)
    db.add(transcript)
    db.commit()

    # Submit to Celery instead of BackgroundTasks
    job = transcribe_full_file.delay(
        transcript_id=str(transcript.id),
        file_path=saved_file_path,
        language=language
    )

    # Create processing job with Celery task ID
    processing_job = ProcessingJob(
        transcript_id=transcript.id,
        job_type=JobType.TRANSCRIPTION,
        status=JobStatus.QUEUED,
        celery_task_id=job.id
    )
    db.add(processing_job)
    db.commit()

    return {
        "transcript_id": str(transcript.id),
        "job_id": job.id,
        "status": "queued"
    }

@app.get("/api/jobs/{job_id}/status")
async def get_job_status(job_id: str):
    """Get Celery job status"""
    from app.celery_config import celery_app

    result = celery_app.AsyncResult(job_id)

    return {
        "job_id": job_id,
        "status": result.state,
        "result": result.result if result.ready() else None
    }
```

---

## Monitoring with Flower

Flower provides a web UI for monitoring:

- **URL:** http://localhost:5555
- **Features:**
  - Real-time task status
  - Worker information
  - Queue depth
  - Task success/failure rates
  - Execution time metrics
  - Broker monitoring

---

## Consequences

### Positive

1. **Robust Queue:** Persistent job storage with Redis
2. **Priority Support:** Separate queues for different priorities
3. **Automatic Retry:** Built-in exponential backoff
4. **Monitoring:** Flower dashboard for visibility
5. **Scalability:** Add workers without code changes
6. **Maturity:** Well-documented, production-proven

### Negative

1. **Complexity:** Additional infrastructure component
2. **Redis Dependency:** Requires Redis maintenance
3. **Learning Curve:** Celery concepts (tasks, workers, beat)
4. **Debugging:** Distributed debugging is harder
5. **Resource Usage:** Workers consume memory

### Mitigations

- Use Docker for easy deployment
- Implement health checks
- Add comprehensive logging
- Use Flower for monitoring
- Document worker configuration

---

## Alternatives Considered

### 1. RQ (Redis Queue)

**Pros:** Simpler than Celery
**Cons:** No built-in retry, no Beat scheduler, less mature
**Decision:** Not chosen due to limited features

### 2. Dramatiq

**Pros:** Modern, simpler API
**Cons:** Smaller community, less documentation
**Decision:** Not chosen due to ecosystem support

### 3. FastAPI BackgroundTasks (Current)

**Pros:** Built-in, simple
**Cons:** No persistence, no priority, no retry
**Decision:** Being replaced due to limitations

---

## References

- Celery Documentation: https://docs.celeryq.dev/
- Redis as Broker: https://docs.celeryq.dev/en/stable/userguide/redis.html
- Flower Monitoring: https://flower.readthedocs.io/

---

**Document Control**

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-02-03 | Performance Team | Initial ADR |
