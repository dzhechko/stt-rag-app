# Aggregates
## Feature 1: UI/UX Improvements - Tactical Domain-Driven Design

| Version | Date | Author | Status |
|---------|------|--------|--------|
| 1.0 | 2025-02-03 | System Architect | Draft |

---

## 1. Aggregate Overview

Aggregates are clusters of domain objects that can be treated as a unit. They enforce consistency boundaries around domain invariants.

### 1.1 Aggregate Design Principles

| Principle | Description | Application |
|-----------|-------------|-------------|
| **Consistency Boundary** | Transactions only update one aggregate | Progress state only changes via ProgressTracker |
| **Aggregate Root** | Entry point for aggregate operations | ProgressTracker, NotificationManager |
| **Reference by ID** | Other aggregates reference by ID, not object | Task references ProgressTracker by taskId |
| ** eventual Consistency** | Other aggregates update asynchronously | Progress update triggers eventual notification |
| **Large Aggregates** | Keep aggregates small for performance | Split responsibilities into focused aggregates |

### 1.2 Aggregate Summary Map

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         Aggregate Map                                   │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌──────────────────────┐  ┌──────────────────────┐                    │
│  │  ProgressTracker     │  │  NotificationManager │                    │
│  │  ──────────────────  │  │  ──────────────────  │                    │
│  │  • Progress          │  │  • Notification      │                    │
│  │  • Stage             │  │  • Permission        │                    │
│  │  • TimeEstimate      │  │  • History           │                    │
│  │  • TaskMetadata      │  │                      │                    │
│  └──────────────────────┘  └──────────────────────┘                    │
│                                                                         │
│  ┌──────────────────────┐  ┌──────────────────────┐                    │
│  │  UploadManager       │  │  TranscriptDisplay   │                    │
│  │  ──────────────────  │  │  ──────────────────  │                    │
│  │  • Upload            │  │  • Transcript        │                    │
│  │  • FileValidation    │  │  • Segment           │                    │
│  │  • UploadQueue       │  │  • SearchResult      │                    │
│  └──────────────────────┘  └──────────────────────┘                    │
│                                                                         │
│  ┌──────────────────────┐  ┌──────────────────────┐                    │
│  │  ErrorState          │  │  ThemePreference     │                    │
│  │  ──────────────────  │  │  ──────────────────  │                    │
│  │  • Error             │  │  • Theme             │                    │
│  │  • RecoveryAction    │  │  • AccentColor       │                    │
│  └──────────────────────┘  └──────────────────────┘                    │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 2. ProgressTracker Aggregate

### 2.1 Aggregate Definition

**Purpose**: Track and manage the progress of a single transcription task.

**Aggregate Root**: `ProgressTracker`

**Consistency Boundary**:
- Progress percentage is always 0-100
- Stage transitions follow valid sequence
- Time estimates are never negative

**Invariants**:
1. Percentage cannot decrease without explicit reset
2. Stage must progress in defined order
3. Time remaining >= 0
4. Completed stage cannot be revisited

### 2.2 Aggregate Structure

```typescript
// Aggregate Root
class ProgressTracker {
  private id: ProgressTrackerId;
  private state: ProgressState;
  private version: number;
  private uncommittedEvents: DomainEvent[];

  // Entities owned by aggregate
  private currentStage: Stage;
  private timeEstimate: TimeEstimate;
  private taskMetadata: TaskMetadata;

  // Value objects owned by aggregate
  private percentage: Percentage;
  private startedAt: Timestamp;
  private lastUpdatedAt: Timestamp;

  // Behavior methods
  startTask(metadata: TaskMetadata): void;
  updateProgress(percentage: number, speed?: number): void;
  transitionToStage(stage: Stage): void;
  recalculateEstimate(algorithm: EstimationAlgorithm): void;
  complete(resultUrl: string): void;
  fail(error: ErrorInfo): void;
}

// Entity within aggregate
class Stage {
  private id: StageId;
  private name: StageName;
  private status: StageStatus;
  private startedAt?: Timestamp;
  private completedAt?: Timestamp;
  private progress: Percentage;

  isComplete(): boolean;
  isCurrent(): boolean;
  getDuration(): number;  // seconds
}

// Value Object
class Percentage {
  private readonly value: number;  // 0-100

  of(value: number): Percentage;
  isComplete(): boolean;  // value === 100
  difference(other: Percentage): number;
}

// Value Object
class TimeEstimate {
  private readonly totalSeconds: number;
  private readonly confidence: number;  // 0-1
  private readonly algorithm: string;

  get remaining(): Duration;
  get isReliable(): boolean;
  recalculate(data: ProgressData): TimeEstimate;
}

// Value Object
class Duration {
  private readonly seconds: number;

  get hours(): number;
  get minutes(): number;
  get formatted(): string;  // "HH:MM:SS"
}
```

