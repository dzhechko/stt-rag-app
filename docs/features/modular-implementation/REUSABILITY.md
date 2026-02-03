# Module Reusability Guide

This document explains how to reuse the modules from this project in other applications, regardless of the technology stack.

## Overview

The modules are designed to be:
- **Vendor-agnostic**: Work with different databases, message brokers, and services
- **Language-agnostic**: Patterns apply to any programming language
- **Framework-agnostic**: Integrate with any web framework
- **Cloud-agnostic**: Deploy on any cloud provider

---

## Quick Start Integration

### Step 1: Choose Your Modules

Decide which modules you need:

| Need | Module |
|------|--------|
| Track long-running operations | Progress Tracking |
| Real-time user updates | Notification |
| Background processing | Job Queue |
| Performance optimization | Cache |
| Data export capabilities | Export |
| Intelligent search | Search |

### Step 2: Set Up Infrastructure

Each module has infrastructure requirements:

```yaml
# docker-compose.yml
services:
  # Required for Job Queue, Cache
  redis:
    image: redis:7
    ports:
      - "6379:6379"

  # Required for Search
  qdrant:
    image: qdrant/qdrant:latest
    ports:
      - "6333:6333"

  # Required for most modules
  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: app_db
      POSTGRES_USER: app_user
      POSTGRES_PASSWORD: app_password
    ports:
      - "5432:5432"
```

### Step 3: Install Dependencies

#### Python (FastAPI)
```bash
pip install fastapi uvicorn sqlalchemy redis asyncpg websockets qdrant-client
```

#### Node.js (Express)
```bash
npm install express ws ioredis pg qdrant-client
```

#### Java (Spring Boot)
```xml
<dependencies>
    <dependency>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-web</artifactId>
    </dependency>
    <dependency>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-data-redis</artifactId>
    </dependency>
    <dependency>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-websocket</artifactId>
    </dependency>
</dependencies>
```

---

## Module-by-Module Integration

### 1. Progress Tracking Module

#### Requirements
- Database for persistence (PostgreSQL, MongoDB, Redis)
- Optional: WebSocket for real-time updates

#### Configuration

**Python (FastAPI)**
```python
# config.py
from pydantic_settings import BaseSettings

class ProgressConfig(BaseSettings):
    # Storage
    storage_type: str = "postgresql"
    database_url: str = "postgresql://user:pass@localhost/db"

    # Real-time updates
    websocket_enabled: bool = True
    websocket_url: str = "ws://localhost:8000/ws/progress"

    # Cleanup
    retain_completed_hours: int = 24
    retain_failed_hours: int = 168

config = ProgressConfig()
```

**Node.js (Express)**
```javascript
// config.js
module.exports = {
  progress: {
    storage: {
      type: 'postgresql',
      url: process.env.DATABASE_URL
    },
    websocket: {
      enabled: true,
      url: 'ws://localhost:8000/ws/progress'
    },
    retention: {
      completed: 24 * 3600, // hours in seconds
      failed: 168 * 3600
    }
  }
}
```

#### API Contract

**REST API**
```yaml
# Create progress
POST /api/progress
Body: {
  "id": "optional-id",
  "stages": ["upload", "process", "complete"],
  "metadata": {"file_id": "123"}
}
Response: {Progress}

# Update progress
PATCH /api/progress/{id}
Body: {
  "progress": 50,
  "stage": "upload"
}
Response: {Progress}

# Get progress
GET /api/progress/{id}
Response: {Progress}

# Complete progress
POST /api/progress/{id}/complete
Body: {"result": {...}}
Response: {Progress}

# Fail progress
POST /api/progress/{id}/fail
Body: {"error": "Error message"}
Response: {Progress}
```

**WebSocket Events**
```typescript
// Client subscribes to progress updates
const ws = new WebSocket('ws://localhost:8000/ws/progress');
ws.send(JSON.stringify({
  action: 'subscribe',
  progress_id: 'progress-id'
}));

// Server sends updates
{
  event: 'progress.update',
  data: {
    id: 'progress-id',
    progress: 50,
    stage: 'upload',
    status: 'processing'
  }
}
```

#### Integration Example

