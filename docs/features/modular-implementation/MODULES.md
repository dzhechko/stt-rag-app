# Reusable Modules Documentation

This document describes the reusable modules that can be extracted from the STT application and applied to any IT project.

## Module Catalog

| Module | Purpose | Complexity | Reusability |
|--------|---------|------------|-------------|
| Progress Tracking | Track long-running operations | Medium | High |
| Notification | Real-time user notifications | Medium | High |
| Job Queue | Async background processing | High | High |
| Cache | Performance optimization | Medium | High |
| Export | Multi-format data export | Medium | Medium |
| Search | Vector-based semantic search | High | Medium |

---

## 1. Progress Tracking Module

### Purpose
Track the progress of long-running operations (file uploads, data processing, batch jobs, etc.) with real-time updates to users.

### Scope
- Progress state management (enum-based)
- Percentage-based progress (0-100)
- Multi-stage progress tracking
- Error handling and recovery
- Progress persistence
- Progress aggregation (batch operations)

### Interface/Contract

#### TypeScript/JavaScript
```typescript
interface ProgressTracker {
  // Create a new progress tracker
  create(options: ProgressOptions): Promise<Progress>

  // Update progress
  update(id: string, progress: number, stage?: string): Promise<void>

  // Complete progress
  complete(id: string, result?: any): Promise<void>

  // Fail progress
  fail(id: string, error: Error): Promise<void>

  // Get current progress
  get(id: string): Promise<Progress>

  // Subscribe to progress updates
  subscribe(id: string, callback: (progress: Progress) => void): () => void
}

interface Progress {
  id: string
  status: 'pending' | 'processing' | 'completed' | 'failed'
  progress: number // 0-100
  stage?: string
  stages?: ProgressStage[]
  error?: ProgressError
  metadata: Record<string, any>
  createdAt: Date
  updatedAt: Date
  completedAt?: Date
}

interface ProgressStage {
  name: string
  status: 'pending' | 'processing' | 'completed' | 'failed'
  progress: number
  startedAt?: Date
  completedAt?: Date
}

interface ProgressOptions {
  id?: string
  stages?: string[]
  metadata?: Record<string, any>
  userId?: string
}
```

#### Python
```python
from dataclasses import dataclass
from enum import Enum
from typing import Optional, List, Callable, Dict, Any
from datetime import datetime

class ProgressStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

@dataclass
class ProgressStage:
    name: str
    status: ProgressStatus
    progress: float
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

@dataclass
class Progress:
    id: str
    status: ProgressStatus
    progress: float
    stage: Optional[str] = None
    stages: Optional[List[ProgressStage]] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = None
    created_at: datetime = None
    updated_at: datetime = None
    completed_at: Optional[datetime] = None

class ProgressTracker:
    async def create(self, options: ProgressOptions) -> Progress:
        """Create a new progress tracker"""
        pass

    async def update(self, id: str, progress: float, stage: Optional[str] = None) -> None:
        """Update progress"""
        pass

    async def complete(self, id: str, result: Optional[Any] = None) -> None:
        """Mark progress as complete"""
        pass

    async def fail(self, id: str, error: Exception) -> None:
        """Mark progress as failed"""
        pass

    async def get(self, id: str) -> Progress:
        """Get current progress"""
        pass
```

### Dependencies
- Database (PostgreSQL, MongoDB, etc.)
- Cache layer (optional, for performance)
- WebSocket server (for real-time updates)

### Configuration Options
```yaml
progress_tracker:
  # Persistence backend
  storage:
    type: postgresql # or mongodb, redis, memory
    connection_string: "${DATABASE_URL}"
    table: "progress"

  # Cache configuration
  cache:
    enabled: true
    ttl: 3600 # seconds

  # Cleanup
  cleanup:
    enabled: true
    retain_completed: 86400 # 24 hours
    retain_failed: 604800 # 7 days

  # Real-time updates
  realtime:
    enabled: true
    websocket_url: "ws://localhost:8000/ws/progress"
```

### Integration Points

