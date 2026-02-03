# Design Patterns Documentation

This document describes the key design patterns used in the modular implementation, making them reusable across different IT applications.

## Pattern Catalog

| Pattern | Purpose | Complexity | Use Case |
|---------|---------|------------|----------|
| Progress Tracking | Track long-running operations | Medium | File uploads, batch processing |
| Real-time Notification | Push updates to clients | Medium | Status changes, alerts |
| Async Job Processing | Background task execution | High | Heavy computations, IO operations |
| Cache Invalidation | Keep data fresh | Medium | Read-heavy workloads |
| Export Service | Multi-format data export | Medium | Reports, data exports |
| Vector Search | Semantic content search | High | RAG, recommendations |

---

## 1. Progress Tracking Pattern

### Intent
Provide real-time feedback to users for long-running operations while maintaining clean separation of concerns.

### Context
- Long-running operations (file uploads, data processing, batch jobs)
- Need for user feedback during execution
- Multi-stage operations with different phases
- Potential for failures requiring recovery

### Structure

```
+----------------+       +---------------------+       +----------------+
|    Client      |------>|  ProgressController |------>| ProgressStorage |
+----------------+       +---------------------+       +----------------+
                                |
                                v
                        +-------------------+
                        |  ProgressEmitter  |
                        +-------------------+
                                |
                                v
                        +-------------------+
                        | WebSocket/EventBus |
                        +-------------------+
```

### Participants

1. **ProgressController** - Manages progress state
2. **ProgressStorage** - Persists progress data
3. **ProgressEmitter** - Broadcasts progress updates
4. **Client** - Consumes progress updates

### Implementation

#### Python Implementation
```python
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, List, Callable, Dict, Any
from datetime import datetime
import asyncio

class ProgressStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

@dataclass
class ProgressStage:
    name: str
    status: ProgressStatus = ProgressStatus.PENDING
    progress: float = 0.0
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None

@dataclass
class Progress:
    id: str
    status: ProgressStatus = ProgressStatus.PENDING
    progress: float = 0.0
    stages: List[ProgressStage] = field(default_factory=list)
    current_stage: int = 0
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None

    # Internal callbacks
    _on_update: Optional[Callable[[Progress], None]] = None

    def set_callback(self, callback: Callable[[Progress], None]):
        """Set callback for progress updates"""
        self._on_update = callback

    async def update(self, progress: float, stage: Optional[str] = None):
        """Update progress"""
        self.progress = min(100, max(0, progress))
        self.updated_at = datetime.utcnow()

        if stage and self.stages:
            for s in self.stages:
                if s.name == stage:
                    s.progress = self.progress
                    s.status = ProgressStatus.PROCESSING
                    if s.started_at is None:
                        s.started_at = datetime.utcnow()
                    break

        if self._on_update:
            await self._on_update(self)

    async def advance_stage(self):
        """Move to next stage"""
        if self.current_stage < len(self.stages):
            # Complete current stage
            if self.stages:
                self.stages[self.current_stage].status = ProgressStatus.COMPLETED
                self.stages[self.current_stage].completed_at = datetime.utcnow()

            self.current_stage += 1

            # Start next stage
            if self.current_stage < len(self.stages):
                self.stages[self.current_stage].status = ProgressStatus.PROCESSING
                self.stages[self.current_stage].started_at = datetime.utcnow()

    async def complete(self):
        """Mark progress as complete"""
        self.status = ProgressStatus.COMPLETED
        self.progress = 100.0
        self.completed_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()

        if self._on_update:
            await self._on_update(self)

    async def fail(self, error: str):
        """Mark progress as failed"""
        self.status = ProgressStatus.FAILED
        self.error = error
        self.updated_at = datetime.utcnow()

        if self.stages and self.current_stage < len(self.stages):
            self.stages[self.current_stage].status = ProgressStatus.FAILED
            self.stages[self.current_stage].error = error

        if self._on_update:
            await self._on_update(self)

class ProgressTracker:
    def __init__(self, storage, emitter):
        self._storage = storage
        self._emitter = emitter
        self._active: Dict[str, Progress] = {}

    async def create(
        self,
        id: str,
        stages: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Progress:
        """Create a new progress tracker"""
        progress = Progress(
            id=id,
            metadata=metadata or {}
        )

        if stages:
            progress.stages = [ProgressStage(name=name) for name in stages]

        # Set up callback for real-time updates
        progress.set_callback(self._on_progress_update)

        # Store progress
        await self._storage.save(progress)
        self._active[id] = progress

        return progress

    async def get(self, id: str) -> Optional[Progress]:
        """Get progress by ID"""
        if id in self._active:
            return self._active[id]
        return await self._storage.load(id)

    async def update(self, id: str, progress: float, stage: Optional[str] = None):
        """Update progress"""
        tracker = await self.get(id)
        if tracker:
            await tracker.update(progress, stage)

    async def complete(self, id: str):
        """Complete progress"""
        tracker = await self.get(id)
        if tracker:
            await tracker.complete()
            await self._storage.save(tracker)

    async def fail(self, id: str, error: str):
        """Fail progress"""
        tracker = await self.get(id)
        if tracker:
            await tracker.fail(error)
            await self._storage.save(tracker)

    async def _on_progress_update(self, progress: Progress):
        """Handle progress updates"""
        # Persist to storage
        await self._storage.save(progress)

        # Emit to clients
        await self._emitter.emit(progress.id, progress)

    async def cleanup(self, id: str):
        """Clean up completed progress"""
        if id in self._active:
            del self._active[id]
```

