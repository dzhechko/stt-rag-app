# ADR-001: WebSocket for Real-time Progress Updates

| Status | Proposed by | Decision date | Effective date |
|--------|-------------|---------------|---------------|
| Accepted | System Architect | 2025-02-03 | 2025-02-03 |

---

## Context

The STT application processes large audio/video files that can take minutes to hours to transcribe. Users need visibility into progress to:
1. Know the system is working
2. Estimate when the task will complete
3. Plan their time accordingly
4. Receive notifications when complete

Current implementation uses HTTP polling, which:
- Creates unnecessary server load with frequent requests
- Has delay between updates (polling interval)
- Scales poorly with many concurrent users
- Wastes bandwidth when no progress has been made

## Decision

Use WebSocket connections for real-time, bidirectional progress updates between backend and frontend.

### Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        WebSocket Architecture                           │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─────────────────┐                                                    │
│  │   React UI      │                                                    │
│  │  ─────────────  │                                                    │
│  │  • Progress     │                                                    │
│  │    Component    │                                                    │
│  │  • Stage        │                                                    │
│  │    Indicator    │                                                    │
│  │  • Time         │                                                    │
│  │    Estimate     │                                                    │
│  └────────┬────────┘                                                    │
│           │                                                             │
│           │ WebSocket Connection                                        │
│           │ (ws://api.example.com/ws/progress/{taskId})                 │
│           │                                                             │
│           ▼                                                             │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                  WebSocket Manager                              │   │
│  │  ┌────────────────────────────────────────────────────────────┐ │   │
│  │  │ Connection Management:                                      │ │   │
│  │  │  • Establish connection                                     │ │   │
│  │  │  • Handle reconnection (exponential backoff)                │ │   │
│  │  │  • Heartbeat/ping-pong                                      │ │   │
│  │  │  • Graceful shutdown                                        │ │   │
│  │  └────────────────────────────────────────────────────────────┘ │   │
│  │  ┌────────────────────────────────────────────────────────────┐ │   │
│  │  │ Message Handling:                                           │ │   │
│  │  │  • Parse incoming messages                                  │ │   │
│  │  │  • Route to appropriate handlers                            │ │   │
│  │  │  • Emit domain events                                       │ │   │
│  │  └────────────────────────────────────────────────────────────┘ │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│           │                                                             │
│           │ Domain Events                                              │
│           │                                                             │
│           ▼                                                             │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                    State Management                             │   │
│  │  (React Query / Zustand)                                        │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### Message Protocol

#### Client → Server Messages

```typescript
// Subscribe to task progress
interface SubscribeMessage {
  type: "subscribe";
  taskId: string;
  token: string;  // JWT for authentication
}

// Unsubscribe from task
interface UnsubscribeMessage {
  type: "unsubscribe";
  taskId: string;
}

// Request current state
interface StateRequestMessage {
  type: "get_state";
  taskId: string;
}

// Heartbeat
interface PingMessage {
  type: "ping";
  timestamp: number;
}
```

#### Server → Client Messages

```typescript
// Progress update
interface ProgressUpdateMessage {
  type: "progress_update";
  taskId: string;
  payload: {
    percentage: number;
    stage: Stage;
    bytesProcessed?: number;
    bytesTotal?: number;
    processingSpeed?: number;
    timestamp: string;
  };
}

// Stage change
interface StageChangeMessage {
  type: "stage_change";
  taskId: string;
  payload: {
    fromStage: Stage;
    toStage: Stage;
    timestamp: string;
  };
}

// Time estimate update
interface TimeEstimateMessage {
  type: "time_estimate";
  taskId: string;
  payload: {
    estimatedTimeRemaining: number;
    confidence: number;
  };
}

// Completion
interface CompletionMessage {
  type: "complete";
  taskId: string;
  payload: {
    resultUrl: string;
    duration: number;
  };
}

// Error
interface ErrorMessage {
  type: "error";
  taskId: string;
  payload: {
    code: string;
    message: string;
  };
}

// Heartbeat response
interface PongMessage {
  type: "pong";
  timestamp: number;
}
```

### Implementation Details

#### Frontend WebSocket Manager

```typescript
class ProgressWebSocketManager {
  private ws: WebSocket | null = null;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectDelay = 1000;  // Start at 1 second
  private heartbeatInterval: NodeJS.Timeout | null = null;

  connect(taskId: string, token: string): void {
    const url = `wss://api.example.com/ws/progress/${taskId}`;
    this.ws = new WebSocket(url);

    this.ws.onopen = () => {
      console.log("WebSocket connected");
      this.reconnectAttempts = 0;
      this.reconnectDelay = 1000;

      // Subscribe to task
      this.send({
        type: "subscribe",
        taskId,
        token
      });

      // Start heartbeat
      this.startHeartbeat();
    };

    this.ws.onmessage = (event) => {
      const message = JSON.parse(event.data);
      this.handleMessage(message);
    };

    this.ws.onclose = () => {
      console.log("WebSocket disconnected");
      this.stopHeartbeat();
      this.attemptReconnect(taskId, token);
    };

    this.ws.onerror = (error) => {
      console.error("WebSocket error:", error);
    };
  }

  private handleMessage(message: ServerMessage): void {
    switch (message.type) {
      case "progress_update":
        this.eventBus.publish(new ProgressUpdatedEvent(message.payload));
        break;
      case "stage_change":
        this.eventBus.publish(new StageChangedEvent(message.payload));
        break;
      case "time_estimate":
        this.eventBus.publish(new TimeEstimateUpdatedEvent(message.payload));
        break;
      case "complete":
        this.eventBus.publish(new ProgressCompletedEvent(message.payload));
        break;
      case "error":
        this.eventBus.publish(new ProgressFailedEvent(message.payload));
        break;
    }
  }

  private startHeartbeat(): void {
    this.heartbeatInterval = setInterval(() => {
      this.send({ type: "ping", timestamp: Date.now() });
    }, 30000);  // Every 30 seconds
  }

  private attemptReconnect(taskId: string, token: string): void {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.error("Max reconnect attempts reached");
      // Fallback to polling
      this.fallbackToPolling(taskId);
      return;
    }

    this.reconnectAttempts++;
    const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1);

    setTimeout(() => {
      console.log(`Reconnecting... attempt ${this.reconnectAttempts}`);
      this.connect(taskId, token);
    }, delay);
  }

  private fallbackToPolling(taskId: string): void {
    // Implement polling as fallback
    console.log("Falling back to polling");
    this.pollingService.startPolling(taskId);
  }

  disconnect(): void {
    this.stopHeartbeat();
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }
}
```

#### Backend WebSocket Handler (FastAPI)

```python
from fastapi import WebSocket, WebSocketDisconnect, Depends
from typing import Dict, Set
import json
import asyncio

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, Set[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, task_id: str):
        await websocket.accept()
        if task_id not in self.active_connections:
            self.active_connections[task_id] = set()
        self.active_connections[task_id].add(websocket)

    def disconnect(self, websocket: WebSocket, task_id: str):
        if task_id in self.active_connections:
            self.active_connections[task_id].discard(websocket)
            if not self.active_connections[task_id]:
                del self.active_connections[task_id]

    async def send_progress_update(self, task_id: str, message: dict):
        if task_id in self.active_connections:
            disconnected = set()
            for connection in self.active_connections[task_id]:
                try:
                    await connection.send_json(message)
                except:
                    disconnected.add(connection)

            # Remove disconnected connections
            for conn in disconnected:
                self.disconnect(conn, task_id)