```python
# In your application
from progress_module import ProgressTracker, ProgressStorage

# Initialize
storage = ProgressStorage(database_url=config.database_url)
tracker = ProgressTracker(storage=storage, emitter=ws_emitter)

# Use in your handler
async def process_file(file_id: str):
    progress = await tracker.create(
        id=file_id,
        stages=["upload", "transcribe", "process"]
    )

    try:
        # Upload stage
        for i in range(0, 101, 10):
            await do_upload_work()
            await tracker.update(file_id, i, "upload")
        await tracker.advance_stage(file_id)

        # Transcribe stage
        for i in range(0, 101, 5):
            await do_transcribe()
            await tracker.update(file_id, i, "transcribe")

        # Complete
        await tracker.complete(file_id)

    except Exception as e:
        await tracker.fail(file_id, str(e))
```

#### Extensibility Points

1. **Custom Storage**: Implement `ProgressStorage` interface
2. **Custom Emitter**: Implement `ProgressEmitter` for different notification systems
3. **Custom Metadata**: Add application-specific metadata fields
4. **Stage Validation**: Add custom validation for stage transitions

---

### 2. Notification Module

#### Requirements
- WebSocket server (Socket.IO, ws, SockJS)
- Database for persistence (optional)
- Email service (optional): SendGrid, AWS SES, Mailgun

#### Configuration

```yaml
notification:
  # Channels
  channels:
    in_app:
      enabled: true
    email:
      enabled: true
      provider: sendgrid
      api_key: "${SENDGRID_API_KEY}"
      from: "noreply@example.com"
    push:
      enabled: false
      provider: firebase
      credentials: "./firebase.json"

  # Persistence
  persistence:
    enabled: true
    retention:
      read: 2592000  # 30 days
      unread: 7776000  # 90 days

  # Templates
  templates:
    dir: "./templates/notifications"
```

#### API Contract

```yaml
# Send notification
POST /api/notifications
Body: {
  "type": "info",
  "title": "File Uploaded",
  "message": "Your file has been uploaded successfully",
  "user_id": "user-123",
  "channels": ["in-app", "email"],
  "action_url": "/files/123",
  "action_label": "View File"
}
Response: {notification_id: "..."}

# Get user notifications
GET /api/notifications?user_id=123&unread_only=true&limit=50
Response: [{Notification}]

# Mark as read
POST /api/notifications/{id}/read
Response: {success: true}

# WebSocket subscription
WS /ws/notifications?user_id=123
```

#### Integration Example

```python
from notification_module import NotificationService, NotificationChannel

# Initialize
notifications = NotificationService(
    db=session,
    email_provider=SendGridProvider(api_key="...")
)

# Send notification
await notifications.send(
    type="success",
    title="Processing Complete",
    message="Your file has been processed",
    user_id=user_id,
    channels=[NotificationChannel.IN_APP, NotificationChannel.EMAIL],
    action_url=f"/files/{file_id}",
    action_label="View Result"
)
```

#### Extensibility Points

1. **Custom Channels**: Implement `NotificationChannel` interface
2. **Custom Templates**: Add Jinja2/Handlebars templates
3. **Notification Routing**: Route based on user preferences
4. **Batch Sending**: Queue notifications for bulk operations

---

### 3. Job Queue Module

#### Requirements
- Message broker: Redis, RabbitMQ, SQS
- Worker processes
- Optional: Monitoring dashboard

#### Configuration

```yaml
job_queue:
  # Broker
  broker:
    type: redis  # or rabbitmq, sqs
    url: "redis://localhost:6379"
    queue_prefix: "jobs"

  # Workers
  workers:
    default:
      count: 4
      queues: ["default"]
    high_priority:
      count: 2
      queues: ["high_priority"]

  # Job defaults
  defaults:
    max_attempts: 3
    backoff: exponential
    timeout: 300

  # Scheduler (for delayed jobs)
  scheduler:
    enabled: true
    timezone: "UTC"
```

#### API Contract

