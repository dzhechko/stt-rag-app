# Pseudocode: Progress Calculation
## Feature 1: UI/UX Improvements

| Version | Date | Author | Status |
|---------|------|--------|--------|
| 1.0 | 2025-02-03 | System Architect | Draft |

---

## 1. Progress Calculation Algorithm

### 1.1 Main Progress Calculation

```
FUNCTION CalculateProgress(task: Task, progressData: ProgressData): ProgressState

    INPUT:
        task: Task containing taskId, file info, stages
        progressData: Current progress data from backend

    OUTPUT:
        ProgressState with percentage, stage, time estimate

    BEGIN
        // 1. Initialize state
        state = NEW ProgressState()
        state.taskId = task.id
        state.lastUpdated = CURRENT_TIMESTAMP()

        // 2. Determine current stage
        state.currentStage = DETERMINE_STAGE(progressData.stageName)

        // 3. Calculate overall percentage
        state.percentage = CALCULATE_OVERALL_PERCENTAGE(
            task.stages,
            state.currentStage,
            progressData.stageProgress
        )

        // 4. Calculate stage progress
        state.stageProgress = progressData.stageProgress

        // 5. Calculate time estimate
        state.timeEstimate = CALCULATE_TIME_ESTIMATE(task, state)

        // 6. Calculate speed metrics
        IF progressData.bytesProcessed AND progressData.totalBytes THEN
            state.processingSpeed = CALCULATE_SPEED(
                progressData.bytesProcessed,
                task.timeElapsed
            )
        END IF

        // 7. Determine status
        IF state.percentage = 100 THEN
            state.status = "COMPLETED"
        ELSE IF progressData.error THEN
            state.status = "FAILED"
        ELSE
            state.status = "IN_PROGRESS"
        END IF

        RETURN state
    END
```

### 1.2 Determine Stage

```
FUNCTION DETERMINE_STAGE(stageName: String): Stage

    BEGIN
        SWITCH stageName
            CASE "uploading"
                RETURN Stage.UPLOADING
            CASE "validating"
                RETURN Stage.VALIDATING
            CASE "queued"
                RETURN Stage.QUEUED
            CASE "processing"
                RETURN Stage.PROCESSING
            CASE "transcribing"
                RETURN Stage.TRANSCRIBING
            CASE "finalizing"
                RETURN Stage.FINALIZING
            CASE "completed"
                RETURN Stage.COMPLETED
            CASE "failed"
                RETURN Stage.FAILED
            DEFAULT
                RETURN Stage.UNKNOWN
        END SWITCH
    END
```

### 1.3 Calculate Overall Percentage

```
FUNCTION CALCULATE_OVERALL_PERCENTAGE(
    stages: Stage[],
    currentStage: Stage,
    stageProgress: Number
): Number

    BEGIN
        // Define stage weights (what % of total time each stage takes)
        // These can be adjusted based on historical data
        stageWeights = {
            UPLOADING: 0.15,      // 15% - uploading file
            VALIDATING: 0.05,     // 5%  - validation
            QUEUED: 0.00,         // 0%  - waiting in queue
            PROCESSING: 0.25,     // 25% - audio preprocessing
            TRANSCRIBING: 0.50,   // 50% - actual transcription
            FINALIZING: 0.05      // 5%  - post-processing
        }

        // Calculate completed percentage from finished stages
        completedPercent = 0
        FOR EACH stage IN stages
            IF stage.index < currentStage.index THEN
                completedPercent += stageWeights[stage.name] * 100
            END IF
        END FOR

        // Add current stage progress
        currentStageWeight = stageWeights[currentStage.name] * 100
        currentStagePercent = currentStageWeight * (stageProgress / 100)

        totalPercent = completedPercent + currentStagePercent

        // Clamp to 0-100
        RETURN CLAMP(totalPercent, 0, 100)
    END
```

### 1.4 Calculate Speed