manager = ConnectionManager()

@app.websocket("/ws/progress/{task_id}")
async def progress_websocket(
    websocket: WebSocket,
    task_id: str,
    token: str = None
):
    await manager.connect(websocket, task_id)

    try:
        while True:
            data = await websocket.receive_json()

            if data["type"] == "subscribe":
                # Send current state immediately
                current_state = await get_task_progress(task_id)
                await websocket.send_json({
                    "type": "progress_update",
                    "taskId": task_id,
                    "payload": current_state
                })

            elif data["type"] == "ping":
                await websocket.send_json({
                    "type": "pong",
                    "timestamp": data["timestamp"]
                })

    except WebSocketDisconnect:
        manager.disconnect(websocket, task_id)

# Called by transcription service
async def broadcast_progress(task_id: str, progress: dict):
    await manager.send_progress_update(task_id, {
        "type": "progress_update",
        "taskId": task_id,
        "payload": progress
    })
```

## Alternatives Considered

### Alternative 1: HTTP Long Polling

**Description**: Client sends requests and server holds connection open until new data is available.

**Pros**:
- Simple to implement
- Works with standard HTTP
- No special infrastructure needed

**Cons**:
- Higher latency than WebSocket
- More server overhead (many open connections)
- Not truly real-time
- Wasted requests when no updates

**Rejected because**: WebSocket provides better real-time experience and lower server load.

### Alternative 2: Server-Sent Events (SSE)

**Description**: Unidirectional push from server to client over HTTP.

**Pros**:
- Simpler than WebSocket
- Uses standard HTTP
- Built-in reconnection support

**Cons**:
- Unidirectional only (server → client)
- No native support in all browsers
- Limited to text data

**Rejected because**: Need bidirectional communication for subscriptions and heartbeat.

### Alternative 3: Polling with Exponential Backoff

**Description**: Client polls server with increasing intervals between requests.

**Pros**:
- Simplest implementation
- Works everywhere
- Easy to cache

**Cons**:
- Not real-time
- Delay between updates
- Wasted bandwidth
- Server load from frequent requests

**Rejected because**: Poor user experience for long-running tasks.

## Consequences

### Positive

1. **Real-time updates**: Users see progress immediately
2. **Reduced server load**: No polling overhead
3. **Better UX**: Smooth, continuous progress updates
4. **Scalability**: More efficient use of connections
5. **Bidirectional**: Client can send messages too

### Negative

1. **Infrastructure complexity**: Requires WebSocket support
2. **Connection management**: Need to handle reconnections
3. **Load balancer configuration**: Must support WebSocket upgrades
4. **Fallback required**: Need polling backup for older browsers
5. **Testing complexity**: WebSocket testing is more complex

### Mitigations

1. Use battle-tested WebSocket libraries (Socket.IO, ws)
2. Implement robust reconnection logic
3. Use polling fallback for unsupported browsers
4. Add comprehensive monitoring for connection health
5. Document WebSocket requirements for deployment

## Implementation Roadmap

1. **Phase 1**: WebSocket backend endpoint
   - Implement FastAPI WebSocket handler
   - Add connection management
   - Create progress broadcast function

2. **Phase 2**: Frontend WebSocket client
   - Create WebSocket manager class
   - Implement message handlers
   - Add reconnection logic

3. **Phase 3**: Integration
   - Connect to React state management
   - Update UI components
   - Add error handling

4. **Phase 4**: Testing & Optimization
   - Load testing with concurrent connections
   - Monitor performance
   - Optimize message payloads

## References

- [RFC 6455 - WebSocket Protocol](https://datatracker.ietf.org/doc/html/rfc6455)
- [FastAPI WebSockets Documentation](https://fastapi.tiangolo.com/advanced/websockets/)
- [WebSocket API - MDN](https://developer.mozilla.org/en-US/docs/Web/API/WebSocket)

---

*End of ADR-001*