#### Backend Integration
```python
# In your long-running operation handler
from progress_tracker import tracker

async def process_file(file_id: str):
    # Create progress tracker
    progress = await tracker.create(
        id=file_id,
        stages=["upload", "transcribe", "process"]
    )

    try:
        # Stage 1: Upload
        await tracker.update(progress.id, 0, "upload")
        await upload_file(file_id)
        await tracker.update(progress.id, 100, "upload")

        # Stage 2: Transcribe
        await tracker.update(progress.id, 0, "transcribe")
        for i in range(100):
            await do_transcription_work()
            await tracker.update(progress.id, i, "transcribe")

        # Complete
        await tracker.complete(progress.id)
    except Exception as e:
        await tracker.fail(progress.id, e)
```

#### Frontend Integration
```typescript
// React component
import { useProgress } from '@modules/progress'

function FileUpload({ fileId }) {
  const { progress, stage, status } = useProgress(fileId)

  return (
    <div>
      <ProgressBar value={progress} />
      <p>Status: {status}</p>
      <p>Stage: {stage}</p>
    </div>
  )
}
```

---

## 2. Notification Module

### Purpose
Send real-time notifications to users through multiple channels (WebSocket, email, push, etc.).

### Scope
- WebSocket-based real-time notifications
- Notification persistence
- User notification preferences
- Notification channels (in-app, email, push)
- Notification templates
- Notification queue for offline users

### Interface/Contract

#### TypeScript/JavaScript
```typescript
interface NotificationService {
  // Send notification to user
  send(notification: Notification): Promise<void>

  // Send bulk notifications
  sendBulk(notifications: Notification[]): Promise<void>

  // Mark notification as read
  markAsRead(notificationId: string, userId: string): Promise<void>

  // Get user notifications
  getUserNotifications(userId: string, filters?: NotificationFilters): Promise<Notification[]>

  // Subscribe to real-time notifications
  subscribe(userId: string, callback: (notification: Notification) => void): () => void

  // Set user preferences
  setPreferences(userId: string, preferences: NotificationPreferences): Promise<void>
}

interface Notification {
  id: string
  type: 'info' | 'success' | 'warning' | 'error'
  title: string
  message: string
  timestamp: Date
  read: boolean
  userId: string
  category?: string
  actionUrl?: string
  actionLabel?: string
  metadata?: Record<string, any>
  channels?: NotificationChannel[]
}

type NotificationChannel = 'in-app' | 'email' | 'push' | 'sms'

interface NotificationPreferences {
  channels: NotificationChannel[]
  categories: Record<string, boolean>
  quietHours?: { start: string; end: string }
}
```

#### Python
```python
from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from enum import Enum

class NotificationType(str, Enum):
    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"

class NotificationChannel(str, Enum):
    IN_APP = "in-app"
    EMAIL = "email"
    PUSH = "push"
    SMS = "sms"

@dataclass
class Notification:
    id: str
    type: NotificationType
    title: str
    message: str
    user_id: str
    category: Optional[str] = None
    action_url: Optional[str] = None
    action_label: Optional[str] = None
    metadata: Dict[str, Any] = None
    channels: List[NotificationChannel] = None

class NotificationService:
    async def send(self, notification: Notification) -> None:
        """Send notification to user"""
        pass

    async def send_bulk(self, notifications: List[Notification]) -> None:
        """Send bulk notifications"""
        pass

    async def mark_as_read(self, notification_id: str, user_id: str) -> None:
        """Mark notification as read"""
        pass

    async def get_user_notifications(
        self,
        user_id: str,
        unread_only: bool = False,
        limit: int = 50
    ) -> List[Notification]:
        """Get user notifications"""
        pass
```

### Dependencies
- WebSocket server (Socket.IO, ws, etc.)
- Database for notification persistence
- Email service (SendGrid, AWS SES, etc.) - optional
- Push notification service (Firebase, OneSignal) - optional

