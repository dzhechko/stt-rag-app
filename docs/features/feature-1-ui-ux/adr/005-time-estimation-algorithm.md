# ADR-005: Time Estimation Algorithm

| Status | Proposed by | Decision date | Effective date |
|--------|-------------|---------------|---------------|
| Accepted | System Architect | 2025-02-03 | 2025-02-03 |

---

## Context

Users transcribing large files (hundreds of MB, hours of audio) need accurate time estimates to:
1. Plan their time effectively
2. Know when to check back
3. Decide whether to wait or work on something else

Poor estimates cause:
- User frustration (estimates way off)
- Loss of trust (repeated inaccuracies)
- Bad user experience (no feedback)

## Decision

Implement a **multi-stage time estimation algorithm** that combines:
1. **File metadata analysis** (initial estimate)
2. **Linear extrapolation** (during processing)
3. **Historical data** (if available)
4. **Stage-based adjustments** (different stages have different speeds)

### Algorithm

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    Time Estimation Algorithm                           │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  File Selected                                                         │
│       │                                                                │
│       ▼                                                                │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  Stage 1: Initial Estimate (based on metadata)                  │   │
│  │  • File size (MB)                                               │   │
│  │  • Duration (seconds)                                           │   │
│  │  • Known processing rates (from historical data)                │   │
│  │                                                                  │   │
│  │  Estimate = (FileSize / AverageUploadSpeed) +                   │   │
│  │             (AudioDuration / AverageTranscriptionRate) +        │   │
│  │             BufferTime                                           │   │
│  │                                                                  │   │
│  │  Confidence: LOW (0.2)                                          │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│       │                                                                │
│       ▼                                                                │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  Stage 2: Upload Estimate (during upload)                       │   │
│  │  • Current upload speed                                          │   │
│  │  • Bytes uploaded / total bytes                                 │   │
│  │  • Time elapsed                                                 │   │
│  │                                                                  │   │
│  │  UploadETA = (BytesRemaining / CurrentUploadSpeed)               │   │
│  │  ProcessingETA = AudioDuration / AverageProcessingRate           │   │
│  │  TotalETA = UploadETA + ProcessingETA + Buffer                   │   │
│  │                                                                  │   │
│  │  Confidence: MEDIUM (0.4)                                       │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│       │                                                                │
│       ▼                                                                │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  Stage 3: Processing Estimate (during transcription)             │   │
│  │  • Progress percentage                                           │   │
│  │  • Time elapsed since processing started                        │   │
│  │  • Current processing rate                                      │   │
│  │  • Stage multipliers (transcribing is slower than processing)    │   │
│  │                                                                  │   │
│  │  Rate = ProgressPercentage / TimeElapsed                        │   │
│  │  RemainingProgress = 1 - ProgressPercentage                     │   │
│  │  ProcessingETA = RemainingProgress / Rate                        │   │
│  │  StageAdjustedETA = ProcessingETA * StageMultiplier             │   │
│  │                                                                  │   │
│  │  Confidence: HIGH (0.7+)                                        │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│       │                                                                │
│       ▼                                                                │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  Stage 4: Refinement (historical data)                          │   │
│  │  • Compare estimate vs actual for similar files                 │   │
│  │  • Apply correction factor if consistent bias detected          │   │
│  │                                                                  │   │
│  │  If HistoricalError > 10%:                                      │   │
│  │    AdjustedETA = ETA * (1 + HistoricalError)                    │   │
│  │                                                                  │   │
│  │  Confidence: VERY_HIGH (0.9+)                                  │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### Implementation Details

