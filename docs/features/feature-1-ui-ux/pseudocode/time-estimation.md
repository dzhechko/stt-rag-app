# Pseudocode: Time Estimation
## Feature 1: UI/UX Improvements

| Version | Date | Author | Status |
|---------|------|--------|--------|
| 1.0 | 2025-02-03 | System Architect | Draft |

---

## 1. Time Estimation Algorithm

### 1.1 Main Estimation Function

```
FUNCTION CalculateTimeEstimate(
    task: Task,
    progressState: ProgressState,
    historicalData: HistoricalData[]
): TimeEstimate

    INPUT:
        task: Task with file info (size, duration)
        progressState: Current progress state
        historicalData: Past similar tasks for learning

    OUTPUT:
        TimeEstimate with seconds, confidence, method

    BEGIN
        // 1. Select estimation method based on available data
        IF progressState.timeElapsed < 5 SECONDS THEN
            // Use file metadata for initial estimate
            estimate = ESTIMATE_FROM_METADATA(task)

        ELSE IF progressState.currentStage = Stage.UPLOADING THEN
            // Use upload speed for better estimate
            estimate = ESTIMATE_FROM_UPLOAD(task, progressState)

        ELSE IF progressState.percentage > 0 THEN
            // Use linear extrapolation
            estimate = ESTIMATE_FROM_LINEAR(task, progressState)

            // Apply historical correction if we have enough data
            IF LENGTH(historicalData) >= 5 THEN
                estimate = APPLY_HISTORICAL_CORRECTION(
                    task,
                    estimate,
                    historicalData
                )
            END IF

        ELSE
            // Fallback to metadata estimate
            estimate = ESTIMATE_FROM_METADATA(task)
        END IF

        // 2. Ensure minimum estimate
        IF estimate.seconds < 10 THEN
            estimate.seconds = 10
        END IF

        // 3. Add buffer time
        estimate.seconds = estimate.seconds + CALCULATE_BUFFER(estimate)

        RETURN estimate
    END
```

### 1.2 Estimate From Metadata

```
FUNCTION ESTIMATE_FROM_METADATA(task: Task): TimeEstimate

    BEGIN
        // Default processing rates (can be adjusted)
        UPLOAD_SPEED_MBPS = 5          // 5 MB/s
        TRANSCRIPTION_RATE = 0.3       // 0.3x real-time
        BUFFER_SECONDS = 30            // 30 second buffer

        // Calculate upload time
        fileSizeMB = task.fileSize / (1024 * 1024)
        uploadTimeSeconds = fileSizeMB / UPLOAD_SPEED_MBPS

        // Calculate transcription time
        // For 0.3x rate: 1 minute of audio = 3.33 minutes of processing
        transcriptionTimeSeconds = task.audioDuration / TRANSCRIPTION_RATE

        // Calculate total
        totalSeconds = uploadTimeSeconds + transcriptionTimeSeconds + BUFFER_SECONDS

        RETURN NEW TimeEstimate(
            seconds: ROUND(totalSeconds),
            confidence: 0.2,  // Low confidence for metadata-only
            method: "METADATA"
        )
    END
```

### 1.3 Estimate From Upload

```
FUNCTION ESTIMATE_FROM_UPLOAD(
    task: Task,
    progressState: ProgressState
): TimeEstimate

    BEGIN
        // Check if we have upload speed data
        IF NOT progressState.uploadSpeed THEN
            RETURN ESTIMATE_FROM_METADATA(task)
        END IF

        // Calculate remaining upload time
        bytesRemaining = task.fileSize - progressState.bytesUploaded
        uploadETaseconds = bytesRemaining / progressState.uploadSpeed

        // Estimate processing time from metadata
        // (we don't have processing progress yet)
        processingETaseconds = task.audioDuration / DEFAULT_TRANSCRIPTION_RATE

        // Add buffer
        totalSeconds = uploadETaseconds + processingETaseconds + BUFFER_SECONDS

        // Confidence is medium during upload
        confidence = CALCULATE_UPLOAD_CONFIDENCE(progressState)

        RETURN NEW TimeEstimate(
            seconds: ROUND(totalSeconds),
            confidence: confidence,
            method: "UPLOAD"
        )
    END

    FUNCTION CALCULATE_UPLOAD_CONFIDENCE(state: ProgressState): Number
        BEGIN
            // Confidence increases as upload progresses
            baseConfidence = 0.3
            progressBonus = state.stageProgress / 200  // Max 0.5
            RETURN MIN(baseConfidence + progressBonus, 0.6)
        END
```