### Configuration Options
```yaml
notification:
  # Persistence
  storage:
    type: postgresql
    connection_string: "${DATABASE_URL}"
    table: "notifications"

  # WebSocket
  websocket:
    enabled: true
    path: "/ws/notifications"
    cors_origins: ["http://localhost:5173"]

  # Email channel
  email:
    enabled: true
    provider: sendgrid # or ses, mailgun
    from_address: "noreply@example.com"
    template_dir: "./templates/email"

  # Push notifications
  push:
    enabled: false
    provider: firebase # or onesignal
    credentials_path: "./firebase-credentials.json"

  # Retention
  retention:
    read: 2592000 # 30 days
    unread: 7776000 # 90 days
```

### Integration Points

#### Backend Integration
```python
from notification_service import notifications

async def notify_transcript_complete(user_id: str, transcript_id: str):
    await notifications.send(
        Notification(
            type=NotificationType.SUCCESS,
            title="Transcription Complete",
            message=f"Your transcript {transcript_id} is ready",
            user_id=user_id,
            category="transcription",
            action_url=f"/transcripts/{transcript_id}",
            action_label="View Transcript",
            channels=[NotificationChannel.IN_APP, NotificationChannel.EMAIL]
        )
    )
```

#### Frontend Integration
```typescript
import { useNotifications, NotificationList } from '@modules/notifications'

function App() {
  return (
    <NotificationList />
  )
}

// Custom hook
function useNotifications() {
  const [notifications, setNotifications] = useState<Notification[]>([])

  useEffect(() => {
    const unsubscribe = notificationService.subscribe(
      userId,
      (notification) => {
        setNotifications(prev => [notification, ...prev])
      }
    )

    return unsubscribe
  }, [userId])

  return { notifications }
}
```

---

## 3. Job Queue Module

### Purpose
Process background tasks asynchronously with support for retries, prioritization, and distributed workers.

### Scope
- Background job processing
- Job status tracking
- Job retry with exponential backoff
- Job prioritization
- Job cancellation
- Scheduled jobs
- Job monitoring and metrics

### Interface/Contract

#### TypeScript/JavaScript (Bull/Agenda style)
```typescript
interface JobQueue {
  // Enqueue a job
  enqueue(name: string, data: any, options?: JobOptions): Promise<Job>

  // Schedule a job for later
  schedule(name: string, data: any, date: Date, options?: JobOptions): Promise<Job>

  // Get job by ID
  getJob(jobId: string): Promise<Job>

  // Get jobs with filters
  getJobs(filters?: JobFilters): Promise<Job[]>

  // Cancel a job
  cancelJob(jobId: string): Promise<void>

  // Remove a job
  removeJob(jobId: string): Promise<void>

  // Process jobs (worker)
  process(name: string, handler: JobHandler, options?: ProcessOptions): void

  // Get queue stats
  getStats(): Promise<QueueStats>
}

interface Job {
  id: string
  name: string
  data: any
  status: 'pending' | 'active' | 'completed' | 'failed' | 'delayed'
  priority: number
  attempts: number
  maxAttempts: number
  createdAt: Date
  processedAt?: Date
  completedAt?: Date
  failedAt?: Date
  result?: any
  error?: Error
}

interface JobOptions {
  priority?: number
  delay?: number // milliseconds
  attempts?: number
  backoff?: 'fixed' | 'exponential'
  timeout?: number // milliseconds
}

type JobHandler = (job: Job) => Promise<any>
```

#### Python (Celery/Arq style)
```python
from dataclasses import dataclass
from typing import Any, Callable, Optional
from datetime import datetime
from enum import Enum

class JobStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

@dataclass
class Job:
    id: str
    name: str
    status: JobStatus
    data: dict
    priority: int
    attempts: int
    max_attempts: int
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Optional[Any] = None
    error: Optional[str] = None

class JobQueue:
    async def enqueue(
        self,
        name: str,
        data: dict,
        priority: int = 0,
        delay: int = 0,
        max_attempts: int = 3
    ) -> Job:
        """Enqueue a job"""
        pass

    async def schedule(
        self,
        name: str,
        data: dict,
        scheduled_at: datetime,
        **kwargs
    ) -> Job:
        """Schedule a job for later execution"""
        pass

    async def get_job(self, job_id: str) -> Optional[Job]:
        """Get job by ID"""
        pass

    async def cancel_job(self, job_id: str) -> bool:
        """Cancel a job"""
        pass

    def worker(self, queue_name: str = "default"):
        """Decorator to register a job handler"""
        def decorator(func: Callable):
            self._register_handler(queue_name, func)
            return func
        return decorator
```

