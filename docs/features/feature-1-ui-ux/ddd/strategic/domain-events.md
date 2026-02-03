# Domain Events
## Feature 1: UI/UX Improvements - Strategic Domain-Driven Design

| Version | Date | Author | Status |
|---------|------|--------|--------|
| 1.0 | 2025-02-03 | System Architect | Draft |

---

## 1. Domain Events Overview

Domain Events represent something that happened in the domain that domain experts care about. They are immutable facts about the past.

### 1.1 Event Design Principles

| Principle | Description | Example |
|-----------|-------------|---------|
| **Past Tense** | Events name things that HAVE happened | `ProgressUpdated` not `UpdateProgress` |
| **Immutable** | Events cannot be changed once created | Append-only event log |
| **Rich Payload** | Events carry all relevant data | Include both old and new values |
| **Business Meaning** | Events reflect domain concepts | `StageChanged` not `StateUpdated` |
| **Timestamped** | Events include when they occurred | `timestamp: ISO8601` |
| **Identified** | Events have unique IDs | `eventId: UUID` |

### 1.2 Event Metadata Structure

```typescript
interface DomainEvent {
  // Event identification
  eventId: string;           // Unique event ID (UUID)
  eventType: string;         // Event type name (e.g., "ProgressUpdated")
  aggregateId: string;       // ID of the aggregate that emitted the event
  aggregateType: string;     // Type of aggregate (e.g., "ProgressTracker")

  // When it happened
  timestamp: string;         // ISO8601 timestamp
  version: number;           // Aggregate version (for optimistic concurrency)

  // Causality
  correlationId?: string;    // Links related events
  causationId?: string;      // Event that caused this event

  // Event data
  payload: unknown;          // Event-specific data
}
```

---

## 2. Progress Tracking Events

### 2.1 ProgressUpdated Event

Emitted when the progress percentage changes.

```typescript
interface ProgressUpdatedEvent extends DomainEvent {
  eventType: "ProgressUpdated";
  aggregateType: "ProgressTracker";

  payload: {
    taskId: string;                  // ID of the task
    oldPercentage: number;           // Previous progress (0-100)
    newPercentage: number;           // New progress (0-100)
    stage: Stage;                    // Current stage
    bytesProcessed?: number;         // Bytes processed (for uploads)
    bytesTotal?: number;             // Total bytes
    processingSpeed?: number;        // Speed (bytes/second or words/second)
  };
}
```

**Use Cases**:
- Update progress bar UI
- Trigger time estimate recalculation
- Log progress for analytics
- Check for milestone achievements (25%, 50%, 75%, 100%)

**Subscribers**:
- `ProgressUIComponent` - Updates visual progress bar
- `TimeEstimationService` - Recalculates ETA
- `NotificationService` - Checks for notification thresholds
- `AnalyticsService` - Logs progress metrics

### 2.2 StageChanged Event

Emitted when a task transitions to a new stage.

```typescript
interface StageChangedEvent extends DomainEvent {
  eventType: "StageChanged";
  aggregateType: "ProgressTracker";

  payload: {
    taskId: string;
    fromStage: Stage;                 // Previous stage
    toStage: Stage;                   // New stage
    timestamp: string;                // When the transition occurred
    reason?: string;                  // Optional reason for change
  };
}
```

**Use Cases**:
- Update stage indicator UI
- Trigger stage-specific notifications
- Calculate stage durations for analytics
- Update time estimates based on stage

**Subscribers**:
- `StageIndicatorComponent` - Updates stage display
- `TimeEstimationService` - Recalculates based on stage
- `NotificationService` - Sends stage transition notification
- `AnalyticsService` - Tracks stage timing

### 2.3 ProgressStarted Event

Emitted when a task begins processing.

```typescript
interface ProgressStartedEvent extends DomainEvent {
  eventType: "ProgressStarted";
  aggregateType: "ProgressTracker";

  payload: {
    taskId: string;
    fileName: string;
    fileSize: number;
    fileType: string;
    estimatedDuration?: number;       // Initial estimate in seconds
    stages: Stage[];                  // Stages that will be executed
  };
}
```

**Use Cases**:
- Initialize progress tracking UI
- Start time estimation
- Create notification for completion
- Log start time for analytics