#### TypeScript Implementation
```typescript
interface ProgressCallback {
  (progress: Progress): void | Promise<void>;
}

interface ProgressOptions {
  id: string;
  stages?: string[];
  metadata?: Record<string, any>;
}

class Progress {
  public readonly id: string;
  public status: 'pending' | 'processing' | 'completed' | 'failed';
  public progress: number;
  public stages: ProgressStage[];
  public currentStage: number;
  public error?: string;
  public metadata: Record<string, any>;
  public createdAt: Date;
  public updatedAt: Date;
  public completedAt?: Date;

  private onUpdate?: ProgressCallback;

  constructor(options: ProgressOptions) {
    this.id = options.id;
    this.status = 'pending';
    this.progress = 0;
    this.stages = (options.stages || []).map(name => new ProgressStage(name));
    this.currentStage = 0;
    this.metadata = options.metadata || {};
    this.createdAt = new Date();
    this.updatedAt = new Date();
  }

  setCallback(callback: ProgressCallback) {
    this.onUpdate = callback;
  }

  async update(progress: number, stage?: string) {
    this.progress = Math.min(100, Math.max(0, progress));
    this.updatedAt = new Date();

    if (stage && this.stages.length > 0) {
      const stageObj = this.stages.find(s => s.name === stage);
      if (stageObj) {
        stageObj.progress = this.progress;
        stageObj.status = 'processing';
        if (!stageObj.startedAt) {
          stageObj.startedAt = new Date();
        }
      }
    }

    if (this.onUpdate) {
      await this.onUpdate(this);
    }
  }

  async advanceStage() {
    if (this.currentStage < this.stages.length) {
      // Complete current
      this.stages[this.currentStage].status = 'completed';
      this.stages[this.currentStage].completedAt = new Date();

      // Start next
      this.currentStage++;
      if (this.currentStage < this.stages.length) {
        this.stages[this.currentStage].status = 'processing';
        this.stages[this.currentStage].startedAt = new Date();
      }
    }
  }

  async complete() {
    this.status = 'completed';
    this.progress = 100;
    this.completedAt = new Date();
    this.updatedAt = new Date();

    if (this.onUpdate) {
      await this.onUpdate(this);
    }
  }

  async fail(error: string) {
    this.status = 'failed';
    this.error = error;
    this.updatedAt = new Date();

    if (this.stages.length > 0 && this.currentStage < this.stages.length) {
      this.stages[this.currentStage].status = 'failed';
      this.stages[this.currentStage].error = error;
    }

    if (this.onUpdate) {
      await this.onUpdate(this);
    }
  }
}

class ProgressTracker {
  private storage: ProgressStorage;
  private emitter: ProgressEmitter;
  private active = new Map<string, Progress>();

  constructor(storage: ProgressStorage, emitter: ProgressEmitter) {
    this.storage = storage;
    this.emitter = emitter;
  }

  async create(options: ProgressOptions): Promise<Progress> {
    const progress = new Progress(options);
    progress.setCallback(async (p) => this.onUpdate(p));

    await this.storage.save(progress);
    this.active.set(options.id, progress);

    return progress;
  }

  async get(id: string): Promise<Progress | undefined> {
    if (this.active.has(id)) {
      return this.active.get(id);
    }
    return this.storage.load(id);
  }

  private async onUpdate(progress: Progress): Promise<void> {
    await this.storage.save(progress);
    await this.emitter.emit(progress.id, progress);
  }
}
```