### Dependencies
- Message broker (Redis, RabbitMQ, SQS)
- Worker processes
- Monitoring backend (optional)

### Configuration Options
```yaml
job_queue:
  # Broker
  broker:
    type: redis # or rabbitmq, sqs
    connection_string: "${REDIS_URL}"

  # Queues
  queues:
    default:
      priority: 0
      workers: 4
    high_priority:
      priority: 10
      workers: 2
    low_priority:
      priority: -10
      workers: 1

  # Job defaults
  defaults:
    max_attempts: 3
    backoff: exponential
    timeout: 300 # seconds

  # Scheduled jobs
  scheduler:
    enabled: true
    timezone: "UTC"

  # Monitoring
  monitoring:
    enabled: true
    metrics_port: 9090
```

### Integration Points

#### Backend Integration
```python
from job_queue import queue

@queue.worker("transcription")
async def process_transcription(job: Job):
    file_id = job.data["file_id"]
    # Process transcription
    result = await transcribe_file(file_id)
    return result

# Enqueue a job
async def start_transcription(file_id: str):
    job = await queue.enqueue(
        "transcription",
        {"file_id": file_id},
        priority=5
    )
    return job.id
```

#### Monitoring Integration
```python
from job_queue import queue

async def get_queue_stats():
    stats = await queue.get_stats()
    return {
        "pending": stats.pending,
        "processing": stats.processing,
        "completed": stats.completed,
        "failed": stats.failed,
        "workers": stats.workers
    }
```

---

## 4. Cache Module

### Purpose
Improve application performance through intelligent caching with multiple strategies and invalidation patterns.

### Scope
- Multi-level caching (L1: memory, L2: Redis)
- TTL-based expiration
- Tag-based invalidation
- Cache-aside pattern
- Write-through caching (optional)
- Cache warming
- Cache metrics

### Interface/Contract

#### TypeScript/JavaScript
```typescript
interface CacheProvider {
  // Get value from cache
  get<T>(key: string): Promise<T | null>

  // Set value in cache
  set(key: string, value: any, options?: CacheOptions): Promise<void>

  // Get or set (cache aside)
  getOrSet<T>(key: string, factory: () => Promise<T>, options?: CacheOptions): Promise<T>

  // Delete key
  delete(key: string): Promise<void>

  // Delete by pattern
  deletePattern(pattern: string): Promise<void>

  // Invalidate by tags
  invalidate(tags: string[]): Promise<void>

  // Clear all cache
  clear(): Promise<void>

  // Get cache stats
  getStats(): Promise<CacheStats>
}

interface CacheOptions {
  ttl?: number // seconds
  tags?: string[]
  compress?: boolean
}

interface CacheStats {
  hits: number
  misses: number
  hitRate: number
  size: number
  keys: number
}
```

