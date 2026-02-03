# Pseudocode: WebSocket Message Handling
## Feature 1: UI/UX Improvements

| Version | Date | Author | Status |
|---------|------|--------|--------|
| 1.0 | 2025-02-03 | System Architect | Draft |

---

## 1. WebSocket Connection Management

### 1.1 Initialize Connection

```
FUNCTION InitializeWebSocket(taskId: String, authToken: String): WebSocketConnection

    BEGIN
        // Construct WebSocket URL
        wsUrl = "wss://api.example.com/ws/progress/" + taskId

        // Create connection
        ws = NEW WebSocket(wsUrl)
        ws.authToken = authToken

        // Set up event handlers
        ws.onOpen = HANDLE_ON_OPEN
        ws.onMessage = HANDLE_ON_MESSAGE
        ws.onError = HANDLE_ON_ERROR
        ws.onClose = HANDLE_ON_CLOSE

        // Set connection state
        connection = NEW WebSocketConnection()
        connection.ws = ws
        connection.taskId = taskId
        connection.state = "CONNECTING"
        connection.connectedAt = NULL
        connection.messageCount = 0

        RETURN connection
    END
```

### 1.2 Handle Connection Open

```
FUNCTION HANDLE_ON_OPEN(event: Event): Void

    BEGIN
        LOG("WebSocket connected")

        // Update connection state
        connection.state = "CONNECTED"
        connection.connectedAt = CURRENT_TIMESTAMP()
        connection.reconnectAttempts = 0
        connection.reconnectDelay = INITIAL_RECONNECT_DELAY

        // Send subscription message
        subscriptionMessage = {
            type: "subscribe",
            taskId: connection.taskId,
            token: connection.ws.authToken
        }

        connection.ws.send(JSON.stringify(subscriptionMessage))

        // Start heartbeat
        START_HEARTBEAT(connection)

        // Emit connection event
        EMIT("websocket:connected", { taskId: connection.taskId })
    END
```

### 1.3 Handle Connection Close

```
FUNCTION HANDLE_ON_CLOSE(event: CloseEvent): Void

    BEGIN
        LOG("WebSocket disconnected: " + event.code + " - " + event.reason)

        // Update connection state
        connection.state = "DISCONNECTED"

        // Stop heartbeat
        STOP_HEARTBEAT(connection)

        // Check if should reconnect
        IF event.code != 1000 THEN  // 1000 = normal close
            ATTEMPT_RECONNECT(connection)
        ELSE
            // Normal close, cleanup
            CLEANUP_CONNECTION(connection)
        END IF

        // Emit disconnect event
        EMIT("websocket:disconnected", {
            taskId: connection.taskId,
            code: event.code,
            reason: event.reason
        })
    END
```

### 1.4 Handle Connection Error

```
FUNCTION HANDLE_ON_ERROR(event: ErrorEvent): Void

    BEGIN
        LOG("WebSocket error: " + event.message)

        // Update connection state
        connection.state = "ERROR"

        // Emit error event
        EMIT("websocket:error", {
            taskId: connection.taskId,
            error: event.message
        })

        // Note: onclose will be called after.onerror
    END
```

---

## 2. Message Handling

### 2.1 Handle Incoming Message

```
FUNCTION HANDLE_ON_MESSAGE(event: MessageEvent): Void

    BEGIN
        // Increment message count
        connection.messageCount++

        // Parse message
        TRY
            message = JSON.parse(event.data)
        CATCH error
            LOG("Failed to parse message: " + error.message)
            RETURN
        END TRY

        // Validate message structure
        IF NOT message.type OR NOT message.payload THEN
            LOG("Invalid message structure")
            RETURN
        END IF

        // Route to appropriate handler
        SWITCH message.type
            CASE "progress_update"
                HANDLE_PROGRESS_UPDATE(message.payload)

            CASE "stage_change"
                HANDLE_STAGE_CHANGE(message.payload)

            CASE "time_estimate"
                HANDLE_TIME_ESTIMATE(message.payload)

            CASE "complete"
                HANDLE_COMPLETE(message.payload)

            CASE "error"
                HANDLE_ERROR(message.payload)

            CASE "pong"
                HANDLE_PONG(message.payload)

            DEFAULT
                LOG("Unknown message type: " + message.type)
        END SWITCH
    END
```

### 2.2 Handle Progress Update