### Usage Example

```python
# In your application handler
async def process_large_file(file_id: str):
    # Create progress tracker with stages
    progress = await tracker.create(
        id=file_id,
        stages=["upload", "transcribe", "process"],
        metadata={"file_name": file_id}
    )

    try:
        # Stage 1: Upload
        await tracker.update(file_id, 0, "upload")
        for chunk_progress in range(0, 101, 10):
            await upload_chunk()
            await tracker.update(file_id, chunk_progress, "upload")
        await tracker.advance_stage(file_id)

        # Stage 2: Transcribe
        for transcribe_progress in range(0, 101, 5):
            await do_transcription()
            await tracker.update(file_id, transcribe_progress, "transcribe")
        await tracker.advance_stage(file_id)

        # Complete
        await tracker.complete(file_id)

    except Exception as e:
        await tracker.fail(file_id, str(e))
```

### Consequences

**Benefits:**
- Clean separation between operation logic and progress reporting
- Real-time updates without polling
- Persistent progress tracking across restarts
- Easy to test and mock

**Liabilities:**
- Requires WebSocket infrastructure for real-time updates
- Additional storage overhead
- Complexity in distributed systems

---

## 2. Real-time Notification Pattern (WebSocket)

### Intent
Push real-time updates to connected clients without polling.

### Context
- Need for instant updates
- Multiple connected clients
- Event-driven architecture
- Stateful connections

### Structure

```
+--------+       +------------+       +-----------+       +--------+
| Client |<----->| WebSocket  |<----->| Event Bus |<----->| Events |
+--------+       +------------+       +-----------+       +--------+
                            |
                            v
                     +--------------+
                     | Notification |
                     |   Manager    |
                     +--------------+
                            |
                            v
                     +--------------+
                     |  Persistence |
                     +--------------+
```

### Implementation

#### Python (FastAPI + WebSocket)
```python
from fastapi import WebSocket
from typing import Dict, Set
import json
import asyncio

class WebSocketManager:
    def __init__(self):
        # Active connections: {user_id: Set[WebSocket]}
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        # Channel subscriptions: {channel: Set[user_id]}
        self.channel_subscribers: Dict[str, Set[str]] = {}

    async def connect(self, websocket: WebSocket, user_id: str):
        """Connect a client"""
        await websocket.accept()

        if user_id not in self.active_connections:
            self.active_connections[user_id] = set()

        self.active_connections[user_id].add(websocket)

    async def disconnect(self, websocket: WebSocket, user_id: str):
        """Disconnect a client"""
        if user_id in self.active_connections:
            self.active_connections[user_id].discard(websocket)

            # Clean up empty sets
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]

    async def send_personal(self, message: dict, user_id: str):
        """Send message to specific user"""
        if user_id in self.active_connections:
            disconnected = set()

            for websocket in self.active_connections[user_id]:
                try:
                    await websocket.send_json(message)
                except Exception:
                    disconnected.add(websocket)

            # Clean up disconnected websockets
            for ws in disconnected:
                await self.disconnect(ws, user_id)

    async def broadcast(self, message: dict, channel: str = None):
        """Broadcast message to channel or all users"""
        if channel and channel in self.channel_subscribers:
            # Send to channel subscribers
            for user_id in self.channel_subscribers[channel]:
                await self.send_personal(message, user_id)
        else:
            # Send to all connected users
            for user_id in self.active_connections:
                await self.send_personal(message, user_id)

    def subscribe(self, user_id: str, channel: str):
        """Subscribe user to channel"""
        if channel not in self.channel_subscribers:
            self.channel_subscribers[channel] = set()

        self.channel_subscribers[channel].add(user_id)

    def unsubscribe(self, user_id: str, channel: str):
        """Unsubscribe user from channel"""
        if channel in self.channel_subscribers:
            self.channel_subscribers[channel].discard(user_id)

# Global manager
manager = WebSocketManager()

# FastAPI endpoint
from fastapi import APIRoute

@route.get("/ws/notifications")
async def websocket_notifications(websocket: WebSocket, user_id: str):
    await manager.connect(websocket, user_id)

    try:
        while True:
            # Keep connection alive, handle incoming messages
            data = await websocket.receive_text()

            # Handle subscriptions, etc.
            message = json.loads(data)
            if message.get("action") == "subscribe":
                manager.subscribe(user_id, message["channel"])

    except Exception:
        await manager.disconnect(websocket, user_id)
```