#### Python
```python
from dataclasses import dataclass
from typing import Any, Optional, List, Callable
from datetime import timedelta

@dataclass
class CacheOptions:
    ttl: Optional[int] = None # seconds
    tags: Optional[List[str]] = None
    compress: bool = False

@dataclass
class CacheStats:
    hits: int
    misses: int
    hit_rate: float
    size: int
    keys: int

class CacheProvider:
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        pass

    async def set(self, key: str, value: Any, options: Optional[CacheOptions] = None) -> None:
        """Set value in cache"""
        pass

    async def get_or_set(
        self,
        key: str,
        factory: Callable,
        options: Optional[CacheOptions] = None
    ) -> Any:
        """Get or set using factory function"""
        pass

    async def delete(self, key: str) -> None:
        """Delete key from cache"""
        pass

    async def delete_pattern(self, pattern: str) -> None:
        """Delete keys matching pattern"""
        pass

    async def invalidate(self, tags: List[str]) -> None:
        """Invalidate cache by tags"""
        pass

    async def clear(self) -> None:
        """Clear all cache"""
        pass

    async def get_stats(self) -> CacheStats:
        """Get cache statistics"""
        pass

    # Decorator for caching function results
    def cached(self, ttl: int = 300, tags: Optional[List[str]] = None):
        """Decorator to cache function results"""
        def decorator(func: Callable):
            async def wrapper(*args, **kwargs):
                cache_key = self._make_key(func.__name__, args, kwargs)
                return await self.get_or_set(
                    cache_key,
                    lambda: func(*args, **kwargs),
                    CacheOptions(ttl=ttl, tags=tags)
                )
            return wrapper
        return decorator
```

### Dependencies
- Redis (recommended for L2 cache)
- In-memory cache (node-cache, cachetools, etc.)

### Configuration Options
```yaml
cache:
  # L1: In-memory cache
  l1:
    enabled: true
    max_size: 1000 # number of items
    ttl: 60 # seconds

  # L2: Redis cache
  l2:
    enabled: true
    connection_string: "${REDIS_URL}"
    default_ttl: 3600 # 1 hour
    key_prefix: "cache:"

  # Compression
  compression:
    enabled: true
    threshold: 1024 # bytes

  # Metrics
  metrics:
    enabled: true
    collect_interval: 60 # seconds
```

### Integration Points

#### Backend Integration
```python
from cache import cache

# Using the decorator
@cache.cached(ttl=3600, tags=["transcripts"])
async def get_transcript(transcript_id: str):
    return await db.query(Transcript).filter_by(id=transcript_id).first()

# Using get_or_set
async def get_rag_results(query: str):
    return await cache.get_or_set(
        f"rag:{hash(query)}",
        lambda: perform_rag_search(query),
        CacheOptions(ttl=1800, tags=["rag"])
    )

# Manual cache operations
async def update_transcript(transcript_id: str, data: dict):
    result = await db.update(transcript_id, data)
    await cache.delete(f"transcript:{transcript_id}")
    await cache.invalidate(["transcripts"])
    return result
```

---

## 5. Export Module

### Purpose
Export data in multiple formats with support for templates and batch operations.

### Scope
- Multi-format export (TXT, JSON, SRT, DOCX, PDF)
- Template-based export
- Batch export with progress tracking
- Export job processing
- Export history and management

### Interface/Contract

#### TypeScript/JavaScript
```typescript
interface ExportService {
  // Create export job
  export(source: ExportSource, format: ExportFormat, options?: ExportOptions): Promise<ExportJob>

  // Get export job status
  getJob(jobId: string): Promise<ExportJob>

  // Download export
  download(jobId: string): Promise<Buffer>

  // List exports
  list(filters?: ExportFilters): Promise<ExportJob[]>

  // Cancel export
  cancel(jobId: string): Promise<void>

  // Register custom format
  registerFormat(format: ExportFormatDefinition): void
}

interface ExportJob {
  id: string
  status: 'pending' | 'processing' | 'completed' | 'failed'
  format: ExportFormat
  source: ExportSource
  progress: number
  filePath?: string
  downloadUrl?: string
  expiresAt?: Date
  error?: string
  createdAt: Date
  completedAt?: Date
}

interface ExportSource {
  type: 'transcript' | 'summary' | 'rag' | 'custom'
  id: string
  data?: any
}

type ExportFormat = 'txt' | 'json' | 'srt' | 'docx' | 'pdf' | 'csv'

interface ExportOptions {
  template?: string
  includeMetadata?: boolean
  filename?: string
  ttl?: number // seconds until download link expires
}
```