**Subscribers**:
- `ProgressTracker` - Initializes tracking state
- `TimeEstimationService` - Creates initial estimate
- `NotificationService` - Schedules completion notification
- `AnalyticsService` - Records task start

### 2.4 ProgressCompleted Event

Emitted when a task completes successfully.

```typescript
interface ProgressCompletedEvent extends DomainEvent {
  eventType: "ProgressCompleted";
  aggregateType: "ProgressTracker";

  payload: {
    taskId: string;
    duration: number;                 // Total duration in seconds
    resultUrl: string;                // URL to transcript
    finalPercentage: number;          // Should be 100
    stagesCompleted: Stage[];         // All completed stages
    timeByStage: Record<Stage, number>; // Time spent in each stage
  };
}
```

**Use Cases**:
- Show completion UI
- Send completion notification
- Clear progress tracking
- Navigate to transcript view

**Subscribers**:
- `ProgressUIComponent` - Shows completion state
- `NotificationService` - Sends completion notification
- `TranscriptDisplayService` - Loads transcript
- `Router` - Navigates to transcript view
- `AnalyticsService` - Records completion metrics

### 2.5 ProgressFailed Event

Emitted when a task fails.

```typescript
interface ProgressFailedEvent extends DomainEvent {
  eventType: "ProgressFailed";
  aggregateType: "ProgressTracker";

  payload: {
    taskId: string;
    error: {
      code: string;                   // Error code
      message: string;                // User-friendly message
      technical?: string;             // Technical details
    };
    stage: Stage;                     // Stage where failure occurred
    percentage: number;               // Progress at failure
    retryable: boolean;               // Whether user can retry
    retryAfter?: number;              // Delay before retry (seconds)
  };
}
```

**Use Cases**:
- Display error UI with recovery options
- Send error notification
- Log error for support
- Offer retry if applicable

**Subscribers**:
- `ErrorHandlingService` - Displays error with recovery
- `NotificationService` - Sends error notification
- `RetryService` - Manages retry logic
- `AnalyticsService` - Records failure metrics
- `SupportService` - Logs error for support

### 2.6 TimeEstimateUpdated Event

Emitted when the time estimate is recalculated.

```typescript
interface TimeEstimateUpdatedEvent extends DomainEvent {
  eventType: "TimeEstimateUpdated";
  aggregateType: "ProgressTracker";

  payload: {
    taskId: string;
    oldEstimate?: number;             // Previous estimate (seconds)
    newEstimate: number;              // New estimate (seconds)
    confidence: number;               // 0-1, how confident we are
    algorithm: string;                // Algorithm used (e.g., "linear", "ml")
    dataPoints: number;               // Amount of data used for estimate
  };
}
```

**Use Cases**:
- Update time remaining display
- Send notification for significant changes
- Track estimation accuracy

**Subscribers**:
- `TimeEstimationUIComponent` - Updates time display
- `NotificationService` - Notifies on significant changes
- `AnalyticsService` - Tracks estimation accuracy

---

## 3. Notification Events

### 3.1 NotificationRequested Event

Emitted when a notification should be sent.

```typescript
interface NotificationRequestedEvent extends DomainEvent {
  eventType: "NotificationRequested";
  aggregateType: "NotificationManager";

  payload: {
    notificationId: string;
    type: NotificationType;           // INFO, SUCCESS, WARNING, ERROR
    title: string;
    message: string;
    channel: NotificationChannel;     // BROWSER, IN_APP, SOUND
    actions?: NotificationAction[];   // Optional action buttons
    duration?: number;                // Auto-dismiss duration (ms)
    priority: NotificationPriority;   // LOW, NORMAL, HIGH, URGENT
  };
}

type NotificationType = "INFO" | "SUCCESS" | "WARNING" | "ERROR";
type NotificationChannel = "BROWSER" | "IN_APP" | "SOUND";
type NotificationPriority = "LOW" | "NORMAL" | "HIGH" | "URGENT";

interface NotificationAction {
  id: string;
  label: string;
  action: string;                    // Action to perform
  primary?: boolean;                 // Is this the primary action?
}
```

**Use Cases**:
- Send browser notification
- Display in-app toast
- Play notification sound