### 2.3 Aggregate Behaviors

#### Start Task

```typescript
// Start tracking a new task
startTask(metadata: TaskMetadata): void {
  // Guard: Cannot start if already started
  if (this.state !== ProgressState.IDLE) {
    throw new Error("Task already started");
  }

  // Update state
  this.state = ProgressState.IN_PROGRESS;
  this.currentStage = Stage.UPLOADING;
  this.startedAt = Timestamp.now();
  this.taskMetadata = metadata;
  this.percentage = Percentage.of(0);

  // Raise event
  this.raiseEvent<ProgressStartedEvent>({
    eventId: uuid(),
    eventType: "ProgressStarted",
    aggregateId: this.id.value,
    aggregateType: "ProgressTracker",
    timestamp: new Date().toISOString(),
    version: ++this.version,
    payload: {
      taskId: metadata.taskId,
      fileName: metadata.fileName,
      fileSize: metadata.fileSize,
      fileType: metadata.fileType,
      estimatedDuration: this.timeEstimate.remaining.seconds,
      stages: this.getStages()
    }
  });
}
```

#### Update Progress

```typescript
// Update progress percentage
updateProgress(percentage: number, speed?: number): void {
  const newPercentage = Percentage.of(percentage);

  // Guard: Progress cannot go backwards
  if (newPercentage.value < this.percentage.value) {
    throw new Error("Progress cannot decrease");
  }

  const oldPercentage = this.percentage;
  this.percentage = newPercentage;
  this.lastUpdatedAt = Timestamp.now();

  // Raise event
  this.raiseEvent<ProgressUpdatedEvent>({
    eventId: uuid(),
    eventType: "ProgressUpdated",
    aggregateId: this.id.value,
    aggregateType: "ProgressTracker",
    timestamp: new Date().toISOString(),
    version: ++this.version,
    payload: {
      taskId: this.taskMetadata.taskId,
      oldPercentage: oldPercentage.value,
      newPercentage: newPercentage.value,
      stage: this.currentStage.name,
      processingSpeed: speed
    }
  });

  // Auto-recalculate estimate if threshold reached
  if (this.shouldRecalculateEstimate(newPercentage)) {
    this.recalculateEstimate(new EstimationAlgorithm());
  }
}
```

#### Transition to Stage

```typescript
// Move to next stage
transitionToStage(stage: StageName): void {
  const fromStage = this.currentStage;

  // Guard: Validate stage transition
  if (!this.isValidTransition(fromStage.name, stage)) {
    throw new Error(`Invalid stage transition: ${fromStage.name} -> ${stage}`);
  }

  // Complete current stage
  fromStage.complete();

  // Start new stage
  this.currentStage = Stage.start(stage);
  this.lastUpdatedAt = Timestamp.now();

  // Raise event
  this.raiseEvent<StageChangedEvent>({
    eventId: uuid(),
    eventType: "StageChanged",
    aggregateId: this.id.value,
    aggregateType: "ProgressTracker",
    timestamp: new Date().toISOString(),
    version: ++this.version,
    payload: {
      taskId: this.taskMetadata.taskId,
      fromStage: fromStage.name,
      toStage: stage,
      timestamp: new Date().toISOString()
    }
  });
}

private isValidTransition(from: StageName, to: StageName): boolean {
  const transitions = {
    UPLOADING: ["VALIDATING", "FAILED"],
    VALIDATING: ["QUEUED", "FAILED"],
    QUEUED: ["PROCESSING", "FAILED"],
    PROCESSING: ["TRANSCRIBING", "FAILED"],
    TRANSCRIBING: ["FINALIZING", "FAILED"],
    FINALIZING: ["COMPLETED", "FAILED"],
    COMPLETED: [],  // Terminal state
    FAILED: []      // Terminal state
  };

  return transitions[from].includes(to);
}
```