#### TypeScript (React)
```typescript
class NotificationClient {
  private ws: WebSocket | null = null;
  private userId: string;
  private subscriptions = new Map<string, Set<MessageHandler>>();
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;

  constructor(userId: string, url: string) {
    this.userId = userId;
    this.connect(url);
  }

  private connect(url: string) {
    this.ws = new WebSocket(`${url}?user_id=${this.userId}`);

    this.ws.onopen = () => {
      console.log('WebSocket connected');
      this.reconnectAttempts = 0;
    };

    this.ws.onmessage = (event) => {
      const message = JSON.parse(event.data);
      this.handleMessage(message);
    };

    this.ws.onclose = () => {
      console.log('WebSocket disconnected');
      this.reconnect();
    };

    this.ws.onerror = (error) => {
      console.error('WebSocket error:', error);
    };
  }

  private reconnect() {
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      this.reconnectAttempts++;
      setTimeout(() => {
        console.log(`Reconnecting... (${this.reconnectAttempts})`);
        this.connect(this.ws!.url.split('?')[0]);
      }, 1000 * this.reconnectAttempts);
    }
  }

  private handleMessage(message: any) {
    const handlers = this.subscriptions.get(message.channel || 'default');
    handlers?.forEach(handler => handler(message));
  }

  subscribe(channel: string, handler: MessageHandler) {
    if (!this.subscriptions.has(channel)) {
      this.subscriptions.set(channel, new Set());
      // Tell server we want to subscribe
      this.send({ action: 'subscribe', channel });
    }
    this.subscriptions.get(channel)!.add(handler);
  }

  unsubscribe(channel: string, handler: MessageHandler) {
    const handlers = this.subscriptions.get(channel);
    if (handlers) {
      handlers.delete(handler);
      if (handlers.size === 0) {
        this.subscriptions.delete(channel);
        this.send({ action: 'unsubscribe', channel });
      }
    }
  }

  private send(data: any) {
    this.ws?.readyState === WebSocket.OPEN &&
      this.ws?.send(JSON.stringify(data));
  }

  disconnect() {
    this.ws?.close();
  }
}

// Usage in React
function useNotifications(userId: string) {
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const client = useRef<NotificationClient>();

  useEffect(() => {
    client.current = new NotificationClient(
      userId,
      'ws://localhost:8000/ws/notifications'
    );

    client.current.subscribe('default', (message) => {
      if (message.type === 'notification') {
        setNotifications(prev => [message.data, ...prev]);
      }
    });

    return () => {
      client.current?.disconnect();
    };
  }, [userId]);

  return { notifications };
}
```

### Consequences

**Benefits:**
- Real-time updates without polling overhead
- Reduced server load compared to polling
- Better user experience
- Scalable with proper architecture

**Liabilities:**
- Maintaining connection state
- Handling reconnections
- More complex than polling
- Requires sticky sessions in some load balancers

---

## 3. Async Job Processing Pattern

### Intent
Process tasks asynchronously in the background with support for retries, scheduling, and distributed execution.

### Context
- Long-running tasks
- Need for fault tolerance
- Scheduled operations
- Resource-intensive processing

### Structure

```
+--------+       +------------+       +-------+       +-----------+
| Client |------>| Job Queue  |------>| Worker |------>| Handler   |
+--------+       +------------+       +-------+       +-----------+
                      |
                      v
               +--------------+
               |  Job Storage |
               +--------------+
                      |
                      v
               +--------------+
               |  Monitoring  |
               +--------------+
```

### Implementation