### 1.4 Estimate From Linear Extrapolation

```
FUNCTION ESTIMATE_FROM_LINEAR(
    task: Task,
    progressState: ProgressState
): TimeEstimate

    BEGIN
        // Calculate current processing rate
        progressFraction = progressState.percentage / 100
        timeElapsed = progressState.timeElapsed

        // Rate = progress per second
        rate = progressFraction / timeElapsed

        // Apply stage multiplier (some stages are slower)
        stageMultiplier = GET_STAGE_MULTIPLIER(progressState.currentStage)

        // Calculate remaining time
        remainingFraction = 1 - progressFraction
        baseETaseconds = remainingFraction / rate

        // Adjust for stage
        adjustedETaseconds = baseETaseconds * stageMultiplier

        // Calculate confidence based on progress
        // More progress = higher confidence
        confidence = CALCULATE_LINEAR_CONFIDENCE(progressFraction)

        RETURN NEW TimeEstimate(
            seconds: ROUND(adjustedETaseconds),
            confidence: confidence,
            method: "LINEAR"
        )
    END

    FUNCTION GET_STAGE_MULTIPLIER(stage: Stage): Number
        BEGIN
            // Some stages take longer relative to progress shown
            multipliers = {
                UPLOADING: 1.0,
                VALIDATING: 0.5,
                QUEUED: 0.0,
                PROCESSING: 0.8,
                TRANSCRIBING: 1.5,    // Transcription is slower
                FINALIZING: 0.3,
                COMPLETED: 0.0,
                FAILED: 0.0
            }
            RETURN multipliers[stage] OR 1.0
        END

    FUNCTION CALCULATE_LINEAR_CONFIDENCE(progressFraction: Number): Number
        BEGIN
            // Confidence formula: 0.2 + (progress * 0.7)
            // Min: 0.2, Max: 0.9
            baseConfidence = 0.2
            progressBonus = progressFraction * 0.7
            RETURN MIN(baseConfidence + progressBonus, 0.95)
        END
```

### 1.5 Apply Historical Correction

```
FUNCTION APPLY_HISTORICAL_CORRECTION(
    task: Task,
    baseEstimate: TimeEstimate,
    historicalData: HistoricalData[]
): TimeEstimate

    BEGIN
        // Find similar tasks
        similarTasks = FILTER_SIMILAR_TASKS(task, historicalData)

        // Need at least 3 similar tasks for correction
        IF LENGTH(similarTasks) < 3 THEN
            RETURN baseEstimate
        END IF

        // Calculate average error rate for similar tasks
        errors = []
        FOR EACH similarTask IN similarTasks
            expectedTime = CALCULATE_EXPECTED_TIME(similarTask)
            actualTime = similarTask.actualDuration
            errorRate = (actualTime - expectedTime) / expectedTime
            errors.APPEND(errorRate)
        END FOR

        avgError = AVERAGE(errors)

        // Only apply correction if consistent bias detected (>10%)
        IF ABS(avgError) > 0.1 THEN
            correctedSeconds = baseEstimate.seconds * (1 + avgError)
            correctedConfidence = MIN(baseEstimate.confidence + 0.1, 0.95)

            RETURN NEW TimeEstimate(
                seconds: ROUND(correctedSeconds),
                confidence: correctedConfidence,
                method: "HISTORICAL"
            )
        END IF

        RETURN baseEstimate
    END

    FUNCTION FILTER_SIMILAR_TASKS(
        task: Task,
        historicalData: HistoricalData[]
    ): HistoricalData[]

        BEGIN
            similar = []
            FOR EACH historical IN historicalData
                // Check if similar (size within 50%, duration within 30%)
                sizeRatio = task.fileSize / historical.fileSize
                durationRatio = task.audioDuration / historical.audioDuration

                IF sizeRatio >= 0.5 AND sizeRatio <= 1.5 AND
                   durationRatio >= 0.7 AND durationRatio <= 1.3 THEN
                    similar.APPEND(historical)
                END IF
            END FOR

            RETURN similar
        END
```