```
FUNCTION CALCULATE_SPEED(bytesProcessed: Number, timeElapsed: Number): ProcessingSpeed

    BEGIN
        // Calculate bytes per second
        bytesPerSecond = bytesProcessed / timeElapsed

        // Convert to human-readable format
        IF bytesPerSecond >= 1024 * 1024 THEN
            value = bytesPerSecond / (1024 * 1024)
            unit = "MB/s"
        ELSE IF bytesPerSecond >= 1024 THEN
            value = bytesPerSecond / 1024
            unit = "KB/s"
        ELSE
            value = bytesPerSecond
            unit = "B/s"
        END IF

        RETURN NEW ProcessingSpeed(
            value: value,
            unit: unit,
            rawBytesPerSecond: bytesPerSecond
        )
    END
```

### 1.5 Handle Progress Update

```
FUNCTION HandleProgressUpdate(message: WebSocketMessage): ProgressEvent

    BEGIN
        // Parse message
        taskId = message.payload.taskId
        percentage = message.payload.percentage
        stage = message.payload.stage
        timestamp = message.payload.timestamp

        // Get previous state
        previousState = GET_STATE(taskId)

        // Create new state
        newState = COPY(previousState)
        newState.percentage = percentage
        newState.currentStage = stage
        newState.lastUpdated = timestamp

        // Calculate delta
        delta = percentage - previousState.percentage

        // Determine if significant update (more than 1% change)
        isSignificant = ABS(delta) >= 1

        // Calculate time estimate if significant
        IF isSignificant THEN
            newState.timeEstimate = CALCULATE_TIME_ESTIMATE(task, newState)
        END IF

        // Save state
        SAVE_STATE(taskId, newState)

        // Create event
        event = NEW ProgressEvent(
            taskId: taskId,
            oldPercentage: previousState.percentage,
            newPercentage: percentage,
            stage: stage,
            delta: delta,
            isSignificant: isSignificant,
            timeEstimate: newState.timeEstimate
        )

        RETURN event
    END
```

### 1.6 Handle Stage Change

```
FUNCTION HandleStageChange(message: WebSocketMessage): StageChangeEvent

    BEGIN
        // Parse message
        taskId = message.payload.taskId
        fromStage = DETERMINE_STAGE(message.payload.fromStage)
        toStage = DETERMINE_STAGE(message.payload.toStage)
        timestamp = message.payload.timestamp

        // Validate transition
        IF NOT IS_VALID_TRANSITION(fromStage, toStage) THEN
            THROW ERROR("Invalid stage transition")
        END IF

        // Get previous state
        previousState = GET_STATE(taskId)

        // Update state
        newState = COPY(previousState)
        newState.currentStage = toStage
        newState.previousStage = fromStage
        newState.stageChangedAt = timestamp

        // Calculate stage duration
        IF fromStage.startedAt THEN
            stageDuration = timestamp - fromStage.startedAt
            fromStage.duration = stageDuration
        END IF

        // Start new stage
        toStage.startedAt = timestamp

        // Save state
        SAVE_STATE(taskId, newState)

        // Create event
        event = NEW StageChangeEvent(
            taskId: taskId,
            fromStage: fromStage,
            toStage: toStage,
            timestamp: timestamp
        )

        RETURN event
    END
```

---

## 2. Stage Progress Calculation

### 2.1 Upload Stage Progress

```
FUNCTION CALCULATE_UPLOAD_PROGRESS(uploadData: UploadData): Number

    BEGIN
        IF uploadData.totalBytes = 0 THEN
            RETURN 0
        END IF

        // Calculate percentage based on bytes uploaded
        percentage = (uploadData.bytesUploaded / uploadData.totalBytes) * 100

        // Adjust for chunked upload overhead (add 5% buffer)
        adjustedPercentage = percentage * 0.95

        RETURN ROUND(adjustedPercentage, 1)
    END
```