```yaml
# Enqueue job
POST /api/jobs
Body: {
  "name": "transcribe",
  "payload": {"file_id": "123"},
  "priority": 5,
  "delay": 0,
  "max_attempts": 3
}
Response: {job_id: "..."}

# Get job status
GET /api/jobs/{id}
Response: {Job}

# Cancel job
DELETE /api/jobs/{id}
Response: {success: true}

# List jobs
GET /api/jobs?status=pending&limit=50
Response: [{Job}]
```

#### Integration Example

```python
from job_queue import JobQueue, job_handler

# Initialize
queue = JobQueue(broker=redis_broker)

# Define job handler
@queue.handler("transcribe")
async def transcribe_job(file_id: str):
    result = await transcribe_file(file_id)
    return result

# Enqueue job
job = await queue.enqueue(
    name="transcribe",
    payload={"file_id": file_id},
    priority=5
)

# Check status
status = await queue.get_status(job.id)
```

#### Extensibility Points

1. **Custom Brokers**: Implement `JobBroker` interface for different message systems
2. **Job Dependencies**: Add job dependency graphs
3. **Custom Retry Logic**: Implement custom backoff strategies
4. **Job Middleware**: Add preprocessing/postprocessing hooks
5. **Dead Letter Queue**: Handle failed jobs

---

### 4. Cache Module

#### Requirements
- Redis (recommended) or Memcached
- Optional: In-memory cache for L1 cache

#### Configuration

```yaml
cache:
  # L1: In-memory
  l1:
    enabled: true
    max_size: 1000
    ttl: 60

  # L2: Redis
  l2:
    enabled: true
    url: "redis://localhost:6379"
    default_ttl: 3600
    key_prefix: "cache:"

  # Compression
  compression:
    enabled: true
    threshold: 1024

  # Metrics
  metrics:
    enabled: true
```

#### API Contract

```python
# Get/Set
await cache.get(key)
await cache.set(key, value, ttl=3600, tags=["user", "profile"])

# Cache aside
result = await cache.get_or_set(
    key="user:123",
    factory=lambda: fetch_user_from_db("123"),
    ttl=3600
)

# Invalidation
await cache.delete("user:123")
await cache.invalidate(["user"])  # By tags
await cache.delete_pattern("user:*")

# Stats
stats = await cache.get_stats()
# {hits: 1000, misses: 100, hit_rate: 0.91}
```

#### Integration Example

```python
from cache_module import Cache, cached

# Initialize
cache = Cache(
    l1=MemoryCache(max_size=1000),
    l2=RedisCache(url="redis://localhost:6379")
)

# Using decorator
@cached(ttl=3600, tags=["transcripts"])
async def get_transcript(id: str):
    return await db.query(Transcript).get(id)

# Manual caching
async def update_transcript(id: str, data: dict):
    result = await db.update(Transcript, id, data)
    await cache.invalidate(["transcripts"])
    return result
```

#### Extensibility Points

1. **Custom Storage**: Implement `CacheBackend` interface
2. **Serialization**: Custom serializers for complex objects
3. **Eviction Policies**: LRU, LFU, FIFO
4. **Distributed Locking**: For cache stampede prevention
5. **Cache Warming**: Pre-populate cache on startup

---

### 5. Export Module

#### Requirements
- Document generation libraries
- Template engine (optional)
- Storage backend (S3, local)

#### Configuration

```yaml
export:
  # Storage
  storage:
    type: s3  # or local, gcs
    bucket: "exports"
    region: "us-east-1"
    public_url: "https://s3.amazonaws.com/exports"

  # Formats
  formats:
    txt:
      enabled: true
    json:
      enabled: true
      pretty: true
    srt:
      enabled: true
    docx:
      enabled: true
      template_dir: "./templates/docx"
    pdf:
      enabled: true
      template_dir: "./templates/pdf"

  # Jobs
  jobs:
    timeout: 300
    max_size: 1073741824  # 1GB
```

#### API Contract

```yaml
# Create export
POST /api/exports
Body: {
  "source_type": "transcript",
  "source_id": "123",
  "format": "srt",
  "template": "custom",
  "filename": "transcript_123"
}
Response: {job_id: "...", status: "pending"}

# Get export job
GET /api/exports/{id}
Response: {ExportJob}

# Download export
GET /api/exports/{id}/download
Response: binary file

# List exports
GET /api/exports?source_type=transcript&status=completed
Response: [{ExportJob}]

# Cancel export
DELETE /api/exports/{id}
Response: {success: true}
```