#### Python (Celery-style)
```python
import asyncio
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Optional
from datetime import datetime
from enum import Enum
import uuid
import json

class JobStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRYING = "retrying"

@dataclass
class Job:
    id: str
    name: str
    payload: Dict[str, Any]
    status: JobStatus = JobStatus.PENDING
    priority: int = 0
    attempts: int = 0
    max_attempts: int = 3
    result: Optional[Any] = None
    error: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    scheduled_at: Optional[datetime] = None

class JobQueue:
    def __init__(self, storage, broker):
        self.storage = storage
        self.broker = broker
        self.handlers: Dict[str, Callable] = {}

    def register_handler(self, name: str, handler: Callable):
        """Register a job handler"""
        self.handlers[name] = handler

    async def enqueue(
        self,
        name: str,
        payload: Dict[str, Any],
        priority: int = 0,
        delay: Optional[int] = None,
        max_attempts: int = 3
    ) -> Job:
        """Enqueue a job"""
        job = Job(
            id=str(uuid.uuid4()),
            name=name,
            payload=payload,
            priority=priority,
            max_attempts=max_attempts
        )

        if delay:
            job.scheduled_at = datetime.utcnow()

        await self.storage.save(job)
        await self.broker.enqueue(job)

        return job

    async def dequeue(self, queues: Optional[List[str]] = None) -> Optional[Job]:
        """Dequeue next job"""
        return await self.broker.dequeue(queues)

    async def process(self, job: Job) -> Job:
        """Process a job"""
        if job.name not in self.handlers:
            job.status = JobStatus.FAILED
            job.error = f"No handler registered for {job.name}"
            await self.storage.save(job)
            return job

        job.status = JobStatus.PROCESSING
        job.started_at = datetime.utcnow()
        await self.storage.save(job)

        try:
            handler = self.handlers[job.name]
            result = await handler(**job.payload)

            job.status = JobStatus.COMPLETED
            job.result = result
            job.completed_at = datetime.utcnow()

        except Exception as e:
            job.attempts += 1

            if job.attempts < job.max_attempts:
                # Retry with exponential backoff
                job.status = JobStatus.RETRYING
                delay = 2 ** job.attempts
                job.scheduled_at = datetime.utcnow()

                await asyncio.sleep(delay)
                await self.broker.enqueue(job)
            else:
                job.status = JobStatus.FAILED
                job.error = str(e)
                job.completed_at = datetime.utcnow()

        await self.storage.save(job)
        return job

    async def cancel(self, job_id: str) -> bool:
        """Cancel a job"""
        job = await self.storage.load(job_id)
        if job and job.status in [JobStatus.PENDING, JobStatus.RETRYING]:
            job.status = JobStatus.CANCELLED
            await self.storage.save(job)
            return True
        return False

    async def get_status(self, job_id: str) -> Optional[Job]:
        """Get job status"""
        return await self.storage.load(job_id)
```

#### Usage
```python
# Define job handlers
queue = JobQueue(storage, broker)

@queue.register_handler("transcribe")
async def transcribe_handler(file_id: str):
    # Transcribe file
    return await transcribe_file(file_id)

@queue.register_handler("send_email")
async def send_email_handler(to: str, subject: str, body: str):
    # Send email
    return await send_email(to, subject, body)

# Enqueue jobs
async def process_upload(file_id: str, user_id: str):
    # Enqueue transcription
    job1 = await queue.enqueue("transcribe", {"file_id": file_id})

    # Enqueue notification email
    job2 = await queue.enqueue(
        "send_email",
        {"to": user_id, "subject": "Transcription Complete"},
        delay=3600  # Send in 1 hour
    )

    return job1.id, job2.id

# Worker process
async def worker(queues: List[str] = None):
    while True:
        job = await queue.dequeue(queues)
        if job:
            await queue.process(job)
        else:
            await asyncio.sleep(0.1)
```

### Consequences

**Benefits:**
- Fault tolerance with retries
- Distributed processing
- Job scheduling
- Priority handling

**Liabilities:**
- Additional infrastructure (broker, storage)
- Monitoring complexity
- Dead letter handling

---

## 4. Cache Invalidation Pattern

### Intent
Keep cached data consistent with source of truth while maximizing cache hit rate.

### Context
- Read-heavy workloads
- Expensive computations/queries
- Data that changes infrequently
- Need for eventual consistency

### Strategies

### 1. Time-Based Expiration (TTL)

```python
# Simple TTL-based caching
@cached(ttl=3600)  # Cache for 1 hour
async def get_user(user_id: str):
    return await db.query(User).filter_by(id=user_id).first()
```