#### Complete Task

```typescript
// Mark task as completed
complete(resultUrl: string): void {
  // Guard: Must be in finalizing stage
  if (this.currentStage.name !== StageName.FINALIZING) {
    throw new Error("Can only complete from FINALIZING stage");
  }

  const duration = this.startedAt.difference(Timestamp.now());

  // Update state
  this.state = ProgressState.COMPLETED;
  this.percentage = Percentage.of(100);
  this.currentStage.complete();
  this.lastUpdatedAt = Timestamp.now();

  // Raise event
  this.raiseEvent<ProgressCompletedEvent>({
    eventId: uuid(),
    eventType: "ProgressCompleted",
    aggregateId: this.id.value,
    aggregateType: "ProgressTracker",
    timestamp: new Date().toISOString(),
    version: ++this.version,
    payload: {
      taskId: this.taskMetadata.taskId,
      duration: duration.seconds,
      resultUrl,
      finalPercentage: 100,
      stagesCompleted: this.getAllStages(),
      timeByStage: this.getTimeByStage()
    }
  });
}
```

---

## 3. NotificationManager Aggregate

### 3.1 Aggregate Definition

**Purpose**: Manage notification delivery, permissions, and history.

**Aggregate Root**: `NotificationManager`

**Consistency Boundary**:
- Permissions are recorded accurately
- Notification history is append-only
- Notification preferences are consistent

**Invariants**:
1. Cannot send notification without permission (for browser notifications)
2. Notification history cannot be modified
3. Notification count never decreases (purge is separate operation)

### 3.2 Aggregate Structure

```typescript
// Aggregate Root
class NotificationManager {
  private id: NotificationManagerId;
  private userId?: UserId;
  private permission: NotificationPermission;
  private preferences: NotificationPreferences;
  private history: NotificationHistory;
  private version: number;
  private uncommittedEvents: DomainEvent[];

  // Behavior methods
  requestPermission(): Promise<NotificationPermission>;
  sendNotification(request: NotificationRequest): NotificationId;
  recordDelivery(notificationId: NotificationId, result: DeliveryResult): void;
  updatePreferences(preferences: Partial<NotificationPreferences>): void;
  dismissNotification(notificationId: NotificationId): void;
  getHistory(limit?: number): NotificationRecord[];
}

// Entity
class NotificationRecord {
  private id: NotificationId;
  private request: NotificationRequest;
  private status: NotificationStatus;
  private sentAt?: Timestamp;
  private dismissedAt?: Timestamp;
  private clickedAt?: Timestamp;

  markAsSent(): void;
  markAsDismissed(): void;
  markAsClicked(): void;
  isPending(): boolean;
  isDelivered(): boolean;
}

// Value Object
class NotificationRequest {
  readonly type: NotificationType;
  readonly title: string;
  readonly message: string;
  readonly channel: NotificationChannel;
  readonly actions: NotificationAction[];
  readonly duration?: number;
  readonly priority: NotificationPriority;

  withChannel(channel: NotificationChannel): NotificationRequest;
  withAction(action: NotificationAction): NotificationRequest;
}

// Value Object
class NotificationPreferences {
  readonly browserEnabled: boolean;
  readonly inAppEnabled: boolean;
  readonly soundEnabled: boolean;
  readonly soundType?: SoundType;

  withBrowserEnabled(enabled: boolean): NotificationPreferences;
  withSoundEnabled(enabled: boolean): NotificationPreferences;
}

// Enum
enum NotificationPermission {
  GRANTED = "GRANTED",
  DENIED = "DENIED",
  DEFAULT = "DEFAULT"
}

enum NotificationChannel {
  BROWSER = "BROWSER",
  IN_APP = "IN_APP",
  SOUND = "SOUND"
}
```