**Subscribers**:
- `BrowserNotificationService` - Sends browser notification
- `ToastNotificationService` - Displays in-app toast
- `SoundNotificationService` - Plays sound

### 3.2 NotificationPermissionGranted Event

Emitted when user grants notification permission.

```typescript
interface NotificationPermissionGrantedEvent extends DomainEvent {
  eventType: "NotificationPermissionGranted";
  aggregateType: "NotificationManager";

  payload: {
    timestamp: string;
    previousPermission: NotificationPermission;
  };
}

type NotificationPermission = "GRANTED" | "DENIED" | "DEFAULT";
```

**Use Cases**:
- Enable browser notifications
- Update UI to show notifications enabled
- Record permission in analytics

**Subscribers**:
- `NotificationPreferenceService` - Saves permission
- `NotificationUIComponent` - Updates permission indicator
- `AnalyticsService` - Records permission grant

### 3.3 NotificationPermissionDenied Event

Emitted when user denies notification permission.

```typescript
interface NotificationPermissionDeniedEvent extends DomainEvent {
  eventType: "NotificationPermissionDenied";
  aggregateType: "NotificationManager";

  payload: {
    timestamp: string;
    previousPermission: NotificationPermission;
  };
}
```

**Use Cases**:
- Fall back to in-app notifications only
- Show educational message about enabling notifications
- Record denial in analytics

**Subscribers**:
- `NotificationPreferenceService` - Records denial
- `NotificationUIComponent` - Shows in-app only message
- `AnalyticsService` - Records permission denial

### 3.4 NotificationClicked Event

Emitted when user clicks on a notification.

```typescript
interface NotificationClickedEvent extends DomainEvent {
  eventType: "NotificationClicked";
  aggregateType: "NotificationManager";

  payload: {
    notificationId: string;
    action?: string;                  // Action ID if button clicked
    clickedAt: string;                // When clicked
    timeSinceShown: number;           // Milliseconds since notification was shown
  };
}
```

**Use Cases**:
- Navigate to relevant page
- Perform the requested action
- Track notification engagement

**Subscribers**:
- `Router` - Navigates to target page
- `ActionHandler` - Executes the action
- `AnalyticsService` - Tracks engagement

### 3.5 NotificationDismissed Event

Emitted when user dismisses a notification.

```typescript
interface NotificationDismissedEvent extends DomainEvent {
  eventType: "NotificationDismissed";
  aggregateType: "NotificationManager";

  payload: {
    notificationId: string;
    dismissedAt: string;
    dismissalMethod: "CLICK" | "TIMEOUT" | "PROGRAMMATIC";
    timeSinceShown: number;
  };
}
```

**Use Cases**:
- Remove notification from UI
- Record dismissal for analytics
- Update notification history

**Subscribers**:
- `NotificationUIComponent` - Removes notification
- `NotificationHistoryService` - Records dismissal
- `AnalyticsService` - Tracks dismissal rates

---

## 4. File Upload Events

### 4.1 FileSelected Event

Emitted when user selects a file via file picker.

```typescript
interface FileSelectedEvent extends DomainEvent {
  eventType: "FileSelected";
  aggregateType: "UploadManager";

  payload: {
    uploadId: string;
    file: {
      name: string;
      size: number;
      type: string;
      lastModified: string;
    };
    selectionMethod: "PICKER" | "DROP";
  };
}
```

**Use Cases**:
- Validate file
- Show file preview
- Start upload process

**Subscribers**:
- `FileValidationService` - Validates file
- `UploadUIComponent` - Shows file preview
- `UploadService` - Initiates upload

### 4.2 FileDropped Event

Emitted when user drops files on drag zone.

```typescript
interface FileDroppedEvent extends DomainEvent {
  eventType: "FileDropped";
  aggregateType: "UploadManager";

  payload: {
    uploadId: string;
    files: Array<{
      name: string;
      size: number;
      type: string;
    }>;
    dropPosition: { x: number; y: number; };
  };
}
```

**Use Cases**:
- Validate all dropped files
- Add to upload queue
- Show queue preview

**Subscribers**:
- `FileValidationService` - Validates all files
- `UploadQueueService` - Adds to queue
- `UploadUIComponent` - Shows queue

### 4.3 FileValidated Event

Emitted after file validation completes.