#### Python
```python
from dataclasses import dataclass
from typing import Optional, List, Any, Dict
from enum import Enum
from datetime import datetime

class ExportFormat(str, Enum):
    TXT = "txt"
    JSON = "json"
    SRT = "srt"
    DOCX = "docx"
    PDF = "pdf"
    CSV = "csv"

@dataclass
class ExportSource:
    type: str
    id: str
    data: Optional[Dict[str, Any]] = None

@dataclass
class ExportJob:
    id: str
    status: str
    format: ExportFormat
    source: ExportSource
    progress: float
    file_path: Optional[str] = None
    download_url: Optional[str] = None
    expires_at: Optional[datetime] = None
    error: Optional[str] = None
    created_at: datetime = None
    completed_at: Optional[datetime] = None

@dataclass
class ExportOptions:
    template: Optional[str] = None
    include_metadata: bool = True
    filename: Optional[str] = None
    ttl: int = 86400 # 24 hours

class ExportService:
    async def export(
        self,
        source: ExportSource,
        format: ExportFormat,
        options: Optional[ExportOptions] = None
    ) -> ExportJob:
        """Create export job"""
        pass

    async def get_job(self, job_id: str) -> Optional[ExportJob]:
        """Get export job status"""
        pass

    async def download(self, job_id: str) -> bytes:
        """Download export file"""
        pass

    async def list_exports(
        self,
        user_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50
    ) -> List[ExportJob]:
        """List export jobs"""
        pass

    async def cancel(self, job_id: str) -> bool:
        """Cancel export job"""
        pass

    def register_format(self, format_def: 'ExportFormatDefinition') -> None:
        """Register custom export format"""
        pass
```

### Dependencies
- Document generators (python-docx, reportlab, etc.)
- Template engines (Jinja2, Handlebars)
- Storage backend (S3, local filesystem)
- Job queue (for async export)

### Configuration Options
```yaml
export:
  # Storage
  storage:
    type: local # or s3, gcs
    path: "./exports"
    public_url: "https://example.com/exports"

  # Formats
  formats:
    txt:
      enabled: true
      template_dir: "./templates/txt"
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

  # Job processing
  jobs:
    timeout: 300 # seconds
    max_size: 1073741824 # 1GB

  # Download links
  downloads:
    ttl: 86400 # 24 hours
    token_required: false
```

### Integration Points

#### Backend Integration
```python
from export_service import export_service

async def export_transcript(transcript_id: str, format: str):
    job = await export_service.export(
        source=ExportSource(type="transcript", id=transcript_id),
        format=ExportFormat(format),
        options=ExportOptions(
            filename=f"transcript_{transcript_id}",
            include_metadata=True
        )
    )
    return job.id

# Custom export format handler
@export_service.register_format
class CustomExporter:
    format = "custom"
    content_type = "text/plain"

    async def export(self, data: dict) -> str:
        # Custom export logic
        return formatted_data
```

---

## 6. Search Module

### Purpose
Provide vector-based semantic search with hybrid capabilities (vector + keyword) for intelligent content discovery.

### Scope
- Vector embeddings generation
- Vector similarity search
- Hybrid search (HNSW + BM25)
- Query expansion
- Search result filtering and faceting
- Search analytics

### Interface/Contract

#### TypeScript/JavaScript
```typescript
interface SearchService {
  // Index a document
  index(document: SearchDocument): Promise<void>

  // Batch index documents
  indexBatch(documents: SearchDocument[]): Promise<void>

  // Search
  search(query: SearchQuery): Promise<SearchResult[]>

  // Delete document
  delete(documentId: string): Promise<void>

  // Update document
  update(documentId: string, document: SearchDocument): Promise<void>

  // Get similar documents
  findSimilar(documentId: string, limit?: number): Promise<SearchResult[]>

  // Get search stats
  getStats(): Promise<SearchStats>
}

interface SearchDocument {
  id: string
  content: string
  metadata?: Record<string, any>
  embeddings?: number[]
}

interface SearchQuery {
  query: string
  filters?: Record<string, any>
  limit?: number
  threshold?: number
  hybrid?: boolean
  rerank?: boolean
  queryExpansion?: boolean
}

interface SearchResult {
  id: string
  score: number
  content: string
  metadata: Record<string, any>
  highlights?: string[]
}
```