### 3.3 Aggregate Behaviors

#### Request Permission

```typescript
// Request browser notification permission
async requestPermission(): Promise<NotificationPermission> {
  // Guard: Already granted or denied
  if (this.permission !== NotificationPermission.DEFAULT) {
    return this.permission;
  }

  // Request permission from browser
  const result = await NotificationClient.requestPermission();

  // Update state
  const previous = this.permission;
  this.permission = result;

  // Raise event
  if (result === NotificationPermission.GRANTED) {
    this.raiseEvent<NotificationPermissionGrantedEvent>({
      eventId: uuid(),
      eventType: "NotificationPermissionGranted",
      aggregateId: this.id.value,
      aggregateType: "NotificationManager",
      timestamp: new Date().toISOString(),
      version: ++this.version,
      payload: {
        timestamp: new Date().toISOString(),
        previousPermission: previous
      }
    });
  } else if (result === NotificationPermission.DENIED) {
    this.raiseEvent<NotificationPermissionDeniedEvent>({
      eventId: uuid(),
      eventType: "NotificationPermissionDenied",
      aggregateId: this.id.value,
      aggregateType: "NotificationManager",
      timestamp: new Date().toISOString(),
      version: ++this.version,
      payload: {
        timestamp: new Date().toISOString(),
        previousPermission: previous
      }
    });
  }

  return result;
}
```

#### Send Notification

```typescript
// Send a notification
sendNotification(request: NotificationRequest): NotificationId {
  // Guard: Check permission for browser notifications
  if (request.channel === NotificationChannel.BROWSER &&
      this.permission !== NotificationPermission.GRANTED) {
    // Fallback to in-app
    request = request.withChannel(NotificationChannel.IN_APP);
  }

  // Check preferences
  if (request.channel === NotificationChannel.BROWSER && !this.preferences.browserEnabled) {
    return;  // Skip if disabled in preferences
  }

  // Create notification record
  const notificationId = NotificationId.generate();
  const record = new NotificationRecord(notificationId, request);
  this.history.add(record);

  // Raise event
  this.raiseEvent<NotificationRequestedEvent>({
    eventId: uuid(),
    eventType: "NotificationRequested",
    aggregateId: this.id.value,
    aggregateType: "NotificationManager",
    timestamp: new Date().toISOString(),
    version: ++this.version,
    payload: {
      notificationId: notificationId.value,
      type: request.type,
      title: request.title,
      message: request.message,
      channel: request.channel,
      actions: request.actions.map(a => ({
        id: a.id,
        label: a.label,
        action: a.action,
        primary: a.isPrimary
      })),
      duration: request.duration,
      priority: request.priority
    }
  });

  return notificationId;
}
```

---

## 4. UploadManager Aggregate

### 4.1 Aggregate Definition

**Purpose**: Coordinate file upload process including validation, queuing, and progress tracking.

**Aggregate Root**: `UploadManager`

**Consistency Boundary**:
- Upload queue state is consistent
- File validation results are immutable
- Upload progress is monotonic

**Invariants**:
1. Cannot upload invalid file
2. Cannot exceed concurrent upload limit
3. Upload progress only increases

### 4.2 Aggregate Structure