### 2.2 Transcription Stage Progress

```
FUNCTION CALCULATE_TRANSCRIPTION_PROGRESS(transcriptionData: TranscriptionData): Number

    BEGIN
        // For transcription, progress comes from backend
        // But we can add smoothing to prevent jitter

        rawPercentage = transcriptionData.percentage

        // Get previous percentage
        previousPercentage = GET_PREVIOUS_PERCENTAGE(transcriptionData.taskId)

        // Apply smoothing to prevent jumps
        // Use exponential moving average with alpha = 0.3
        IF previousPercentage EXISTS THEN
            smoothedPercentage = (0.3 * rawPercentage) + (0.7 * previousPercentage)
        ELSE
            smoothedPercentage = rawPercentage
        END IF

        RETURN ROUND(smoothedPercentage, 1)
    END
```

### 2.3 Overall Progress with Stages

```
FUNCTION CALCULATE_WEIGHTED_PROGRESS(stageProgresses: Map<Stage, Number>): Number

    BEGIN
        // Define stage weights
        weights = {
            UPLOADING: 0.15,
            VALIDATING: 0.05,
            QUEUED: 0.00,
            PROCESSING: 0.25,
            TRANSCRIBING: 0.50,
            FINALIZING: 0.05
        }

        totalProgress = 0

        // Calculate progress for each completed stage
        FOR EACH stage IN ORDER_OF_STAGES
            progress = stageProgresses[stage]

            IF progress = 100 THEN
                // Stage complete - add full weight
                totalProgress += weights[stage] * 100
            ELSE IF progress > 0 THEN
                // Stage in progress - add weighted progress
                totalProgress += weights[stage] * progress
            END IF
        END FOR

        RETURN ROUND(totalProgress, 1)
    END
```

---

## 3. Progress State Management

### 3.1 Initialize Progress State

```
FUNCTION InitializeProgressState(task: Task): ProgressState

    BEGIN
        state = NEW ProgressState()
        state.taskId = task.id
        state.fileName = task.fileName
        state.fileSize = task.fileSize
        state.currentStage = Stage.UPLOADING
        state.percentage = 0
        state.status = "PENDING"
        state.createdAt = CURRENT_TIMESTAMP()
        state.lastUpdated = CURRENT_TIMESTAMP()

        // Initialize stages
        state.stages = []
        FOR EACH stageName IN STAGE_ORDER
            stage = NEW Stage()
            stage.name = stageName
            stage.status = "PENDING"
            state.stages.APPEND(stage)
        END FOR

        // Start first stage
        state.stages[0].status = "IN_PROGRESS"
        state.stages[0].startedAt = CURRENT_TIMESTAMP()

        RETURN state
    END
```

### 3.2 Update Progress State

```
FUNCTION UpdateProgressState(
    state: ProgressState,
    update: ProgressUpdate
): ProgressState

    BEGIN
        // Create copy for immutability
        newState = COPY(state)

        // Update percentage
        newState.percentage = update.percentage
        newState.lastUpdated = CURRENT_TIMESTAMP()

        // Update current stage progress
        currentStage = FIND_STAGE(newState.stages, update.stage)
        IF currentStage THEN
            currentStage.progress = update.stageProgress
            currentStage.lastUpdated = CURRENT_TIMESTAMP()

            // Mark complete if 100%
            IF update.stageProgress = 100 THEN
                currentStage.status = "COMPLETED"
                currentStage.completedAt = CURRENT_TIMESTAMP()
            END IF
        END IF

        // Update metrics
        IF update.speed THEN
            newState.speed = update.speed
        END IF

        RETURN newState
    END
```

### 3.3 Complete Progress State