### 2. Event-Based Invalidation

```python
class CacheInvalidator:
    def __init__(self, cache, event_bus):
        self.cache = cache
        self.event_bus = event_bus

    async def on_data_changed(self, event: DataChangedEvent):
        """Invalidate cache when data changes"""
        if event.entity_type == "user":
            await self.cache.delete(f"user:{event.entity_id}")

        if event.tags:
            await self.cache.invalidate(event.tags)
```

### 3. Cache-Aside Pattern

```python
async def get_with_cache(key: str, factory: Callable):
    """Get from cache or compute and cache"""
    # Try cache first
    value = await cache.get(key)
    if value is not None:
        return value

    # Compute value
    value = await factory()

    # Store in cache
    await cache.set(key, value, ttl=3600)

    return value
```

### 4. Write-Through Pattern

```python
async def update_with_write_through(key: str, value: any):
    """Update both cache and storage"""
    # Update storage first
    await storage.update(key, value)

    # Then update cache
    await cache.set(key, value, ttl=3600)
```

### 5. Tag-Based Invalidation

```python
# Store with tags
await cache.set("user:123", user_data, tags=["user", "profile"])

# Invalidate by tag
await cache.invalidate(["user"])  # Invalidates all entries with "user" tag
```

### Implementation

```python
from typing import Any, Callable, Optional, List
from dataclasses import dataclass
import hashlib
import json

@dataclass
class CacheOptions:
    ttl: int = 300
    tags: Optional[List[str]] = None
    key_prefix: str = ""

class CacheManager:
    def __init__(self, provider):
        self.provider = provider

    def make_key(self, prefix: str, *args, **kwargs) -> str:
        """Generate cache key from arguments"""
        key_parts = [prefix]

        # Add positional args
        key_parts.extend(str(a) for a in args)

        # Add keyword args (sorted for consistency)
        if kwargs:
            key_parts.append(json.dumps(kwargs, sort_keys=True))

        key = ":".join(key_parts)

        # Hash if too long
        if len(key) > 200:
            key = f"{prefix}:{hashlib.sha256(key.encode()).hexdigest()[:16]}"

        return key

    async def get_or_set(
        self,
        key: str,
        factory: Callable,
        options: Optional[CacheOptions] = None
    ) -> Any:
        """Get from cache or compute"""
        # Try cache
        value = await self.provider.get(key)
        if value is not None:
            return value

        # Compute
        value = await factory()

        # Cache
        await self.provider.set(
            key,
            value,
            ttl=options.ttl if options else 300,
            tags=options.tags if options else None
        )

        return value

    def cached(self, prefix: str, ttl: int = 300, tags: Optional[List[str]] = None):
        """Decorator for caching"""
        def decorator(func: Callable):
            async def wrapper(*args, **kwargs):
                key = self.make_key(prefix, *args, **kwargs)

                return await self.get_or_set(
                    key,
                    lambda: func(*args, **kwargs),
                    CacheOptions(ttl=ttl, tags=tags)
                )
            return wrapper
        return decorator
```

### Usage

```python
cache = CacheManager(redis_provider)

# Using decorator
@cache.cached("user", ttl=3600, tags=["user"])
async def get_user(user_id: str):
    return await db.query(User).filter_by(id=user_id).first()

# Manual invalidation
async def update_user(user_id: str, data: dict):
    await db.update(User, user_id, data)
    await cache.provider.invalidate(["user"])

# Tag-based multi-key invalidation
await cache.provider.set("user:123", data, tags=["user", "profile"])
await cache.provider.set("user:456", data, tags=["user", "profile"])
await cache.provider.invalidate(["user"])  # Invalidates both
```

---

## 5. Export Service Pattern

### Intent
Provide flexible multi-format data export with template support and async processing.

### Context
- Multiple export formats required
- Large datasets requiring async processing
- Customizable output templates
- Batch export operations

### Structure

```
+--------+       +-------------+       +-----------+       +--------+
| Client |------>| Export Queue|------>| Exporter  |------>| Format |
+--------+       +-------------+       +-----------+       +--------+
                                              |
                                              v
                                       +-----------+
                                       | Template |
                                       +-----------+
                                              |
                                              v
                                       +-----------+
                                       | Storage   |
                                       +-----------+
```