---

## 2. Buffer Calculation

### 2.1 Calculate Dynamic Buffer

```
FUNCTION CALCULATE_BUFFER(estimate: TimeEstimate): Number

    BEGIN
        // Base buffer
        baseBuffer = 30  // 30 seconds

        // Add percentage-based buffer (5% of estimated time)
        percentageBuffer = estimate.seconds * 0.05

        // Larger buffer for low confidence estimates
        confidenceMultiplier = 1 + ((1 - estimate.confidence) * 0.5)

        // Calculate total buffer
        totalBuffer = (baseBuffer + percentageBuffer) * confidenceMultiplier

        // Cap buffer at 5 minutes max
        RETURN MIN(totalBuffer, 300)
    END
```

---

## 3. Time Formatting

### 3.1 Format Time Estimate

```
FUNCTION FormatTimeEstimate(estimate: TimeEstimate): String

    BEGIN
        seconds = estimate.seconds

        // Handle very short estimates
        IF seconds < 60 THEN
            RETURN "< 1 minute"
        END IF

        // Handle minutes
        IF seconds < 3600 THEN
            minutes = ROUND(seconds / 60)
            IF minutes = 1 THEN
                RETURN "About 1 minute"
            ELSE
                RETURN "About " + minutes + " minutes"
            END IF
        END IF

        // Handle hours
        IF seconds < 86400 THEN  // Less than a day
            hours = FLOOR(seconds / 3600)
            minutes = ROUND((seconds % 3600) / 60)

            IF minutes = 0 THEN
                IF hours = 1 THEN
                    RETURN "About 1 hour"
                ELSE
                    RETURN "About " + hours + " hours"
                END IF
            ELSE
                RETURN "About " + hours + "h " + minutes + "m"
            END IF
        END IF

        // Handle days
        days = FLOOR(seconds / 86400)
        hours = ROUND((seconds % 86400) / 3600)

        IF days = 1 THEN
            RETURN "About 1 day"
        ELSE
            RETURN "About " + days + " days"
        END IF
    END
```

### 3.2 Format Precise Time (HH:MM:SS)

```
FUNCTION FormatPreciseTime(seconds: Number): String

    BEGIN
        hours = FLOOR(seconds / 3600)
        minutes = FLOOR((seconds % 3600) / 60)
        secs = FLOOR(seconds % 60)

        // Pad with zeros
        hoursStr = PAD_LEFT(hours, 2, "0")
        minutesStr = PAD_LEFT(minutes, 2, "0")
        secsStr = PAD_LEFT(secs, 2, "0")

        RETURN hoursStr + ":" + minutesStr + ":" + secsStr
    END
```

### 3.3 Format Time Remaining (Dynamic)

```
FUNCTION FormatTimeRemaining(
    estimate: TimeEstimate,
    state: ProgressState
): String

    BEGIN
        // If low confidence, show "estimating"
        IF estimate.confidence < 0.3 THEN
            RETURN "Estimating..."
        END IF

        // If medium confidence, show "about"
        IF estimate.confidence < 0.7 THEN
            RETURN "About " + FormatTimeEstimate(estimate) + " remaining"
        END IF

        // High confidence - show exact-ish time
        IF estimate.seconds < 3600 THEN
            RETURN FormatTimeEstimate(estimate) + " remaining"
        ELSE
            // For longer estimates, show approximate
            hours = ROUND(estimate.seconds / 3600)
            RETURN "Approximately " + hours + " hours remaining"
        END IF
    END
```

---

## 4. Estimate Updates

### 4.1 Should Update Estimate

```
FUNCTION ShouldUpdateEstimate(
    oldEstimate: TimeEstimate,
    newEstimate: TimeEstimate
): Boolean

    BEGIN
        // Always update if method changed
        IF newEstimate.method != oldEstimate.method THEN
            RETURN True
        END IF

        // Update if time difference is significant (>10% or >30 seconds)
        timeDiff = ABS(newEstimate.seconds - oldEstimate.seconds)
        percentDiff = timeDiff / oldEstimate.seconds

        IF timeDiff > 30 OR percentDiff > 0.1 THEN
            RETURN True
        END IF

        // Update if confidence improved significantly (>10%)
        confidenceDiff = newEstimate.confidence - oldEstimate.confidence
        IF confidenceDiff > 0.1 THEN
            RETURN True
        END IF

        RETURN False
    END
```