```
FUNCTION HANDLE_PROGRESS_UPDATE(payload: ProgressUpdatePayload): Void

    BEGIN
        // Extract data
        taskId = payload.taskId
        percentage = payload.percentage
        stage = payload.stage
        timestamp = payload.timestamp

        // Get current state
        currentState = GET_STATE(taskId)

        // Calculate delta
        delta = percentage - currentState.percentage

        // Determine if significant update
        isSignificant = ABS(delta) >= 1

        // Create progress event
        progressEvent = {
            type: "PROGRESS_UPDATED",
            taskId: taskId,
            oldPercentage: currentState.percentage,
            newPercentage: percentage,
            stage: stage,
            delta: delta,
            isSignificant: isSignificant,
            timestamp: timestamp
        }

        // Update state
        newState = COPY(currentState)
        newState.percentage = percentage
        newState.currentStage = stage
        newState.lastUpdated = timestamp
        SAVE_STATE(taskId, newState)

        // Emit event
        EMIT("progress:updated", progressEvent)

        // If significant, also recalculate time estimate
        IF isSignificant THEN
            REQUEST_TIME_ESTIMATE(taskId)
        END IF
    END
```

### 2.3 Handle Stage Change

```
FUNCTION HANDLE_STAGE_CHANGE(payload: StageChangePayload): Void

    BEGIN
        // Extract data
        taskId = payload.taskId
        fromStage = payload.fromStage
        toStage = payload.toStage
        timestamp = payload.timestamp

        // Validate transition
        IF NOT IS_VALID_STAGE_TRANSITION(fromStage, toStage) THEN
            LOG("Invalid stage transition: " + fromStage + " -> " + toStage)
            RETURN
        END IF

        // Get current state
        currentState = GET_STATE(taskId)

        // Update state
        newState = COPY(currentState)
        newState.previousStage = fromStage
        newState.currentStage = toStage
        newState.stageChangedAt = timestamp

        // Complete previous stage
        prevStageObj = FIND_STAGE(newState.stages, fromStage)
        IF prevStageObj THEN
            prevStageObj.status = "COMPLETED"
            prevStageObj.completedAt = timestamp
            prevStageObj.duration = timestamp - prevStageObj.startedAt
        END IF

        // Start new stage
        newStageObj = FIND_STAGE(newState.stages, toStage)
        IF newStageObj THEN
            newStageObj.status = "IN_PROGRESS"
            newStageObj.startedAt = timestamp
        END IF

        SAVE_STATE(taskId, newState)

        // Create and emit event
        stageEvent = {
            type: "STAGE_CHANGED",
            taskId: taskId,
            fromStage: fromStage,
            toStage: toStage,
            timestamp: timestamp
        }

        EMIT("progress:stage_changed", stageEvent)
    END
```

### 2.4 Handle Time Estimate

```
FUNCTION HANDLE_TIME_ESTIMATE(payload: TimeEstimatePayload): Void

    BEGIN
        // Extract data
        taskId = payload.taskId
        estimatedTimeRemaining = payload.estimatedTimeRemaining
        confidence = payload.confidence

        // Get current state
        currentState = GET_STATE(taskId)

        // Update state
        newState = COPY(currentState)
        newState.timeEstimate = {
            seconds: estimatedTimeRemaining,
            confidence: confidence,
            calculatedAt: CURRENT_TIMESTAMP()
        }

        SAVE_STATE(taskId, newState)

        // Create and emit event
        estimateEvent = {
            type: "TIME_ESTIMATE_UPDATED",
            taskId: taskId,
            timeRemaining: estimatedTimeRemaining,
            confidence: confidence
        }

        EMIT("progress:time_estimate_updated", estimateEvent)
    END
```

### 2.5 Handle Complete

```
FUNCTION HANDLE_COMPLETE(payload: CompletePayload): Void

    BEGIN
        // Extract data
        taskId = payload.taskId
        resultUrl = payload.resultUrl
        duration = payload.duration

        // Get current state
        currentState = GET_STATE(taskId)

        // Update state to completed
        newState = COPY(currentState)
        newState.status = "COMPLETED"
        newState.percentage = 100
        newState.currentStage = "COMPLETED"
        newState.completedAt = CURRENT_TIMESTAMP()
        newState.duration = duration
        newState.resultUrl = resultUrl

        SAVE_STATE(taskId, newState)

        // Create and emit event
        completeEvent = {
            type: "PROGRESS_COMPLETED",
            taskId: taskId,
            resultUrl: resultUrl,
            duration: duration
        }

        EMIT("progress:completed", completeEvent)

        // Trigger notification
        TRIGGER_NOTIFICATION("SUCCESS", "Transcription Complete", {
            message: "Your transcript is ready",
            actions: [
                { label: "View", action: "navigate:" + resultUrl }
            ]
        })

        // Close WebSocket connection (no longer needed)
        connection.ws.close(1000, "Task completed")
    END
```