### Implementation

```python
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import io

class ExportFormat(ABC):
    """Base class for export formats"""

    @property
    @abstractmethod
    def extension(self) -> str:
        pass

    @property
    @abstractmethod
    def mime_type(self) -> str:
        pass

    @abstractmethod
    async def export(self, data: Any, template: Optional[str] = None) -> bytes:
        pass

class TxtExportFormat(ExportFormat):
    extension = "txt"
    mime_type = "text/plain"

    async def export(self, data, template=None) -> bytes:
        if template:
            # Use template
            rendered = self._render_template(template, data)
        else:
            rendered = str(data)

        return rendered.encode('utf-8')

class JsonExportFormat(ExportFormat):
    extension = "json"
    mime_type = "application/json"

    async def export(self, data, template=None) -> bytes:
        import json
        return json.dumps(data, indent=2, ensure_ascii=False).encode('utf-8')

class SrtExportFormat(ExportFormat):
    extension = "srt"
    mime_type = "text/plain"

    async def export(self, data, template=None) -> bytes:
        """Export transcript segments as SRT"""
        lines = []
        for i, segment in enumerate(data.get('segments', []), 1):
            lines.append(str(i))
            lines.append(f"{segment['start']} --> {segment['end']}")
            lines.append(segment['text'])
            lines.append('')

        return '\n'.join(lines).encode('utf-8')

class ExportService:
    def __init__(self, storage, queue):
        self.storage = storage
        self.queue = queue
        self.formats: Dict[str, ExportFormat] = {}
        self._register_default_formats()

    def _register_default_formats(self):
        self.register_format('txt', TxtExportFormat())
        self.register_format('json', JsonExportFormat())
        self.register_format('srt', SrtExportFormat())

    def register_format(self, name: str, format: ExportFormat):
        """Register custom format"""
        self.formats[name] = format

    async def export(
        self,
        source_type: str,
        source_id: str,
        format: str,
        template: Optional[str] = None,
        async_mode: bool = True
    ) -> ExportJob:
        """Create export job"""
        if format not in self.formats:
            raise ValueError(f"Unknown format: {format}")

        job = ExportJob(
            id=str(uuid.uuid4()),
            source_type=source_type,
            source_id=source_id,
            format=format
        )

        if async_mode:
            # Queue for background processing
            await self.queue.enqueue('export', {
                'job_id': job.id,
                'source_type': source_type,
                'source_id': source_id,
                'format': format,
                'template': template
            })
        else:
            # Process synchronously
            await self._process_job(job, template)

        return job

    async def _process_job(self, job: ExportJob, template: Optional[str] = None):
        """Process export job"""
        job.status = 'processing'

        try:
            # Get source data
            data = await self._get_source_data(job.source_type, job.source_id)

            # Export
            formatter = self.formats[job.format]
            content = await formatter.export(data, template)

            # Store
            filename = f"{job.source_type}_{job.source_id}.{formatter.extension}"
            path = await self.storage.save(filename, content, formatter.mime_type)

            job.status = 'completed'
            job.file_path = path
            job.download_url = self.storage.get_url(path)

        except Exception as e:
            job.status = 'failed'
            job.error = str(e)
```

### Usage

```python
export_service = ExportService(storage, queue)

# Export transcript to SRT
job = await export_service.export(
    source_type='transcript',
    source_id='abc123',
    format='srt'
)

# Custom format
@dataclass
class CsvExportFormat(ExportFormat):
    extension = "csv"
    mime_type = "text/csv"

    async def export(self, data, template=None) -> bytes:
        import csv
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=data[0].keys())
        writer.writeheader()
        writer.writerows(data)
        return output.getvalue().encode('utf-8')

export_service.register_format('csv', CsvExportFormat())
```

---

## 6. Vector Search Pattern

### Intent
Provide semantic search capabilities using vector embeddings for intelligent content discovery.

### Context
- Large document collections
- Need for semantic similarity
- RAG applications
- Recommendation systems

### Structure

```
+--------+       +-------------+       +-----------+       +-------+
| Client |------>| Search Query|------>| Search    |------>| Vector |
|        |       | Processor   |       | Service   |       | Store |
+--------+       +-------------+       +-----------+       +-------+
                                              |
                                              v
                                       +-----------+
                                       | Embedding |
                                       +-----------+
```