```typescript
interface FileValidatedEvent extends DomainEvent {
  eventType: "FileValidated";
  aggregateType: "FileValidator";

  payload: {
    uploadId: string;
    file: {
      name: string;
      size: number;
      type: string;
    };
    isValid: boolean;
    errors: ValidationError[];
    warnings: ValidationWarning[];
  };

  ValidationError: {
    code: string;
    message: string;
    field?: string;
  };

  ValidationWarning: {
    code: string;
    message: string;
  };
}
```

**Use Cases**:
- Show validation errors
- Enable/disable upload button
- Display warnings

**Subscribers**:
- `UploadUIComponent` - Shows validation results
- `UploadButtonComponent` - Enables/disables button
- `NotificationService` - Shows validation errors

### 4.4 UploadStarted Event

Emitted when file upload begins.

```typescript
interface UploadStartedEvent extends DomainEvent {
  eventType: "UploadStarted";
  aggregateType: "UploadManager";

  payload: {
    uploadId: string;
    taskId: string;
    file: {
      name: string;
      size: number;
      type: string;
    };
    method: "CHUNKED" | "DIRECT";
    chunkSize?: number;
  };
}
```

**Use Cases**:
- Initialize progress tracking
- Start upload progress UI
- Create upload record

**Subscribers**:
- `ProgressTracker` - Starts progress tracking
- `UploadProgressUIComponent` - Shows upload progress
- `UploadRepository` - Saves upload record

### 4.5 UploadProgress Event

Emitted during upload progress.

```typescript
interface UploadProgressEvent extends DomainEvent {
  eventType: "UploadProgress";
  aggregateType: "UploadManager";

  payload: {
    uploadId: string;
    loaded: number;                   // Bytes uploaded
    total: number;                    // Total bytes
    percentage: number;               // 0-100
    speed: number;                    // Bytes/second
    estimatedTimeRemaining: number;   // Seconds
  };
}
```

**Use Cases**:
- Update upload progress bar
- Update time estimate
- Show upload speed

**Subscribers**:
- `UploadProgressUIComponent` - Updates progress bar
- `TimeEstimationService` - Updates ETA
- `UploadStatisticsService` - Records upload metrics

### 4.6 UploadCompleted Event

Emitted when upload completes successfully.

```typescript
interface UploadCompletedEvent extends DomainEvent {
  eventType: "UploadCompleted";
  aggregateType: "UploadManager";

  payload: {
    uploadId: string;
    taskId: string;
    duration: number;                 // Upload duration in seconds
    averageSpeed: number;             // Bytes/second
    serverResponse: {
      fileId: string;
      fileUrl: string;
    };
  };
}
```

**Use Cases**:
- Transition to processing stage
- Update upload statistics
- Clear upload UI

**Subscribers**:
- `ProgressTracker` - Transitions to processing stage
- `UploadStatisticsService` - Records completion
- `UploadUIComponent` - Shows upload complete

---

## 5. Transcript Display Events

### 5.1 TranscriptLoaded Event

Emitted when transcript data is loaded.

```typescript
interface TranscriptLoadedEvent extends DomainEvent {
  eventType: "TranscriptLoaded";
  aggregateType: "TranscriptDisplay";

  payload: {
    taskId: string;
    transcript: {
      id: string;
      text: string;
      segments: TranscriptSegment[];
      metadata: {
        duration: number;
        wordCount: number;
        language: string;
        createdAt: string;
      };
    };
  };

  TranscriptSegment: {
    id: string;
    startTime: number;               // Seconds
    endTime: number;
    text: string;
    speaker?: string;
    confidence: number;
  };
}
```

**Use Cases**:
- Display transcript
- Initialize search
- Setup timestamp navigation

**Subscribers**:
- `TranscriptDisplayComponent` - Renders transcript
- `SearchService` - Initializes search index
- `TimestampNavigationService` - Setup navigation

### 5.2 TimestampClicked Event

Emitted when user clicks a timestamp.

```typescript
interface TimestampClickedEvent extends DomainEvent {
  eventType: "TimestampClicked";
  aggregateType: "TranscriptDisplay";

  payload: {
    taskId: string;
    timestamp: number;                // Seconds
    segmentId: string;
    autoScroll: boolean;              // Whether to scroll transcript
  };
}
```