```typescript
// src/lib/time-estimation/estimation-algorithm.ts

export interface TimeEstimate {
  seconds: number;
  confidence: number;  // 0-1
  method: EstimationMethod;
}

export enum EstimationMethod {
  METADATA = "metadata",
  UPLOAD = "upload",
  LINEAR = "linear",
  HISTORICAL = "historical",
}

export interface ProgressData {
  taskId: string;
  fileSize: number;           // bytes
  audioDuration: number;      // seconds
  currentStage: Stage;
  progressPercentage: number; // 0-100
  timeElapsed: number;        // seconds since task start
  uploadSpeed?: number;       // bytes/second
  bytesUploaded?: number;
}

export interface HistoricalData {
  fileSize: number;
  audioDuration: number;
  actualDuration: number;
  fileType: string;
}

export class TimeEstimationAlgorithm {
  private historicalData: HistoricalData[] = [];
  private stageMultipliers: Record<Stage, number> = {
    [Stage.UPLOADING]: 1.0,
    [Stage.VALIDATING]: 0.1,
    [Stage.QUEUED]: 0.0,
    [Stage.PROCESSING]: 0.3,
    [Stage.TRANSCRIBING]: 1.5,
    [Stage.FINALIZING]: 0.2,
    [Stage.COMPLETED]: 0.0,
    [Stage.FAILED]: 0.0,
  };

  // Default processing rates (can be updated with real data)
  private defaultRates = {
    uploadSpeed: 5 * 1024 * 1024,     // 5 MB/s
    transcriptionSpeed: 0.3,           // 0.3x real-time (1 min audio = 3.3 min)
    processingSpeed: 10.0,            // 10x real-time
    bufferTime: 30,                    // 30 seconds buffer
  };

  calculate(data: ProgressData): TimeEstimate {
    // Determine which method to use based on available data
    if (data.timeElapsed < 5) {
      return this.fromMetadata(data);
    }

    if (data.currentStage === Stage.UPLOADING && data.uploadSpeed) {
      return this.fromUpload(data);
    }

    if (data.progressPercentage > 0) {
      const linearEstimate = this.fromLinearExtrapolation(data);

      // Apply historical correction if available
      if (this.historicalData.length >= 5) {
        return this.withHistoricalCorrection(data, linearEstimate);
      }

      return linearEstimate;
    }

    return this.fromMetadata(data);
  }

  // Stage 1: Initial estimate from file metadata
  private fromMetadata(data: ProgressData): TimeEstimate {
    const uploadTime = data.fileSize / this.defaultRates.uploadSpeed;
    const processingTime = data.audioDuration / this.defaultRates.transcriptionSpeed;
    const totalTime = uploadTime + processingTime + this.defaultRates.bufferTime;

    return {
      seconds: Math.ceil(totalTime),
      confidence: 0.2,
      method: EstimationMethod.METADATA,
    };
  }

  // Stage 2: Estimate during upload
  private fromUpload(data: ProgressData): TimeEstimate {
    if (!data.uploadSpeed || !data.bytesUploaded) {
      return this.fromMetadata(data);
    }

    const bytesRemaining = data.fileSize - data.bytesUploaded;
    const uploadETA = bytesRemaining / data.uploadSpeed;
    const processingETA = data.audioDuration / this.defaultRates.transcriptionSpeed;
    const totalETA = uploadETA + processingETA + this.defaultRates.bufferTime;

    return {
      seconds: Math.ceil(totalETA),
      confidence: 0.4,
      method: EstimationMethod.UPLOAD,
    };
  }

  // Stage 3: Linear extrapolation from current progress
  private fromLinearExtrapolation(data: ProgressData): TimeEstimate {
    const progressFraction = data.progressPercentage / 100;
    const timeElapsed = data.timeElapsed;

    // Calculate rate
    const rate = progressFraction / timeElapsed;

    // Apply stage multiplier (transcribing is slower than processing)
    const stageMultiplier = this.stageMultipliers[data.currentStage] || 1.0;

    // Calculate remaining time
    const remainingFraction = 1 - progressFraction;
    const baseETA = remainingFraction / rate;
    const adjustedETA = baseETA * stageMultiplier;

    // Increase confidence as we get further along
    const confidence = Math.min(0.2 + (progressFraction * 0.8), 0.95);

    return {
      seconds: Math.ceil(adjustedETA),
      confidence: Math.round(confidence * 100) / 100,
      method: EstimationMethod.LINEAR,
    };
  }

  // Stage 4: Apply historical correction
  private withHistoricalCorrection(
    data: ProgressData,
    baseEstimate: TimeEstimate
  ): TimeEstimate {
    // Find similar historical tasks
    const similarTasks = this.historicalData.filter(task =>
      this.isSimilarTask(data, task)
    );

    if (similarTasks.length < 3) {
      return baseEstimate;
    }

    // Calculate average error rate
    const errors = similarTasks.map(task => {
      const expected = task.audioDuration / this.defaultRates.transcriptionSpeed;
      const error = (task.actualDuration - expected) / expected;
      return error;
    });

    const avgError = errors.reduce((sum, e) => sum + e, 0) / errors.length;

    // Only adjust if consistent bias detected (error > 10%)
    if (Math.abs(avgError) > 0.1) {
      const correctedETA = baseEstimate.seconds * (1 + avgError);

      return {
        seconds: Math.ceil(correctedETA),
        confidence: Math.min(baseEstimate.confidence + 0.1, 0.95),
        method: EstimationMethod.HISTORICAL,
      };
    }

    return baseEstimate;
  }

  private isSimilarTask(
    current: ProgressData,
    historical: HistoricalData
  ): boolean {
    // Consider tasks similar if:
    // - File size within 50%
    // - Audio duration within 30%
    const sizeRatio = current.fileSize / historical.fileSize;
    const durationRatio = current.audioDuration / historical.audioDuration;

    return (
      sizeRatio >= 0.5 && sizeRatio <= 1.5 &&
      durationRatio >= 0.7 && durationRatio <= 1.3
    );
  }

  // Update historical data with actual results
  recordActualResult(data: {
    fileSize: number;
    audioDuration: number;
    actualDuration: number;
    fileType: string;
  }): void {
    this.historicalData.push(data);

    // Keep only last 100 records
    if (this.historicalData.length > 100) {
      this.historicalData.shift();
    }

    // Recalculate default rates based on recent data
    this.updateDefaultRates();
  }

  private updateDefaultRates(): void {
    // Update transcription speed based on recent data
    const recent = this.historicalData.slice(-20);

    if (recent.length >= 5) {
      const avgRate = recent.reduce((sum, task) => {
        return sum + (task.audioDuration / task.actualDuration);
      }, 0) / recent.length;

      this.defaultRates.transcriptionSpeed = avgRate;
    }
  }

  // Update default rates manually (from admin/config)
  setDefaultRates(rates: {
    uploadSpeed?: number;
    transcriptionSpeed?: number;
    bufferTime?: number;
  }): void {
    if (rates.uploadSpeed) this.defaultRates.uploadSpeed = rates.uploadSpeed;
    if (rates.transcriptionSpeed) this.defaultRates.transcriptionSpeed = rates.transcriptionSpeed;
    if (rates.bufferTime) this.defaultRates.bufferTime = rates.bufferTime;
  }
}

// Singleton instance
export const estimationAlgorithm = new TimeEstimationAlgorithm();
```