```typescript
// Aggregate Root
class UploadManager {
  private id: UploadManagerId;
  private queue: UploadQueue;
  private activeUploads: Map<UploadId, Upload>;
  private maxConcurrentUploads: number;
  private version: number;

  // Behavior methods
  selectFile(file: FileMetadata): UploadId;
  dropFiles(files: FileMetadata[]): UploadId[];
  validateFile(uploadId: UploadId): ValidationResult;
  startUpload(uploadId: UploadId): void;
  updateUploadProgress(uploadId: UploadId, progress: UploadProgress): void;
  completeUpload(uploadId: UploadId, result: UploadResult): void;
  failUpload(uploadId: UploadId, error: ErrorInfo): void;
  retryUpload(uploadId: UploadId): void;
  cancelUpload(uploadId: UploadId): void;
}

// Entity
class Upload {
  private id: UploadId;
  private file: FileMetadata;
  private status: UploadStatus;
  private progress: UploadProgress;
  private validation?: ValidationResult;
  private result?: UploadResult;
  private error?: ErrorInfo;
  private retryCount: number;
  private createdAt: Timestamp;
  private startedAt?: Timestamp;
  private completedAt?: Timestamp;

  start(): void;
  updateProgress(progress: UploadProgress): void;
  complete(result: UploadResult): void;
  fail(error: ErrorInfo): void;
  retry(): void;
  cancel(): void;
  canRetry(): boolean;
}

// Value Object
class FileMetadata {
  readonly name: string;
  readonly size: number;  // bytes
  readonly type: string;  // MIME type
  readonly lastModified: Date;

  get sizeInMB(): number;
  get sizeInGB(): number;
  isValidFormat(supportedFormats: string[]): boolean;
  isTooLarge(maxSize: number): boolean;
}

// Value Object
class UploadProgress {
  readonly loaded: number;
  readonly total: number;
  readonly percentage: number;
  readonly speed: number;  // bytes/second
  readonly estimatedTimeRemaining: number;  // seconds

  get isComplete(): boolean;
  get formattedSpeed(): string;
  get formattedETA(): string;
}

// Value Object
class ValidationResult {
  readonly isValid: boolean;
  readonly errors: ValidationError[];
  readonly warnings: ValidationWarning[];

  get hasErrors(): boolean;
  get hasWarnings(): boolean;
}
```

### 4.3 Aggregate Behaviors

#### Select File

```typescript
// User selects a file
selectFile(file: FileMetadata): UploadId {
  // Validate file format
  const formatValidation = this.validateFormat(file);
  if (!formatValidation.isValid) {
    throw new FileValidationError(formatValidation.errors);
  }

  // Create upload entity
  const uploadId = UploadId.generate();
  const upload = new Upload(uploadId, file);
  this.queue.add(upload);

  // Raise event
  this.raiseEvent<FileSelectedEvent>({
    eventId: uuid(),
    eventType: "FileSelected",
    aggregateId: this.id.value,
    aggregateType: "UploadManager",
    timestamp: new Date().toISOString(),
    version: ++this.version,
    payload: {
      uploadId: uploadId.value,
      file: {
        name: file.name,
        size: file.size,
        type: file.type,
        lastModified: file.lastModified.toISOString()
      },
      selectionMethod: "PICKER"
    }
  });

  return uploadId;
}

private validateFormat(file: FileMetadata): ValidationResult {
  const supportedFormats = ["audio/mpeg", "audio/wav", "audio/mp4", "video/mp4"];
  const errors: ValidationError[] = [];

  if (!file.isValidFormat(supportedFormats)) {
    errors.push({
      code: "INVALID_FORMAT",
      message: `Unsupported file format: ${file.type}`,
      field: "file"
    });
  }

  return new ValidationResult(errors.length === 0, errors, []);
}
```

#### Start Upload