### Implementation

```python
from typing import List, Optional, Dict, Any
from dataclasses import dataclass

@dataclass
class SearchQuery:
    query: str
    filters: Optional[Dict[str, Any]] = None
    limit: int = 10
    threshold: float = 0.5
    hybrid: bool = True  # Vector + keyword

@dataclass
class SearchResult:
    id: str
    score: float
    content: str
    metadata: Dict[str, Any]
    highlights: Optional[List[str]] = None

class SearchService:
    def __init__(self, vector_store, embedding_service):
        self.vector_store = vector_store
        self.embedding = embedding_service

    async def index(self, document: SearchDocument):
        """Index a document"""
        # Generate embeddings
        embeddings = await self.embedding.embed(document.content)

        # Store in vector database
        await self.vector_store.upsert(
            id=document.id,
            vector=embeddings,
            payload={
                'content': document.content,
                'metadata': document.metadata or {}
            }
        )

    async def search(self, query: SearchQuery) -> List[SearchResult]:
        """Perform search"""
        # Generate query embeddings
        query_vector = await self.embedding.embed(query.query)

        if query.hybrid:
            # Hybrid search: vector + keyword
            results = await self._hybrid_search(query, query_vector)
        else:
            # Vector only
            results = await self._vector_search(query, query_vector)

        # Apply filters
        if query.filters:
            results = self._apply_filters(results, query.filters)

        # Apply threshold
        results = [r for r in results if r.score >= query.threshold]

        return results[:query.limit]

    async def _vector_search(
        self,
        query: SearchQuery,
        query_vector: List[float]
    ) -> List[SearchResult]:
        """Vector similarity search"""
        search_result = await self.vector_store.search(
            vector=query_vector,
            limit=query.limit * 2  # Get more for filtering
        )

        results = []
        for match in search_result:
            results.append(SearchResult(
                id=match.id,
                score=match.score,
                content=match.payload['content'],
                metadata=match.payload.get('metadata', {})
            ))

        return results

    async def _hybrid_search(
        self,
        query: SearchQuery,
        query_vector: List[float]
    ) -> List[SearchResult]:
        """Hybrid search combining vector and keyword"""
        # Vector search
        vector_results = await self._vector_search(query, query_vector)

        # Keyword search (BM25)
        keyword_results = await self._keyword_search(query.query)

        # Reciprocal rank fusion
        results = self._reciprocal_rank_fusion(vector_results, keyword_results)

        return results

    def _reciprocal_rank_fusion(
        self,
        vector_results: List[SearchResult],
        keyword_results: List[SearchResult],
        k: int = 60
    ) -> List[SearchResult]:
        """Combine results using RRF"""
        scores = {}

        for rank, result in enumerate(vector_results, 1):
            scores[result.id] = scores.get(result.id, 0) + 1 / (k + rank)

        for rank, result in enumerate(keyword_results, 1):
            scores[result.id] = scores.get(result.id, 0) + 1 / (k + rank)

        # Create combined results
        all_results = {r.id: r for r in vector_results + keyword_results}
        sorted_ids = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)

        return [all_results[id] for id in sorted_ids]
```

### Usage

```python
search_service = SearchService(qdrant_store, openai_embeddings)

# Index documents
await search_service.index(SearchDocument(
    id="doc1",
    content="Transcription of meeting about Q4 planning",
    metadata={"date": "2024-01-15", "type": "meeting"}
))

# Search
results = await search_service.search(SearchQuery(
    query="quarterly planning",
    limit=5,
    threshold=0.7,
    hybrid=True
))
```

---

## Pattern Selection Guide

| Pattern | Use When | Complexity |
|---------|----------|------------|
| Progress Tracking | Operations > 5 seconds | Medium |
| Real-time Notification | Need instant updates | Medium |
| Async Job Processing | Heavy background tasks | High |
| Cache Invalidation | Read-heavy, slow compute | Medium |
| Export Service | Multiple output formats | Medium |
| Vector Search | Semantic content search | High |

---

## Best Practices

1. **Start Simple**: Implement the simplest pattern that meets requirements
2. **Measure First**: Add patterns based on actual performance needs
3. **Interface Segregation**: Define clear interfaces for each pattern
4. **Testability**: Make patterns easy to test and mock
5. **Observability**: Add metrics and logging for each pattern