### React Hook

```typescript
// src/hooks/use-time-estimate.ts
import { useState, useEffect } from 'react';
import { estimationAlgorithm, ProgressData, TimeEstimate } from '@/lib/time-estimation/estimation-algorithm';

export function useTimeEstimate(progressData: ProgressData) {
  const [estimate, setEstimate] = useState<TimeEstimate>({
    seconds: 0,
    confidence: 0,
    method: 'metadata',
  });

  useEffect(() => {
    const newEstimate = estimationAlgorithm.calculate(progressData);

    // Only update if meaningful change (>5 seconds or >10% confidence change)
    const timeDiff = Math.abs(newEstimate.seconds - estimate.seconds);
    const confidenceDiff = Math.abs(newEstimate.confidence - estimate.confidence);

    if (timeDiff > 5 || confidenceDiff > 0.1) {
      setEstimate(newEstimate);
    }
  }, [
    progressData.progressPercentage,
    progressData.currentStage,
    progressData.timeElapsed,
    progressData.uploadSpeed,
    progressData.bytesUploaded,
  ]);

  return estimate;
}

// Hook to display time estimate
export function useTimeEstimateDisplay(estimate: TimeEstimate) {
  return {
    text: formatTimeEstimate(estimate),
    isReliable: estimate.confidence >= 0.7,
    confidence: estimate.confidence,
  };
}

function formatTimeEstimate(estimate: TimeEstimate): string {
  const seconds = estimate.seconds;

  if (seconds < 60) {
    return "< 1 minute";
  } else if (seconds < 3600) {
    const minutes = Math.round(seconds / 60);
    return `About ${minutes} ${minutes === 1 ? 'minute' : 'minutes'}`;
  } else {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.round((seconds % 3600) / 60);

    if (minutes === 0) {
      return `About ${hours} ${hours === 1 ? 'hour' : 'hours'}`;
    }

    return `About ${hours}h ${minutes}m`;
  }
}
```