```typescript
// Begin uploading a file
startUpload(uploadId: UploadId): void {
  const upload = this.queue.get(uploadId);

  // Guard: Upload must be validated first
  if (!upload.validation || !upload.validation.isValid) {
    throw new Error("Cannot start unvalidated upload");
  }

  // Guard: Check concurrent limit
  if (this.activeUploads.size >= this.maxConcurrentUploads) {
    throw new Error("Maximum concurrent uploads reached");
  }

  // Move from queue to active
  this.queue.remove(uploadId);
  this.activeUploads.set(uploadId, upload);

  // Start upload
  upload.start();

  // Raise event
  this.raiseEvent<UploadStartedEvent>({
    eventId: uuid(),
    eventType: "UploadStarted",
    aggregateId: this.id.value,
    aggregateType: "UploadManager",
    timestamp: new Date().toISOString(),
    version: ++this.version,
    payload: {
      uploadId: uploadId.value,
      taskId: upload.taskId,
      file: {
        name: upload.file.name,
        size: upload.file.size,
        type: upload.file.type
      },
      method: "CHUNKED",
      chunkSize: 1024 * 1024  // 1MB chunks
    }
  });
}
```

---

## 5. TranscriptDisplay Aggregate

### 5.1 Aggregate Definition

**Purpose**: Manage transcript display, search, and export.

**Aggregate Root**: `TranscriptDisplay`

**Consistency Boundary**:
- Transcript segments are ordered by timestamp
- Search results are consistent with current query
- Export format is validated

### 5.2 Aggregate Structure

```typescript
// Aggregate Root
class TranscriptDisplay {
  private id: TranscriptDisplayId;
  private taskId: TaskId;
  private transcript: Transcript;
  private searchState: SearchState;
  private displayPreferences: DisplayPreferences;
  private version: number;

  // Behavior methods
  loadTranscript(data: TranscriptData): void;
  search(query: string, options: SearchOptions): SearchResult[];
  navigateToTimestamp(timestamp: number): void;
  export(format: ExportFormat, options: ExportOptions): ExportResult;
  toggleSpeakerLabels(show: boolean): void;
  setLabelFormat(format: LabelFormat): void;
}

// Entity
class Transcript {
  private id: TranscriptId;
  private segments: TranscriptSegment[];
  private metadata: TranscriptMetadata;

  getSegmentByTimestamp(timestamp: number): TranscriptSegment | undefined;
  getSegmentsInRange(start: number, end: number): TranscriptSegment[];
  search(query: string, options: SearchOptions): SearchResult[];
  export(format: ExportFormat, options: ExportOptions): ExportData;
}

// Entity
class TranscriptSegment {
  private id: SegmentId;
  private startTime: number;  // seconds
  private endTime: number;
  private text: string;
  private speaker?: string;
  private confidence: number;

  contains(query: string, options: SearchOptions): boolean;
  getDuration(): number;
  toSRT(): string;
  toVTT(): string;
}

// Value Object
class SearchOptions {
  readonly caseSensitive: boolean;
  readonly wholeWord: boolean;
  readonly regex: boolean;

  withCaseSensitive(enabled: boolean): SearchOptions;
}

// Value Object
class SearchResult {
  readonly segmentId: string;
  readonly timestamp: number;
  readonly match: string;
  readonly context: {
    before: string;
    after: string;
  };
}

// Value Object
class DisplayPreferences {
  readonly showTimestamps: boolean;
  readonly showSpeakers: boolean;
  readonly showConfidence: boolean;
  readonly speakerLabelFormat: LabelFormat;
  readonly fontSize: number;
  readonly lineHeight: number;
}
```

---

## 6. ErrorState Aggregate

### 6.1 Aggregate Definition

**Purpose**: Manage error state, recovery actions, and error reporting.

**Aggregate Root**: `ErrorState`

**Consistency Boundary**:
- Error state is consistent with system state
- Recovery actions are available only for retryable errors
- Error reports are append-only

### 6.2 Aggregate Structure