### 4.2 Update Estimate with Smoothing

```
FUNCTION UpdateEstimateWithSmoothing(
    currentEstimate: TimeEstimate,
    newRawEstimate: TimeEstimate
): TimeEstimate

    BEGIN
        // Don't smooth if this is the first estimate
        IF NOT currentEstimate THEN
            RETURN newRawEstimate
        END IF

        // Don't smooth across method changes
        IF newRawEstimate.method != currentEstimate.method THEN
            RETURN newRawEstimate
        END IF

        // Apply exponential smoothing
        // Use higher smoothing factor when confident, lower when uncertain
        smoothingFactor = newRawEstimate.confidence

        smoothedSeconds = (smoothingFactor * newRawEstimate.seconds) +
                         ((1 - smoothingFactor) * currentEstimate.seconds)

        smoothedConfidence = MAX(newRawEstimate.confidence, currentEstimate.confidence)

        RETURN NEW TimeEstimate(
            seconds: ROUND(smoothedSeconds),
            confidence: smoothedConfidence,
            method: newRawEstimate.method
        )
    END
```

---

## 5. Historical Data Management

### 5.1 Record Actual Duration

```
FUNCTION RecordActualDuration(
    task: Task,
    actualDuration: Number
): Void

    BEGIN
        historicalEntry = {
            taskId: task.id,
            fileSize: task.fileSize,
            audioDuration: task.audioDuration,
            fileType: task.fileType,
            actualDuration: actualDuration,
            completedAt: CURRENT_TIMESTAMP()
        }

        // Add to historical data
        historicalData.APPEND(historicalEntry)

        // Keep only last 100 entries
        IF LENGTH(historicalData) > 100 THEN
            historicalData.SHIFT()  // Remove oldest
        END IF

        // Update default rates if we have enough data
        IF LENGTH(historicalData) >= 10 THEN
            UPDATE_DEFAULT_RATES(historicalData)
        END IF
    END
```

### 5.2 Update Default Rates

```
FUNCTION UPDATE_DEFAULT_RATES(historicalData: HistoricalData[]): Void

    BEGIN
        // Use last 20 entries for rate calculation
        recent = LAST_N(historicalData, 20)

        // Calculate average transcription rate
        totalRate = 0
        FOR EACH entry IN recent
            rate = entry.audioDuration / entry.actualDuration
            totalRate += rate
        END FOR

        averageRate = totalRate / LENGTH(recent)

        // Update global default
        DEFAULT_TRANSCRIPTION_RATE = averageRate
    END
```

---

## 6. Edge Cases

### 6.1 Handle Zero Progress

```
FUNCTION HandleZeroProgress(task: Task): TimeEstimate

    BEGIN
        // Task just started, use metadata estimate
        estimate = ESTIMATE_FROM_METADATA(task)

        // Add extra buffer for uncertainty
        estimate.seconds = estimate.seconds * 1.5

        RETURN estimate
    END
```

### 6.2 Handle Stalled Progress

```
FUNCTION HandleStalledProgress(
    task: Task,
    state: ProgressState
): TimeEstimate

    BEGIN
        // Detect if stalled (no progress for 2 minutes)
        IF IsProgressStalled(state) THEN
            // Return uncertain estimate
            RETURN NEW TimeEstimate(
                seconds: state.timeEstimate.seconds,  // Keep current
                confidence: 0.1,  // Very low confidence
                method: "STALLED"
            )
        END IF

        // Normal estimation
        RETURN CalculateTimeEstimate(task, state, historicalData)
    END
```

### 6.3 Handle Very Large Files

```
FUNCTION HandleVeryLargeFile(task: Task): TimeEstimate

    BEGIN
        // Define "very large" as > 500MB
        IF task.fileSize > 500 * 1024 * 1024 THEN
            estimate = ESTIMATE_FROM_METADATA(task)

            // Add extra 20% buffer for large files
            estimate.seconds = estimate.seconds * 1.2

            RETURN estimate
        END IF

        // Normal estimation
        RETURN CalculateTimeEstimate(task, state, historicalData)
    END
```

---

*End of Time Estimation Pseudocode*