#### Integration Example

```python
from export_module import ExportService, ExportFormat

# Initialize
export_service = ExportService(
    storage=S3Storage(bucket="exports"),
    job_queue=queue
)

# Export
job = await export_service.export(
    source_type="transcript",
    source_id=transcript_id,
    format=ExportFormat.SRT,
    filename=f"transcript_{transcript_id}"
)

# Check status
status = await export_service.get_job(job.id)

# Download
content = await export_service.download(job.id)
```

#### Extensibility Points

1. **Custom Formats**: Register custom export formatters
2. **Custom Templates**: Jinja2/Handlebars for complex documents
3. **Post-Processing**: Add watermarks, compression, encryption
4. **Batch Export**: Export multiple items in one job
5. **Webhook Callbacks**: Notify when export completes

---

### 6. Search Module

#### Requirements
- Vector database: Qdrant, Pinecone, Weaviate, pgvector
- Embedding service: OpenAI, Cohere, local models

#### Configuration

```yaml
search:
  # Vector database
  vector_db:
    type: qdrant  # or pinecone, weaviate, pgvector
    url: "http://localhost:6333"
    api_key: null
    collection: "documents"

  # Embeddings
  embeddings:
    provider: openai  # or cohere, local
    model: "text-embedding-3-small"
    dimension: 1536
    batch_size: 100
    api_key: "${OPENAI_API_KEY}"

  # Search settings
  search:
    default_limit: 10
    default_threshold: 0.5
    enable_hybrid: true
    enable_reranking: false
```

#### API Contract

```yaml
# Index document
POST /api/search/index
Body: {
  "id": "doc-123",
  "content": "Document content",
  "metadata": {"author": "John", "date": "2024-01-01"}
}
Response: {success: true}

# Search
POST /api/search
Body: {
  "query": "search query",
  "filters": {"author": "John"},
  "limit": 10,
  "threshold": 0.7,
  "hybrid": true
}
Response: [{SearchResult}]

# Delete document
DELETE /api/search/{id}
Response: {success: true}

# Find similar
GET /api/search/{id}/similar?limit=10
Response: [{SearchResult}]
```

#### Integration Example

```python
from search_module import SearchService, SearchDocument

# Initialize
search_service = SearchService(
    vector_db=QdrantClient(url="http://localhost:6333"),
    embedding_service=OpenAIEmbeddings(api_key="...")
)

# Index document
await search_service.index(
    SearchDocument(
        id="doc-1",
        content="Meeting about Q4 planning",
        metadata={"date": "2024-01-15", "type": "meeting"}
    )
)

# Search
results = await search_service.search(
    query="quarterly planning",
    filters={"type": "meeting"},
    limit=10,
    hybrid=True
)
```

#### Extensibility Points

1. **Custom Embeddings**: Use different embedding models
2. **Chunking Strategies**: Different ways to split documents
3. **Reranking**: Add custom reranking models
4. **Query Expansion**: Add related terms to queries
5. **Multi-Vector**: Store multiple vectors per document

---

## Plugin Architecture

### Creating Custom Plugins

Each module supports plugins for extending functionality:

```python
from progress_module import ProgressPlugin

class CustomProgressPlugin(ProgressPlugin):
    async def on_progress_update(self, progress: Progress):
        # Custom logic on progress update
        await send_to_external_system(progress)

    async def on_progress_complete(self, progress: Progress):
        # Custom logic on completion
        await cleanup_resources(progress)

# Register plugin
tracker.register_plugin(CustomProgressPlugin())
```

### Plugin Hooks

| Module | Hooks |
|--------|-------|
| Progress | `on_update`, `on_complete`, `on_fail`, `on_stage_change` |
| Notification | `on_send`, `on_deliver`, `on_read` |
| Job Queue | `on_enqueue`, `on_start`, `on_complete`, `on_fail` |
| Cache | `on_get`, `on_set`, `on_delete`, `on_hit`, `on_miss` |
| Export | `on_create`, `on_complete`, `on_download` |
| Search | `on_index`, `on_search`, `on_result` |