```typescript
// Aggregate Root
class ErrorState {
  private id: ErrorStateId;
  private taskId?: TaskId;
  private currentError?: ErrorInfo;
  private recoveryActions: RecoveryAction[];
  private retryState?: RetryState;
  private reportHistory: ErrorReport[];
  private version: number;

  // Behavior methods
  setError(error: ErrorInfo, context: ErrorContext): void;
  clearError(): void;
  addRecoveryAction(action: RecoveryAction): void;
  executeRecovery(actionId: string): Promise<void>;
  reportError(comment?: string): ErrorReportId;
}

// Value Object
class ErrorInfo {
  readonly code: string;
  readonly message: string;
  readonly technicalMessage?: string;
  readonly stackTrace?: string;
  readonly severity: ErrorSeverity;
  readonly retryable: boolean;
  readonly category: ErrorCategory;

  static fromUnknown(error: unknown): ErrorInfo;
}

// Value Object
class RecoveryAction {
  readonly id: string;
  readonly label: string;
  readonly action: RecoveryActionType;
  readonly isPrimary: boolean;
  readonly requiresUserConfirmation: boolean;
}

enum RecoveryActionType {
  RETRY = "RETRY",
  RELOAD = "RELOAD",
  CONTACT_SUPPORT = "CONTACT_SUPPORT",
  CHOOSE_DIFFERENT_FILE = "CHOOSE_DIFFERENT_FILE",
  CLEAR_CACHE = "CLEAR_CACHE"
}

enum ErrorCategory {
  NETWORK = "NETWORK",
  VALIDATION = "VALIDATION",
  PROCESSING = "PROCESSING",
  PERMISSION = "PERMISSION",
  UNKNOWN = "UNKNOWN"
}

enum ErrorSeverity {
  LOW = "LOW",
  MEDIUM = "MEDIUM",
  HIGH = "HIGH",
  CRITICAL = "CRITICAL"
}
```

---

## 7. ThemePreference Aggregate

### 7.1 Aggregate Definition

**Purpose**: Manage user's theme and visual preferences.

**Aggregate Root**: `ThemePreference`

**Consistency Boundary**:
- Theme preference is consistent across all components
- Accent color is always valid hex color
- System preference detection is separate from user preference

### 7.2 Aggregate Structure

```typescript
// Aggregate Root
class ThemePreference {
  private id: ThemePreferenceId;
  private userId?: UserId;
  private theme: Theme;
  private accentColor: AccentColor;
  private highContrastEnabled: boolean;
  private autoDetectSystem: boolean;
  private detectedSystemTheme?: SystemTheme;
  private version: number;

  // Behavior methods
  setTheme(theme: Theme, method: ThemeChangeMethod): void;
  setAccentColor(color: string): void;
  toggleHighContrast(enabled: boolean): void;
  setAutoDetectSystem(enabled: boolean): void;
  detectSystemTheme(systemTheme: SystemTheme): void;
}

// Value Object
class Theme {
  readonly name: ThemeName;
  readonly mode: ColorMode;

  static LIGHT: Theme;
  static DARK: Theme;
  static HIGH_CONTRAST: Theme;
}

enum ThemeName {
  LIGHT = "LIGHT",
  DARK = "DARK",
  HIGH_CONTRAST = "HIGH_CONTRAST"
}

enum ColorMode {
  LIGHT = "LIGHT",
  DARK = "DARK"
}

// Value Object
class AccentColor {
  readonly hex: string;
  readonly name?: string;

  private constructor(hex: string) {
    if (!this.isValidHex(hex)) {
      throw new Error("Invalid hex color");
    }
    this.hex = hex;
  }

  private isValidHex(hex: string): boolean {
    return /^#[0-9A-F]{6}$/i.test(hex);
  }

  static fromHex(hex: string): AccentColor;
}
```

---

## 8. Aggregate Collaboration Patterns

### 8.1 Saga: Complete Upload and Transcription