### 2.6 Handle Error

```
FUNCTION HANDLE_ERROR(payload: ErrorPayload): Void

    BEGIN
        // Extract data
        taskId = payload.taskId
        error = payload.error
        stage = payload.stage
        retryable = payload.retryable

        // Get current state
        currentState = GET_STATE(taskId)

        // Update state to failed
        newState = COPY(currentState)
        newState.status = "FAILED"
        newState.currentStage = "FAILED"
        newState.error = error
        newState.failedAt = CURRENT_TIMESTAMP()

        SAVE_STATE(taskId, newState)

        // Create and emit event
        errorEvent = {
            type: "PROGRESS_FAILED",
            taskId: taskId,
            error: error,
            stage: stage,
            retryable: retryable
        }

        EMIT("progress:failed", errorEvent)

        // Trigger error notification
        notificationMessage = error.message OR "An error occurred"
        notificationActions = []

        IF retryable THEN
            notificationActions.PUSH({
                label: "Retry",
                action: "retry:" + taskId
            })
        END IF

        notificationActions.PUSH({
            label: "Close",
            action: "dismiss"
        })

        TRIGGER_NOTIFICATION("ERROR", "Transcription Failed", {
            message: notificationMessage,
            actions: notificationActions
        })
    END
```

---

## 3. Reconnection Logic

### 3.1 Attempt Reconnect

```
FUNCTION ATTEMPT_RECONNECT(connection: WebSocketConnection): Void

    BEGIN
        // Check max reconnect attempts
        MAX_ATTEMPTS = 5
        IF connection.reconnectAttempts >= MAX_ATTEMPTS THEN
            LOG("Max reconnect attempts reached")
            EMIT("websocket:reconnect_failed", {
                taskId: connection.taskId,
                attempts: connection.reconnectAttempts
            })

            // Fall back to polling
            START_POLLING_FALLBACK(connection.taskId)
            RETURN
        END IF

        // Increment attempt counter
        connection.reconnectAttempts++

        // Calculate delay with exponential backoff
        delay = connection.reconnectDelay * POWER(2, connection.reconnectAttempts - 1)
        delay = MIN(delay, MAX_RECONNECT_DELAY)  // Cap at 30 seconds

        LOG("Reconnecting in " + delay + "ms (attempt " + connection.reconnectAttempts + ")")

        // Schedule reconnection
        SET_TIMEOUT(delay, FUNCTION()
            TRY
                // Create new connection
                newConnection = InitializeWebSocket(
                    connection.taskId,
                    connection.ws.authToken
                )

                // Update connection reference
                connection.ws = newConnection.ws
                connection.state = "RECONNECTING"

            CATCH error
                LOG("Reconnection failed: " + error.message)
                // This will trigger onclose, which calls ATTEMPT_RECONNECT again
            END TRY
        END)
    END
```

### 3.2 Start Polling Fallback

```
FUNCTION START_POLLING_FALLBACK(taskId: String): Void

    BEGIN
        LOG("Starting polling fallback for task: " + taskId)

        pollInterval = 5000  // Poll every 5 seconds

        pollingTimer = SET_INTERVAL(pollInterval, FUNCTION()
            FETCH_PROGRESS(taskId)
                .THEN(progress => {
                    // Update state with polling result
                    EMIT("polling:progress", progress)
                })
                .CATCH(error => {
                    LOG("Polling error: " + error.message)
                })
        END)

        // Store timer for cleanup
        pollingFallbacks[taskId] = pollingTimer

        EMIT("websocket:polling_started", { taskId: taskId })
    END
```

### 3.3 Stop Polling Fallback

```
FUNCTION STOP_POLLING_FALLBACK(taskId: String): Void

    BEGIN
        IF pollingFallbacks.EXISTS(taskId) THEN
            CLEAR_INTERVAL(pollingFallbacks[taskId])
            DELETE pollingFallbacks[taskId]
            LOG("Stopped polling fallback for task: " + taskId)
        END IF
    END
```

---

## 4. Heartbeat Management

### 4.1 Start Heartbeat

```
FUNCTION START_HEARTBEAT(connection: WebSocketConnection): Void

    BEGIN
        // Send ping every 30 seconds
        HEARTBEAT_INTERVAL = 30000

        connection.heartbeatTimer = SET_INTERVAL(HEARTBEAT_INTERVAL, FUNCTION()
            IF connection.state = "CONNECTED" THEN
                pingMessage = {
                    type: "ping",
                    timestamp: CURRENT_TIMESTAMP()
                }

                TRY
                    connection.ws.send(JSON.stringify(pingMessage))
                    connection.lastPing = CURRENT_TIMESTAMP()
                CATCH error
                    LOG("Failed to send ping: " + error.message)
                END TRY
            END IF
        END)
    END
```