---

## Configuration Guide

### Environment Variables

```bash
# Database
DATABASE_URL=postgresql://user:pass@localhost/db

# Redis
REDIS_URL=redis://localhost:6379

# Qdrant
QDRANT_URL=http://localhost:6333
QDRANT_API_KEY=

# OpenAI (for embeddings)
OPENAI_API_KEY=sk-...

# SendGrid (for emails)
SENDGRID_API_KEY=SG._

# AWS (for S3 storage)
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
AWS_REGION=us-east-1
AWS_BUCKET=exports
```

### Configuration File

```yaml
# config/modules.yaml
modules:
  progress:
    enabled: true
    storage: postgresql
    websocket: true

  notification:
    enabled: true
    channels: [in-app, email]
    email_provider: sendgrid

  job_queue:
    enabled: true
    broker: redis
    workers: 4

  cache:
    enabled: true
    l1_enabled: true
    l2_enabled: true

  export:
    enabled: true
    formats: [txt, json, srt]
    storage: s3

  search:
    enabled: true
    vector_db: qdrant
    embeddings: openai
```

---

## Testing Strategy

### Unit Testing

```python
# Mock dependencies
@pytest.fixture
def mock_progress_storage():
    return MockProgressStorage()

@pytest.fixture
def progress_tracker(mock_progress_storage):
    return ProgressTracker(storage=mock_progress_storage)

async def test_progress_creation(progress_tracker):
    progress = await progress_tracker.create(
        id="test-1",
        stages=["stage1", "stage2"]
    )

    assert progress.id == "test-1"
    assert progress.status == ProgressStatus.PENDING
    assert len(progress.stages) == 2
```

### Integration Testing

```python
@pytest.fixture
async def test_database():
    # Set up test database
    async with TestDatabase() as db:
        yield db

async def test_progress_persistence(test_database):
    storage = PostgreSQLProgressStorage(test_database.url)
    tracker = ProgressTracker(storage=storage)

    progress = await tracker.create(id="test-1")
    await tracker.update("test-1", 50)

    # Verify persistence
    loaded = await tracker.get("test-1")
    assert loaded.progress == 50
```

---

## Deployment Considerations

### Docker Deployment

```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy modules
COPY modules/ ./modules/

# Copy application
COPY app/ ./app/

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Kubernetes Deployment

```yaml
# deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: app
spec:
  replicas: 3
  template:
    spec:
      containers:
      - name: app
        image: myapp:latest
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: db-secret
              key: url
        - name: REDIS_URL
          value: "redis://redis:6379"
```

### Monitoring

```python
# Add metrics to each module
from prometheus_client import Counter, Histogram

progress_updates = Counter('progress_updates_total', 'Total progress updates')
job_duration = Histogram('job_duration_seconds', 'Job processing duration')

# Use in modules
@job_duration.time()
async def process_job(job):
    # Process job
    pass
```

---

## Best Practices

1. **Start Small**: Begin with essential modules, add others as needed
2. **Configure Properly**: Adjust configuration for your use case
3. **Monitor**: Set up monitoring for all modules
4. **Test**: Write tests for module integration
5. **Document**: Keep API documentation current
6. **Version**: Use semantic versioning for modules
7. **Secure**: Never expose sensitive configuration
8. **Scale**: Design for horizontal scaling

---

## Troubleshooting

### Common Issues

| Issue | Solution |
|-------|----------|
| WebSocket connection fails | Check CORS settings, verify WebSocket URL |
| Jobs not processing | Verify worker is running, check broker connection |
| Cache not working | Check Redis connection, verify key format |
| Search returns no results | Verify embeddings generated, check threshold |
| Export fails | Check storage permissions, verify format handler |

### Debug Mode

```yaml
# Enable debug logging
logging:
  level: DEBUG
  modules:
    progress: DEBUG
    notification: DEBUG
    job_queue: DEBUG
```

---

## Support

For issues or questions:
- Check API documentation
- Review integration examples
- Examine test cases
- Open GitHub issue