```typescript
// Orchestrates multiple aggregates
class UploadTranscriptionSaga {
  async execute(file: File): Promise<void> {
    // 1. Upload Manager validates and uploads
    const uploadId = await this.uploadManager.selectFile(file);
    const validation = await this.uploadManager.validateFile(uploadId);

    if (!validation.isValid) {
      this.errorState.setError(validation.toError(), {
        component: "UploadManager",
        action: "validateFile"
      });
      return;
    }

    // 2. Start upload
    await this.uploadManager.startUpload(uploadId);

    // 3. Progress tracker starts tracking
    this.progressTracker.startTask({
      taskId: uploadId.value,
      fileName: file.name,
      fileSize: file.size,
      fileType: file.type
    });

    // 4. Listen for upload completion
    this.eventBus.subscribe(UploadCompletedEvent, async (event) => {
      if (event.payload.uploadId === uploadId.value) {
        // 5. Transition progress to processing
        this.progressTracker.transitionToStage(StageName.PROCESSING);
      }
    });

    // 6. Listen for completion
    this.eventBus.subscribe(ProgressCompletedEvent, async (event) => {
      if (event.payload.taskId === uploadId.value) {
        // 7. Send notification
        this.notificationManager.sendNotification(
          new NotificationRequest({
            type: NotificationType.SUCCESS,
            title: "Transcription Complete",
            message: "Your transcript is ready to view",
            channel: NotificationChannel.BROWSER,
            actions: [{
              id: "view",
              label: "View Transcript",
              action: "navigate:/transcript/" + event.payload.taskId,
              isPrimary: true
            }]
          })
        );

        // 8. Load transcript for display
        this.transcriptDisplay.loadTranscript(event.payload.resultUrl);
      }
    });
  }
}
```

### 8.2 Event Correlation

```typescript
// Correlate events across aggregates
class EventCorrelation {
  private aggregateIds = new Map<string, Set<string>>();

  // Link aggregates to a task
  linkAggregates(taskId: string, aggregateId: string): void {
    if (!this.aggregateIds.has(taskId)) {
      this.aggregateIds.set(taskId, new Set());
    }
    this.aggregateIds.get(taskId)!.add(aggregateId);
  }

  // Get all aggregates for a task
  getAggregatesForTask(taskId: string): string[] {
    return Array.from(this.aggregateIds.get(taskId) || []);
  }

  // Correlate events
  correlate(event: DomainEvent): DomainEvent {
    const aggregates = this.getAggregatesForTask(event.aggregateId);
    return {
      ...event,
      correlationId: event.aggregateId,
      linkedAggregates: aggregates
    };
  }
}
```

---

## 9. Aggregate Persistence

### 9.1 Repository Interfaces

```typescript
// Repository for ProgressTracker
interface ProgressTrackerRepository {
  save(tracker: ProgressTracker): Promise<void>;
  findById(id: ProgressTrackerId): Promise<ProgressTracker | null>;
  findByTaskId(taskId: TaskId): Promise<ProgressTracker | null>;
  delete(id: ProgressTrackerId): Promise<void>;
}

// Repository for NotificationManager
interface NotificationManagerRepository {
  save(manager: NotificationManager): Promise<void>;
  findById(id: NotificationManagerId): Promise<NotificationManager | null>;
  findByUserId(userId: UserId): Promise<NotificationManager | null>;
}

// Repository for UploadManager
interface UploadManagerRepository {
  save(manager: UploadManager): Promise<void>;
  findById(id: UploadManagerId): Promise<UploadManager | null>;
}

// Repository for TranscriptDisplay
interface TranscriptDisplayRepository {
  save(display: TranscriptDisplay): Promise<void>;
  findById(id: TranscriptDisplayId): Promise<TranscriptDisplay | null>;
  findByTaskId(taskId: TaskId): Promise<TranscriptDisplay | null>;
}

// Repository for ThemePreference
interface ThemePreferenceRepository {
  save(preference: ThemePreference): Promise<void>;
  findById(id: ThemePreferenceId): Promise<ThemePreference | null>;
  findByUserId(userId: UserId): Promise<ThemePreference | null>;
}
```

### 9.2 Event Store Interface

```typescript
interface EventStore {
  // Append events to store
  append(aggregateId: string, events: DomainEvent[]): Promise<void>;

  // Load events for aggregate
  load(aggregateId: string): Promise<DomainEvent[]>;

  // Load events from version
  loadFromVersion(aggregateId: string, version: number): Promise<DomainEvent[]>;

  // Subscribe to event stream
  subscribe(handler: (event: DomainEvent) => void): () => void;
}
```

---

*End of Aggregates Documentation*