### 4.2 Handle Pong Response

```
FUNCTION HANDLE_PONG(payload: PongPayload): Void

    BEGIN
        timestamp = payload.timestamp

        // Calculate round-trip time
        rtt = CURRENT_TIMESTAMP() - timestamp

        // Update connection stats
        connection.lastPong = CURRENT_TIMESTAMP()
        connection.roundTripTime = rtt

        // Log if RTT is high
        IF rtt > 1000 THEN
            LOG("High WebSocket RTT: " + rtt + "ms")
        END IF
    END
```

### 4.3 Stop Heartbeat

```
FUNCTION STOP_HEARTBEAT(connection: WebSocketConnection): Void

    BEGIN
        IF connection.heartbeatTimer THEN
            CLEAR_INTERVAL(connection.heartbeatTimer)
            connection.heartbeatTimer = NULL
        END IF
    END
```

---

## 5. Message Queue

### 5.1 Queue Message While Disconnected

```
FUNCTION QueueMessage(taskId: String, message: Object): Void

    BEGIN
        // Add to message queue
        IF NOT messageQueues.EXISTS(taskId) THEN
            messageQueues[taskId] = []
        END IF

        messageQueues[taskId].PUSH({
            message: message,
            timestamp: CURRENT_TIMESTAMP()
        })

        // Limit queue size
        IF LENGTH(messageQueues[taskId]) > 100 THEN
            messageQueues[taskId].SHIFT()  // Remove oldest
        END IF
    END
```

### 5.2 Send Queued Messages

```
FUNCTION SendQueuedMessages(connection: WebSocketConnection): Void

    BEGIN
        taskId = connection.taskId

        IF messageQueues.EXISTS(taskId) AND LENGTH(messageQueues[taskId]) > 0 THEN
            FOR EACH queued IN messageQueues[taskId]
                TRY
                    connection.ws.send(JSON.stringify(queued.message))
                CATCH error
                    LOG("Failed to send queued message: " + error.message)
                END TRY
            END FOR

            // Clear queue
            DELETE messageQueues[taskId]
        END IF
    END
```

---

## 6. Cleanup

### 6.1 Cleanup Connection

```
FUNCTION CLEANUP_CONNECTION(connection: WebSocketConnection): Void

    BEGIN
        // Stop heartbeat
        STOP_HEARTBEAT(connection)

        // Stop polling fallback if running
        STOP_POLLING_FALLBACK(connection.taskId)

        // Clear queued messages
        IF messageQueues.EXISTS(connection.taskId) THEN
            DELETE messageQueues[connection.taskId]
        END IF

        // Remove from active connections
        DELETE activeConnections[connection.taskId]

        LOG("Cleaned up connection for task: " + connection.taskId)
    END
```

### 6.2 Disconnect All

```
FUNCTION DisconnectAll(): Void

    BEGIN
        FOR EACH taskId IN activeConnections.KEYS()
            connection = activeConnections[taskId]

            TRY
                connection.ws.close(1000, "Shutdown")
            CATCH error
                LOG("Error closing connection: " + error.message)
            END TRY
        END FOR

        activeConnections.CLEAR()
        messageQueues.CLEAR()
        pollingFallbacks.CLEAR()
    END
```

---

## 7. Event Bus Integration

### 7.1 Subscribe to Progress Events

```
FUNCTION SubscribeToProgress(taskId: String, callback: Function): UnsubscribeFunction

    BEGIN
        eventName = "progress:" + taskId

        unsubscribe = EVENT_BUS.on(eventName, callback)

        RETURN unsubscribe
    END
```

### 7.2 Bridge WebSocket to Event Bus

```
FUNCTION BridgeWebSocketToEventBus(connection: WebSocketConnection): Void

    BEGIN
        // Subscribe to WebSocket events
        connection.ws.onMessage = (event) => {
            parsedMessage = JSON.parse(event.data)

            // Emit to event bus with taskId prefix
            eventName = "ws:" + connection.taskId + ":" + parsedMessage.type
            EVENT_BUS.emit(eventName, parsedMessage.payload)

            // Also emit to generic event
            EVENT_BUS.emit("ws:message", {
                taskId: connection.taskId,
                type: parsedMessage.type,
                payload: parsedMessage.payload
            })
        }
    END
```

---

*End of WebSocket Handling Pseudocode*