```
FUNCTION CompleteProgressState(
    state: ProgressState,
    resultUrl: String
): ProgressState

    BEGIN
        newState = COPY(state)

        // Update all final values
        newState.status = "COMPLETED"
        newState.percentage = 100
        newState.currentStage = Stage.COMPLETED
        newState.completedAt = CURRENT_TIMESTAMP()
        newState.resultUrl = resultUrl

        // Complete all stages
        FOR EACH stage IN newState.stages
            IF stage.status != "COMPLETED" THEN
                stage.status = "COMPLETED"
                stage.completedAt = CURRENT_TIMESTAMP()
            END IF
        END FOR

        // Calculate total duration
        newState.duration = newState.completedAt - newState.createdAt

        RETURN newState
    END
```

---

## 4. Progress Smoothing

### 4.1 Smooth Percentage Updates

```
FUNCTION SmoothPercentage(
    currentPercentage: Number,
    newPercentage: Number,
    smoothingFactor: Number = 0.3
): Number

    BEGIN
        // Exponential Moving Average
        // newSmoothed = (alpha * newValue) + ((1 - alpha) * oldSmoothed)

        smoothed = (smoothingFactor * newPercentage) +
                   ((1 - smoothingFactor) * currentPercentage)

        RETURN ROUND(smoothed, 1)
    END
```

### 4.2 Detect Progress Stalls

```
FUNCTION DetectProgressStall(state: ProgressState): Boolean

    BEGIN
        // Check if progress hasn't moved in 2 minutes
        STALL_THRESHOLD_MS = 120000  // 2 minutes

        timeSinceLastUpdate = CURRENT_TIMESTAMP() - state.lastUpdated

        IF timeSinceLastUpdate > STALL_THRESHOLD_MS THEN
            RETURN True
        END IF

        // Check if stage is QUEUED for too long (> 5 minutes)
        IF state.currentStage = Stage.QUEUED THEN
            timeInQueue = CURRENT_TIMESTAMP() - state.stageChangedAt
            IF timeInQueue > 300000 THEN  // 5 minutes
                RETURN True
            END IF
        END IF

        RETURN False
    END
```

---

## 5. Progress Event Handling

### 5.1 Process Progress Event

```
FUNCTION ProcessProgressEvent(event: ProgressEvent): UIUpdate

    BEGIN
        uiUpdate = NEW UIUpdate()

        // Update progress bar
        uiUpdate.progress = event.newPercentage

        // Update stage indicator
        uiUpdate.currentStage = event.stage

        // Update time estimate
        uiUpdate.timeEstimate = event.timeEstimate

        // Update stage progress bar
        uiUpdate.stageProgress = GET_STAGE_PROGRESS(event.taskId, event.stage)

        // Check for milestones
        IF event.newPercentage >= 25 AND event.oldPercentage < 25 THEN
            uiUpdate.milestone = "25% complete"
        ELSE IF event.newPercentage >= 50 AND event.oldPercentage < 50 THEN
            uiUpdate.milestone = "50% complete"
        ELSE IF event.newPercentage >= 75 AND event.oldPercentage < 75 THEN
            uiUpdate.milestone = "75% complete"
        ELSE IF event.newPercentage >= 100 AND event.oldPercentage < 100 THEN
            uiUpdate.milestone = "Complete!"
        END IF

        RETURN uiUpdate
    END
```

### 5.2 Debounce Progress Updates

```
// Prevent UI thrashing from too many updates
debounceTimer = NULL

FUNCTION DEBOUNCED_UpdateProgress(event: ProgressEvent): Void

    BEGIN
        // Clear existing timer
        IF debounceTimer EXISTS THEN
            CLEAR_TIMEOUT(debounceTimer)
        END IF

        // Set new timer (update at most every 100ms)
        debounceTimer = SET_TIMEOUT(100, FUNCTION()
            ProcessProgressEvent(event)
        END)

        // Always update immediately for completion
        IF event.newPercentage = 100 THEN
            CLEAR_TIMEOUT(debounceTimer)
            ProcessProgressEvent(event)
        END IF
    END
```

---

*End of Progress Calculation Pseudocode*