**Use Cases**:
- Seek audio player
- Scroll transcript to position
- Highlight active segment

**Subscribers**:
- `AudioPlayerService` - Seeks to timestamp
- `TranscriptScrollService` - Scrolls to segment
- `SegmentHighlightService` - Highlights segment

### 5.3 SearchRequested Event

Emitted when user searches within transcript.

```typescript
interface SearchRequestedEvent extends DomainEvent {
  eventType: "SearchRequested";
  aggregateType: "TranscriptSearch";

  payload: {
    taskId: string;
    query: string;
    options: {
      caseSensitive: boolean;
      wholeWord: boolean;
      regex: boolean;
    };
  };
}
```

**Use Cases**:
- Search transcript text
- Highlight search results
- Navigate between results

**Subscribers**:
- `SearchService` - Performs search
- `TranscriptHighlightService` - Highlights results
- `SearchResultsUIComponent` - Shows results count

### 5.4 ExportRequested Event

Emitted when user requests transcript export.

```typescript
interface ExportRequestedEvent extends DomainEvent {
  eventType: "ExportRequested";
  aggregateType: "TranscriptExport";

  payload: {
    taskId: string;
    format: "TXT" | "SRT" | "JSON" | "VTT";
    options: {
      includeTimestamps: boolean;
      includeSpeakers: boolean;
      includeConfidence: boolean;
    };
    filename?: string;
  };
}
```

**Use Cases**:
- Generate export file
- Trigger download
- Log export for analytics

**Subscribers**:
- `ExportService` - Generates file
- `DownloadService` - Triggers download
- `AnalyticsService` - Records export

### 5.5 SpeakerLabelToggled Event

Emitted when user toggles speaker label display.

```typescript
interface SpeakerLabelToggledEvent extends DomainEvent {
  eventType: "SpeakerLabelToggled";
  aggregateType: "TranscriptDisplay";

  payload: {
    taskId: string;
    showLabels: boolean;
    labelFormat: "LETTERS" | "NAMES" | "NUMBERS";
  };
}
```

**Use Cases**:
- Show/hide speaker labels
- Change label format
- Save user preference

**Subscribers**:
- `TranscriptDisplayComponent` - Toggles label display
- `UserPreferenceService` - Saves preference

---

## 6. Error Handling Events

### 6.1 ErrorOccurred Event

Emitted when an error occurs.

```typescript
interface ErrorOccurredEvent extends DomainEvent {
  eventType: "ErrorOccurred";
  aggregateType: "ErrorHandler";

  payload: {
    errorId: string;
    taskId?: string;
    error: {
      code: string;
      message: string;
      technicalMessage?: string;
      stackTrace?: string;
    };
    context: {
      component: string;
      action: string;
      userAction?: string;
    };
    severity: "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
    userFacing: boolean;              // Should this be shown to user?
    retryable: boolean;
  };
}
```

**Use Cases**:
- Display error to user
- Log error for support
- Trigger retry if applicable

**Subscribers**:
- `ErrorDisplayComponent` - Shows error UI
- `ErrorLoggingService` - Logs to backend
- `RetryService` - Initiates retry if applicable

### 6.2 RetryRequested Event

Emitted when user requests a retry.

```typescript
interface RetryRequestedEvent extends DomainEvent {
  eventType: "RetryRequested";
  aggregateType: "RetryHandler";

  payload: {
    retryId: string;
    taskId: string;
    originalErrorId: string;
    attemptNumber: number;
    maxAttempts: number;
    retryContext: {
      stage: Stage;
      stateAtError: unknown;
    };
  };
}
```

**Use Cases**:
- Execute retry logic
- Update UI to show retrying
- Track retry attempts

**Subscribers**:
- `RetryService` - Executes retry
- `RetryUIComponent` - Shows retry status
- `AnalyticsService` - Tracks retry rate

### 6.3 ErrorResolved Event

Emitted when an error is resolved.

```typescript
interface ErrorResolvedEvent extends DomainEvent {
  eventType: "ErrorResolved";
  aggregateType: "ErrorHandler";

  payload: {
    errorId: string;
    resolution: "RETRY_SUCCESS" | "USER_ACTION" | "AUTOMATIC";
    resolvedAt: string;
    timeToResolve: number;            // Seconds
  };
}
```