#### Python
```python
from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from datetime import datetime

@dataclass
class SearchDocument:
    id: str
    content: str
    metadata: Optional[Dict[str, Any]] = None
    embeddings: Optional[List[float]] = None

@dataclass
class SearchQuery:
    query: str
    filters: Optional[Dict[str, Any]] = None
    limit: int = 10
    threshold: float = 0.5
    hybrid: bool = True
    rerank: bool = False
    query_expansion: bool = False

@dataclass
class SearchResult:
    id: str
    score: float
    content: str
    metadata: Dict[str, Any]
    highlights: Optional[List[str]] = None

@dataclass
class SearchStats:
    documents: int
    searches: int
    avg_latency: float
    cache_hit_rate: float

class SearchService:
    async def index(self, document: SearchDocument) -> None:
        """Index a single document"""
        pass

    async def index_batch(self, documents: List[SearchDocument]) -> None:
        """Index multiple documents"""
        pass

    async def search(self, query: SearchQuery) -> List[SearchResult]:
        """Perform search"""
        pass

    async def delete(self, document_id: str) -> None:
        """Delete document from index"""
        pass

    async def update(self, document_id: str, document: SearchDocument) -> None:
        """Update document in index"""
        pass

    async def find_similar(
        self,
        document_id: str,
        limit: int = 10
    ) -> List[SearchResult]:
        """Find similar documents"""
        pass

    async def get_stats(self) -> SearchStats:
        """Get search statistics"""
        pass
```

### Dependencies
- Vector database (Qdrant, Pinecone, Weaviate, pgvector)
- Embedding model (OpenAI, Cohere, local)
- Optional: Keyword search (Elasticsearch, Typesense)

### Configuration Options
```yaml
search:
  # Vector database
  vector_db:
    type: qdrant # or pinecone, weaviate, pgvector
    url: "${QDRANT_URL}"
    api_key: "${QDRANT_API_KEY}"
    collection: "documents"

  # Embeddings
  embeddings:
    provider: openai # or cohere, local
    model: "text-embedding-3-small"
    dimension: 1536
    batch_size: 100

  # Search settings
  search:
    default_limit: 10
    default_threshold: 0.5
    enable_hybrid: true
    enable_reranking: false
    enable_query_expansion: false

  # Cache
  cache:
    enabled: true
    ttl: 3600

  # Indexing
  indexing:
    batch_size: 100
    auto_index: true
```

### Integration Points

#### Backend Integration
```python
from search_service import search_service

# Index a document
async def index_transcript(transcript: Transcript):
    await search_service.index(
        SearchDocument(
            id=str(transcript.id),
            content=transcript.text,
            metadata={
                "language": transcript.language,
                "created_at": transcript.created_at.isoformat(),
                "duration": transcript.duration
            }
        )
    )

# Search
async def search_transcripts(query: str, filters: dict = None):
    results = await search_service.search(
        SearchQuery(
            query=query,
            filters=filters,
            limit=10,
            hybrid=True
        )
    )
    return results
```

---

## Module Usage Patterns

### Combining Modules

```python
# Progress tracking + Job Queue + Notifications
async def process_with_tracking(file_id: str):
    # Create progress tracker
    progress = await progress_tracker.create(id=file_id)

    # Enqueue job
    job = await job_queue.enqueue("process", {"file_id": file_id})

    # Notify user
    await notification_service.send(
        Notification(
            type=NotificationType.INFO,
            title="Processing Started",
            user_id=user_id,
            channels=[NotificationChannel.IN_APP]
        )
    )

    return job.id
```

---

## Best Practices

1. **Interface First**: Define clear interfaces before implementation
2. **Dependency Injection**: Use DI for better testability
3. **Error Handling**: Implement consistent error handling across modules
4. **Logging**: Use structured logging with correlation IDs
5. **Metrics**: Collect metrics for all operations
6. **Testing**: Write tests for each module independently
7. **Documentation**: Keep API documentation in sync with code