## Alternatives Considered

### Alternative 1: Fixed Multiplier

**Description**: Use a simple multiplier based on audio duration (e.g., 3x real-time).

**Pros**:
- Very simple
- No state needed
- Always returns a value

**Cons**:
- Inaccurate for variable file sizes
- Doesn't account for upload time
- No improvement over time
- Not transparent about uncertainty

**Rejected because**: Too inaccurate for large files.

### Alternative 2: Machine Learning Model

**Description**: Train a model on historical data to predict completion time.

**Pros**:
- Most accurate if enough data
- Improves automatically with data
- Can handle complex patterns

**Cons**:
- Requires lots of training data
- Complex to implement
- Hard to debug
- Overkill for current needs
- "Black box" predictions

**Rejected because**: Don't have enough data yet, adds complexity.

### Alternative 3: User-Provided Estimates

**Description**: Let users input how long they think it will take.

**Pros**:
- User controls expectations
- No algorithm needed

**Cons**:
- Users don't know processing speeds
- Still needs backend validation
- Poor user experience

**Rejected because**: Users can't accurately estimate server processing time.

## Consequences

### Positive

1. **Improves over time**: More accurate as task progresses
2. **Transparent**: Shows confidence level
3. **Adaptable**: Can adjust default rates
4. **Multi-stage**: Different methods for different phases
5. **Historical learning**: Improves with more data

### Negative

1. **Complexity**: More complex than simple multiplier
2. **Cold start**: Less accurate until historical data accumulates
3. **Maintenance**: Need to update rates as system changes
4. **Edge cases**: May be wrong for unusual files
5. **UI complexity**: Need to show confidence levels

### Mitigations

1. Start with conservative estimates
2. Show "estimating..." when confidence is low
3. Allow admin override of default rates
4. Collect actual vs estimated data for improvement
5. Clear UI that shows uncertainty

## Implementation Roadmap

1. **Phase 1**: Basic algorithm
   - Implement metadata estimate
   - Implement linear extrapolation
   - Add stage multipliers

2. **Phase 2**: Upload tracking
   - Add upload speed calculation
   - Implement upload-based estimate

3. **Phase 3**: Historical data
   - Store actual task durations
   - Implement historical correction
   - Auto-update default rates

4. **Phase 4**: UI integration
   - Display time estimates
   - Show confidence levels
   - Handle edge cases

## References

- [Progress Bar UX Best Practices](https://www.nngroup.com/articles/progress-indicators/)
- [Estimating Software Projects](https://www.softwaremag.com/archive/issue-6-03-estimating-software-projects/)

---

*End of ADR-005*