**Use Cases**:
- Clear error UI
- Resume normal operation
- Log resolution for analytics

**Subscribers**:
- `ErrorDisplayComponent` - Clears error
- `ProgressTracker` - Resumes progress
- `AnalyticsService` - Records resolution

### 6.4 ErrorReported Event

Emitted when user reports an error to support.

```typescript
interface ErrorReportedEvent extends DomainEvent {
  eventType: "ErrorReported";
  aggregateType: "ErrorHandler";

  payload: {
    errorId: string;
    reportId: string;
    userComment?: string;
    includeDiagnosticData: boolean;
    reportedAt: string;
  };
}
```

**Use Cases**:
- Submit error report to support
- Show confirmation to user
- Track error reports

**Subscribers**:
- `SupportService` - Submits report
- `NotificationService` - Shows confirmation
- `AnalyticsService` - Tracks report rate

---

## 7. Theme Events

### 7.1 ThemeChanged Event

Emitted when user changes theme.

```typescript
interface ThemeChangedEvent extends DomainEvent {
  eventType: "ThemeChanged";
  aggregateType: "ThemeManager";

  payload: {
    fromTheme: Theme;
    toTheme: Theme;
    changeMethod: "USER_TOGGLE" | "SYSTEM_DETECTED" | "PREFERENCE_LOADED";
  };

  Theme: "LIGHT" | "DARK" | "HIGH_CONTRAST";
}
```

**Use Cases**:
- Apply theme to all components
- Save theme preference
- Update theme toggle UI

**Subscribers**:
- `ThemeProvider` - Applies theme to React tree
- `ThemePreferenceService` - Saves preference
- `ThemeToggleComponent` - Updates button state

### 7.2 AccentColorChanged Event

Emitted when user changes accent color.

```typescript
interface AccentColorChangedEvent extends DomainEvent {
  eventType: "AccentColorChanged";
  aggregateType: "ThemeManager";

  payload: {
    fromColor: string;                // Hex color
    toColor: string;
  };
}
```

**Use Cases**:
- Apply accent color to components
- Save color preference
- Update color picker UI

**Subscribers**:
- `ThemeProvider` - Applies color variables
- `ThemePreferenceService` - Saves preference
- `ColorPickerComponent` - Updates picker

### 7.3 SystemThemeDetected Event

Emitted when system theme preference is detected.

```typescript
interface SystemThemeDetectedEvent extends DomainEvent {
  eventType: "SystemThemeDetected";
  aggregateType: "ThemeManager";

  payload: {
    systemPreference: "LIGHT" | "DARK";
    detectedAt: string;
    browser: string;
  };
}
```

**Use Cases**:
- Auto-switch to match system
- Update system preference indicator
- Enable/disable auto theme switching

**Subscribers**:
- `ThemeManager` - Switches theme if auto-enabled
- `SystemPreferenceUIComponent` - Shows system preference

### 7.4 HighContrastToggled Event

Emitted when high contrast mode is toggled.

```typescript
interface HighContrastToggledEvent extends DomainEvent {
  eventType: "HighContrastToggled";
  aggregateType: "ThemeManager";

  payload: {
    enabled: boolean;
    toggleMethod: "USER_TOGGLE" | "SYSTEM_PREFERENCE";
  };
}
```

**Use Cases**:
- Apply high contrast colors
- Save preference
- Update accessibility tree

**Subscribers**:
- `ThemeProvider` - Applies high contrast theme
- `AccessibilityService` - Updates ARIA attributes
- `ThemePreferenceService` - Saves preference

---

## 8. Event Schemas (TypeScript)

### 8.1 Base Event Type

```typescript
// Base domain event type
interface BaseDomainEvent {
  eventId: string;
  eventType: string;
  aggregateId: string;
  aggregateType: string;
  timestamp: string;
  version: number;
  correlationId?: string;
  causationId?: string;
}

// Union type of all events
type DomainEvent =
  | ProgressUpdatedEvent
  | StageChangedEvent
  | ProgressStartedEvent
  | ProgressCompletedEvent
  | ProgressFailedEvent
  | TimeEstimateUpdatedEvent
  | NotificationRequestedEvent
  | NotificationPermissionGrantedEvent
  | NotificationPermissionDeniedEvent
  | NotificationClickedEvent
  | NotificationDismissedEvent
  | FileSelectedEvent
  | FileDroppedEvent
  | FileValidatedEvent
  | UploadStartedEvent
  | UploadProgressEvent
  | UploadCompletedEvent
  | TranscriptLoadedEvent
  | TimestampClickedEvent
  | SearchRequestedEvent
  | ExportRequestedEvent
  | SpeakerLabelToggledEvent
  | ErrorOccurredEvent
  | RetryRequestedEvent
  | ErrorResolvedEvent
  | ErrorReportedEvent
  | ThemeChangedEvent
  | AccentColorChangedEvent
  | SystemThemeDetectedEvent
  | HighContrastToggledEvent;
```

### 8.2 Event Handler Type

```typescript
// Event handler signature
type EventHandler<T extends DomainEvent> = (event: T) => void | Promise<void>;

// Event bus interface
interface EventBus {
  publish<T extends DomainEvent>(event: T): void;
  subscribe<T extends DomainEvent>(
    eventType: string,
    handler: EventHandler<T>
  ): () => void;  // Returns unsubscribe function
  subscribeToAll(handler: EventHandler<DomainEvent>): () => void;
}
```

---

## 9. Event Flow Examples

### 9.1 Successful Transcription Flow

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        Event Flow: Successful Upload                    │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  1. FileSelected                                                       │
│     └─> FileValidated (valid)                                          │
│         └─> UploadStarted                                              │
│             ├─> ProgressStarted                                        │
│             └─> UploadProgress (multiple)                              │
│                 └─> UploadCompleted                                    │
│                     └─> StageChanged (UPLOADING → QUEUED)              │
│                         └─> StageChanged (QUEUED → PROCESSING)        │
│                             └─> ProgressUpdated (multiple)             │
│                                 └─> StageChanged (PROCESSING → TRANSCRIBING) │
│                                     └─> ProgressUpdated (multiple)     │
│                                         └─> StageChanged (TRANSCRIBING → FINALIZING) │
│                                             └─> ProgressUpdated       │
│                                                 └─> ProgressCompleted  │
│                                                     ├─> NotificationRequested │
│                                                     └─> TranscriptLoaded │
└─────────────────────────────────────────────────────────────────────────┘
```

### 9.2 Error and Retry Flow

```
┌─────────────────────────────────────────────────────────────────────────┐
│                       Event Flow: Error with Retry                      │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  1. UploadStarted                                                      │
│      └─> UploadProgress (45%)                                          │
│          └─> ErrorOccurred (network timeout)                           │
│              ├─> NotificationRequested (error)                          │
│              └─> RetryRequested (user clicks retry)                    │
│                  └─> UploadProgress (resumes from 45%)                 │
│                      └─> UploadCompleted                               │
│                          └─> ErrorResolved                             │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 10. Event Publishing Patterns

### 10.1 Direct Publishing

```typescript
// Within an aggregate
class ProgressTracker {
  updateProgress(percentage: number) {
    const oldPercentage = this.state.percentage;
    this.state.percentage = percentage;

    // Publish event
    this.eventBus.publish<ProgressUpdatedEvent>({
      eventId: uuid(),
      eventType: "ProgressUpdated",
      aggregateId: this.id,
      aggregateType: "ProgressTracker",
      timestamp: new Date().toISOString(),
      version: this.version++,
      payload: {
        taskId: this.taskId,
        oldPercentage,
        newPercentage: percentage,
        stage: this.stage
      }
    });
  }
}
```

### 10.2 Event Sourcing

```typescript
// Rebuild state from events
class ProgressTracker {
  static fromEvents(events: DomainEvent[]): ProgressTracker {
    const tracker = new ProgressTracker();
    for (const event of events) {
      tracker.apply(event);
    }
    return tracker;
  }

  private apply(event: DomainEvent) {
    switch (event.eventType) {
      case "ProgressUpdated":
        this.state.percentage = event.payload.newPercentage;
        break;
      case "StageChanged":
        this.state.stage = event.payload.toStage;
        break;
      // ... other cases
    }
  }
}
```

---

*End of Domain Events Documentation*
