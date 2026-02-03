# Entities and Value Objects
## Feature 1: UI/UX Improvements - Tactical Domain-Driven Design

| Version | Date | Author | Status |
|---------|------|--------|--------|
| 1.0 | 2025-02-03 | System Architect | Draft |

---

## 1. Entities vs Value Objects

### 1.1 Comparison Table

| Aspect | Entity | Value Object |
|--------|--------|--------------|
| **Identity** | Has unique ID, identity matters | No identity, value matters |
| **Mutability** | Can change over time | Immutable |
| **Comparison** | Compared by ID | Compared by value |
| **Lifecycle** | Long-lived, tracked | Short-lived, created/destroyed |
| **Example** | ProgressTracker, Notification | Percentage, TimeEstimate |

### 1.2 Decision Tree

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    Entity vs Value Object Decision                      │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  Does this concept need an identity that persists over time?            │
│       │                                                                │
│       ├─ YES → ENTITY                                                  │
│       │        - ProgressTracker                                        │
│       │        - NotificationRecord                                     │
│       │        - Upload                                                │
│       │        - TranscriptSegment                                      │
│       │                                                                │
│       └─ NO → VALUE OBJECT                                             │
│                - Percentage                                            │
│                - Duration                                              │
│                - Timestamp                                             │
│                - FileMetadata                                          │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Entities

### 2.1 ProgressTracker (Entity)

**Identity**: `ProgressTrackerId` (UUID)

**Lifecycle**: Created on task start, completed/failed when task ends

```typescript
class ProgressTracker {
  readonly id: ProgressTrackerId;
  private state: ProgressState;
  private percentage: Percentage;
  private currentStage: Stage;
  private timeEstimate: TimeEstimate;
  private taskMetadata: TaskMetadata;
  private startedAt: Timestamp;
  private completedAt?: Timestamp;
  private version: number;

  constructor(id: ProgressTrackerId) {
    this.id = id;
    this.state = ProgressState.IDLE;
    this.percentage = Percentage.of(0);
    this.currentStage = Stage.UPLOADING;
    this.startedAt = Timestamp.now();
    this.version = 0;
  }

  // Identity is based on ID
  equals(other: ProgressTracker): boolean {
    return this.id.equals(other.id);
  }

  // State changes over time
  updateProgress(newPercentage: number): void {
    this.percentage = Percentage.of(newPercentage);
    this.version++;
  }

  complete(): void {
    this.state = ProgressState.COMPLETED;
    this.completedAt = Timestamp.now();
    this.percentage = Percentage.of(100);
    this.version++;
  }
}

// Value Object for ID
class ProgressTrackerId {
  private readonly value: string;

  private constructor(value: string) {
    if (!UUID.validate(value)) {
      throw new Error("Invalid ProgressTrackerId");
    }
    this.value = value;
  }

  static generate(): ProgressTrackerId {
    return new ProgressTrackerId(UUID.v4());
  }

  static fromString(value: string): ProgressTrackerId {
    return new ProgressTrackerId(value);
  }

  equals(other: ProgressTrackerId): boolean {
    return this.value === other.value;
  }

  toString(): string {
    return this.value;
  }
}
```

### 2.2 NotificationRecord (Entity)

**Identity**: `NotificationId` (UUID)

**Lifecycle**: Created when notification requested, ends when dismissed/timeout

```typescript
class NotificationRecord {
  readonly id: NotificationId;
  private request: NotificationRequest;
  private status: NotificationStatus;
  private sentAt?: Timestamp;
  private dismissedAt?: Timestamp;
  private clickedAt?: Timestamp;
  private clickCount: number;

  constructor(
    id: NotificationId,
    request: NotificationRequest
  ) {
    this.id = id;
    this.request = request;
    this.status = NotificationStatus.PENDING;
    this.clickCount = 0;
  }

  // Identity
  equals(other: NotificationRecord): boolean {
    return this.id.equals(other.id);
  }

  // State transitions
  markAsSent(): void {
    this.status = NotificationStatus.SENT;
    this.sentAt = Timestamp.now();
  }

  markAsDismissed(): void {
    if (this.status !== NotificationStatus.SENT) return;
    this.status = NotificationStatus.DISMISSED;
    this.dismissedAt = Timestamp.now();
  }

  markAsClicked(): void {
    if (this.status !== NotificationStatus.SENT) return;
    this.status = NotificationStatus.CLICKED;
    this.clickedAt = Timestamp.now();
    this.clickCount++;
  }

  // Behavior
  isPending(): boolean {
    return this.status === NotificationStatus.PENDING;
  }

  isDelivered(): boolean {
    return this.status === NotificationStatus.SENT ||
           this.status === NotificationStatus.CLICKED ||
           this.status === NotificationStatus.DISMISSED;
  }

  getTimeSinceSent(): Duration | null {
    if (!this.sentAt) return null;
    return this.sentAt.difference(Timestamp.now());
  }
}

enum NotificationStatus {
  PENDING = "PENDING",
  SENT = "SENT",
  CLICKED = "CLICKED",
  DISMISSED = "DISMISSED",
  EXPIRED = "EXPIRED"
}
```

### 2.3 Upload (Entity)

**Identity**: `UploadId` (UUID)

**Lifecycle**: Created on file selection, ends on completion/failure/cancellation

```typescript
class Upload {
  readonly id: UploadId;
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

  constructor(id: UploadId, file: FileMetadata) {
    this.id = id;
    this.file = file;
    this.status = UploadStatus.PENDING;
    this.progress = UploadProgress.initial();
    this.retryCount = 0;
    this.createdAt = Timestamp.now();
  }

  equals(other: Upload): boolean {
    return this.id.equals(other.id);
  }

  // State transitions
  start(): void {
    if (this.status !== UploadStatus.PENDING) {
      throw new Error("Upload already started");
    }
    this.status = UploadStatus.UPLOADING;
    this.startedAt = Timestamp.now();
  }

  updateProgress(newProgress: UploadProgress): void {
    if (this.status !== UploadStatus.UPLOADING) return;

    // Guard: Progress is monotonic
    if (newProgress.percentage < this.progress.percentage) {
      throw new Error("Progress cannot decrease");
    }

    this.progress = newProgress;
  }

  complete(result: UploadResult): void {
    this.status = UploadStatus.COMPLETED;
    this.completedAt = Timestamp.now();
    this.result = result;
    this.progress = UploadProgress.complete();
  }

  fail(error: ErrorInfo): void {
    this.status = UploadStatus.FAILED;
    this.completedAt = Timestamp.now();
    this.error = error;
  }

  retry(): void {
    if (!this.canRetry()) {
      throw new Error("Upload cannot be retried");
    }
    this.status = UploadStatus.UPLOADING;
    this.retryCount++;
    this.error = undefined;
    this.startedAt = Timestamp.now();
  }

  cancel(): void {
    this.status = UploadStatus.CANCELLED;
    this.completedAt = Timestamp.now();
  }

  // Queries
  canRetry(): boolean {
    return this.status === UploadStatus.FAILED &&
           this.error?.retryable === true &&
           this.retryCount < 3;
  }

  getDuration(): Duration | null {
    if (!this.startedAt || !this.completedAt) return null;
    return this.startedAt.difference(this.completedAt);
  }
}

enum UploadStatus {
  PENDING = "PENDING",
  UPLOADING = "UPLOADING",
  COMPLETED = "COMPLETED",
  FAILED = "FAILED",
  CANCELLED = "CANCELLED"
}
```

### 2.4 TranscriptSegment (Entity)

**Identity**: `SegmentId` (composite: taskId + index)

**Lifecycle**: Created when transcript loaded, immutable after creation

```typescript
class TranscriptSegment {
  readonly id: SegmentId;
  readonly startTime: number;  // seconds
  readonly endTime: number;
  readonly text: string;
  readonly speaker?: string;
  readonly confidence: number;
  readonly index: number;  // Position in transcript

  constructor(
    id: SegmentId,
    startTime: number,
    endTime: number,
    text: string,
    options: {
      speaker?: string;
      confidence?: number;
      index?: number;
    } = {}
  ) {
    this.id = id;
    this.startTime = startTime;
    this.endTime = endTime;
    this.text = text;
    this.speaker = options.speaker;
    this.confidence = options.confidence ?? 1.0;
    this.index = options.index ?? 0;

    // Validate
    if (startTime >= endTime) {
      throw new Error("Start time must be before end time");
    }
    if (confidence < 0 || confidence > 1) {
      throw new Error("Confidence must be between 0 and 1");
    }
  }

  equals(other: TranscriptSegment): boolean {
    return this.id.equals(other.id);
  }

  // Behavior
  contains(timestamp: number): boolean {
    return timestamp >= this.startTime && timestamp <= this.endTime;
  }

  containsText(query: string, options: SearchOptions = {}): boolean {
    let text = this.text;
    let search = query;

    if (!options.caseSensitive) {
      text = text.toLowerCase();
      search = search.toLowerCase();
    }

    if (options.wholeWord) {
      const regex = new RegExp(`\\b${search}\\b`, options.caseSensitive ? "" : "i");
      return regex.test(text);
    }

    return text.includes(search);
  }

  getDuration(): number {
    return this.endTime - this.startTime;
  }

  // Export formats
  toSRT(): string {
    const startTime = this.formatSRTTime(this.startTime);
    const endTime = this.formatSRTTime(this.endTime);
    const speakerPrefix = this.speaker ? `${this.speaker}: ` : "";

    return `${this.index + 1}\n${startTime} --> ${endTime}\n${speakerPrefix}${this.text}\n\n`;
  }

  toVTT(): string {
    const startTime = this.formatVTTTime(this.startTime);
    const endTime = this.formatVTTTime(this.endTime);
    const speakerPrefix = this.speaker ? `<v.speaker.${this.speaker}>` : "";

    return `${this.index + 1}\n${startTime} --> ${endTime}\n${speakerPrefix}${this.text}\n\n`;
  }

  private formatSRTTime(seconds: number): string {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = Math.floor(seconds % 60);
    const ms = Math.floor((seconds % 1) * 1000);

    return `${String(hours).padStart(2, '0')}:${String(minutes).padStart(2, '0')}:${String(secs).padStart(2, '0')},${String(ms).padStart(3, '0')}`;
  }

  private formatVTTTime(seconds: number): string {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = Math.floor(seconds % 60);
    const ms = Math.floor((seconds % 1) * 1000);

    return `${String(hours).padStart(2, '0')}:${String(minutes).padStart(2, '0')}:${String(secs).padStart(2, '0')}.${String(ms).padStart(3, '0')}`;
  }
}
```

---

## 3. Value Objects

### 3.1 Percentage (Value Object)

**Purpose**: Represent progress percentage with validation

**Immutable**: Yes

```typescript
class Percentage {
  private readonly value: number;

  private constructor(value: number) {
    if (value < 0 || value > 100) {
      throw new Error("Percentage must be between 0 and 100");
    }
    this.value = Math.round(value * 100) / 100;  // 2 decimal places
  }

  static of(value: number): Percentage {
    return new Percentage(value);
  }

  static zero(): Percentage {
    return new Percentage(0);
  }

  static complete(): Percentage {
    return new Percentage(100);
  }

  // Value comparison
  equals(other: Percentage): boolean {
    return this.value === other.value;
  }

  isGreaterThan(other: Percentage): boolean {
    return this.value > other.value;
  }

  isLessThan(other: Percentage): boolean {
    return this.value < other.value;
  }

  // Queries
  get isComplete(): boolean {
    return this.value === 100;
  }

  get isZero(): boolean {
    return this.value === 0;
  }

  get isPartial(): boolean {
    return this.value > 0 && this.value < 100;
  }

  // Operations (return new instances)
  add(amount: number): Percentage {
    return new Percentage(this.value + amount);
  }

  difference(other: Percentage): number {
    return this.value - other.value;
  }

  // Formatting
  toString(): string {
    return `${this.value}%`;
  }

  toFixed(decimals: number): string {
    return `${this.value.toFixed(decimals)}%`;
  }

  toFraction(): number {
    return this.value / 100;
  }

  // For display
  toDisplay(): string {
    if (this.isComplete) return "Complete";
    if (this.isZero) return "Not started";
    return this.toString();
  }
}
```

### 3.2 Duration (Value Object)

**Purpose**: Represent time duration with human-readable formatting

**Immutable**: Yes

```typescript
class Duration {
  private readonly seconds: number;

  private constructor(seconds: number) {
    if (seconds < 0) {
      throw new Error("Duration cannot be negative");
    }
    this.seconds = seconds;
  }

  static ofSeconds(seconds: number): Duration {
    return new Duration(seconds);
  }

  static ofMinutes(minutes: number): Duration {
    return new Duration(minutes * 60);
  }

  static ofHours(hours: number): Duration {
    return new Duration(hours * 3600);
  }

  static zero(): Duration {
    return new Duration(0);
  }

  // Value comparison
  equals(other: Duration): boolean {
    return this.seconds === other.seconds;
  }

  isGreaterThan(other: Duration): boolean {
    return this.seconds > other.seconds;
  }

  isLessThan(other: Duration): boolean {
    return this.seconds < other.seconds;
  }

  // Components
  get inSeconds(): number {
    return this.seconds;
  }

  get inMinutes(): number {
    return this.seconds / 60;
  }

  get inHours(): number {
    return this.seconds / 3600;
  }

  // Time units
  get hours(): number {
    return Math.floor(this.seconds / 3600);
  }

  get minutes(): number {
    return Math.floor((this.seconds % 3600) / 60);
  }

  get remainingSeconds(): number {
    return Math.floor(this.seconds % 60);
  }

  // Operations
  add(other: Duration): Duration {
    return new Duration(this.seconds + other.seconds);
  }

  subtract(other: Duration): Duration {
    return new Duration(Math.max(0, this.seconds - other.seconds));
  }

  multiply(factor: number): Duration {
    return new Duration(this.seconds * factor);
  }

  divide(factor: number): Duration {
    return new Duration(this.seconds / factor);
  }

  // Formatting
  toHHMMSS(): string {
    const h = String(this.hours).padStart(2, '0');
    const m = String(this.minutes).padStart(2, '0');
    const s = String(this.remainingSeconds).padStart(2, '0');
    return `${h}:${m}:${s}`;
  }

  toHumanReadable(): string {
    if (this.seconds < 60) {
      return `${Math.round(this.seconds)} seconds`;
    } else if (this.seconds < 3600) {
      const mins = Math.round(this.inMinutes);
      return `${mins} ${mins === 1 ? 'minute' : 'minutes'}`;
    } else {
      const hrs = this.hours;
      const mins = this.minutes;
      if (mins === 0) {
        return `${hrs} ${hrs === 1 ? 'hour' : 'hours'}`;
      }
      return `${hrs}h ${mins}m`;
    }
  }

  toApproximate(): string {
    if (this.seconds < 60) {
      return "< 1 minute";
    } else if (this.seconds < 3600) {
      return `About ${Math.round(this.inMinutes)} minutes`;
    } else {
      const hrs = Math.round(this.inHours * 10) / 10;
      return `About ${hrs} ${hrs === 1 ? 'hour' : 'hours'}`;
    }
  }

  toString(): string {
    return this.toHHMMSS();
  }
}
```

### 3.3 Timestamp (Value Object)

**Purpose**: Represent a point in time with timezone awareness

**Immutable**: Yes

```typescript
class Timestamp {
  private readonly milliseconds: number;
  private readonly timezone: string;

  private constructor(milliseconds: number, timezone: string = "UTC") {
    this.milliseconds = milliseconds;
    this.timezone = timezone;
  }

  static now(): Timestamp {
    return new Timestamp(Date.now(), Intl.DateTimeFormat().resolvedOptions().timeZone);
  }

  static fromISO(isoString: string): Timestamp {
    const ms = Date.parse(isoString);
    if (isNaN(ms)) {
      throw new Error("Invalid ISO timestamp");
    }
    return new Timestamp(ms, "UTC");
  }

  static fromDate(date: Date): Timestamp {
    return new Timestamp(date.getTime(), "UTC");
  }

  static fromMilliseconds(ms: number): Timestamp {
    return new Timestamp(ms, "UTC");
  }

  // Value comparison
  equals(other: Timestamp): boolean {
    return this.milliseconds === other.milliseconds;
  }

  isBefore(other: Timestamp): boolean {
    return this.milliseconds < other.milliseconds;
  }

  isAfter(other: Timestamp): boolean {
    return this.milliseconds > other.milliseconds;
  }

  // Difference
  difference(other: Timestamp): Duration {
    const seconds = Math.abs(this.milliseconds - other.milliseconds) / 1000;
    return Duration.ofSeconds(seconds);
  }

  timeSince(other: Timestamp): Duration {
    return Duration.ofSeconds((this.milliseconds - other.milliseconds) / 1000);
  }

  timeUntil(other: Timestamp): Duration {
    return Duration.ofSeconds((other.milliseconds - this.milliseconds) / 1000);
  }

  // Operations (return new instances)
  add(duration: Duration): Timestamp {
    return new Timestamp(this.milliseconds + duration.inSeconds * 1000, this.timezone);
  }

  subtract(duration: Duration): Timestamp {
    return new Timestamp(this.milliseconds - duration.inSeconds * 1000, this.timezone);
  }

  // Formatting
  toISO(): string {
    return new Date(this.milliseconds).toISOString();
  }

  toLocaleString(locale?: string): string {
    return new Date(this.milliseconds).toLocaleString(locale);
  }

  toRelative(): string {
    const now = Timestamp.now();
    const diff = now.timeSince(this);

    if (diff.inSeconds < 60) {
      return "just now";
    } else if (diff.inSeconds < 3600) {
      return `${Math.floor(diff.inMinutes)} minutes ago`;
    } else if (diff.inSeconds < 86400) {
      return `${Math.floor(diff.inHours)} hours ago`;
    } else {
      return `${Math.floor(diff.inHours / 24)} days ago`;
    }
  }

  toString(): string {
    return this.toISO();
  }
}
```

### 3.4 FileMetadata (Value Object)

**Purpose**: Immutable file information

**Immutable**: Yes

```typescript
class FileMetadata {
  readonly name: string;
  readonly size: number;  // bytes
  readonly type: string;  // MIME type
  readonly lastModified: Date;

  private constructor(
    name: string,
    size: number,
    type: string,
    lastModified: Date
  ) {
    if (size < 0) {
      throw new Error("File size cannot be negative");
    }
    if (!name || name.trim().length === 0) {
      throw new Error("File name is required");
    }
    this.name = name;
    this.size = size;
    this.type = type;
    this.lastModified = lastModified;
  }

  static fromFile(file: File): FileMetadata {
    return new FileMetadata(
      file.name,
      file.size,
      file.type,
      new Date(file.lastModified)
    );
  }

  static fromObject(obj: {
    name: string;
    size: number;
    type: string;
    lastModified: string | Date;
  }): FileMetadata {
    return new FileMetadata(
      obj.name,
      obj.size,
      obj.type,
      new Date(obj.lastModified)
    );
  }

  // Value comparison
  equals(other: FileMetadata): boolean {
    return this.name === other.name &&
           this.size === other.size &&
           this.type === other.type &&
           this.lastModified.getTime() === other.lastModified.getTime();
  }

  // Queries
  get sizeInKB(): number {
    return this.size / 1024;
  }

  get sizeInMB(): number {
    return this.size / (1024 * 1024);
  }

  get sizeInGB(): number {
    return this.size / (1024 * 1024 * 1024);
  }

  get extension(): string {
    const parts = this.name.split('.');
    return parts.length > 1 ? parts[parts.length - 1].toLowerCase() : '';
  }

  // Validation
  isValidFormat(supportedFormats: string[]): boolean {
    return supportedFormats.some(format => {
      if (format.startsWith('.')) {
        return this.extension === format.substring(1);
      }
      return this.type === format;
    });
  }

  isTooLarge(maxSize: number): boolean {
    return this.size > maxSize;
  }

  isEmpty(): boolean {
    return this.size === 0;
  }

  // Formatting
  get formattedSize(): string {
    if (this.sizeInGB >= 1) {
      return `${this.sizeInGB.toFixed(2)} GB`;
    } else if (this.sizeInMB >= 1) {
      return `${this.sizeInMB.toFixed(2)} MB`;
    } else if (this.sizeInKB >= 1) {
      return `${this.sizeInKB.toFixed(2)} KB`;
    } else {
      return `${this.size} bytes`;
    }
  }

  get formattedType(): string {
    const typeMap: Record<string, string> = {
      "audio/mpeg": "MP3",
      "audio/wav": "WAV",
      "audio/mp4": "M4A",
      "audio/x-m4a": "M4A",
      "video/mp4": "MP4",
      "video/webm": "WEBM"
    };

    return typeMap[this.type] || this.type.toUpperCase();
  }
}
```

### 3.5 Stage (Value Object)

**Purpose**: Represent a stage in the transcription pipeline

**Immutable**: Yes

```typescript
class Stage {
  private readonly name: StageName;
  private readonly status: StageStatus;
  private readonly startedAt?: Timestamp;
  private readonly completedAt?: Timestamp;
  private readonly progress: Percentage;

  private constructor(
    name: StageName,
    status: StageStatus,
    progress: Percentage,
    startedAt?: Timestamp,
    completedAt?: Timestamp
  ) {
    this.name = name;
    this.status = status;
    this.progress = progress;
    this.startedAt = startedAt;
    this.completedAt = completedAt;
  }

  // Factory methods
  static pending(name: StageName): Stage {
    return new Stage(name, StageStatus.PENDING, Percentage.zero());
  }

  static start(name: StageName): Stage {
    return new Stage(name, StageStatus.IN_PROGRESS, Percentage.zero(), Timestamp.now());
  }

  static complete(name: StageName): Stage {
    return new Stage(
      name,
      StageStatus.COMPLETED,
      Percentage.complete(),
      Timestamp.now(),
      Timestamp.now()
    );
  }

  static fail(name: StageName): Stage {
    return new Stage(name, StageStatus.FAILED, Percentage.zero(), Timestamp.now());
  }

  // Value comparison
  equals(other: Stage): boolean {
    return this.name === other.name &&
           this.status === other.status &&
           this.progress.equals(other.progress);
  }

  // Queries
  isPending(): boolean {
    return this.status === StageStatus.PENDING;
  }

  isInProgress(): boolean {
    return this.status === StageStatus.IN_PROGRESS;
  }

  isComplete(): boolean {
    return this.status === StageStatus.COMPLETED;
  }

  isFailed(): boolean {
    return this.status === StageStatus.FAILED;
  }

  isTerminal(): boolean {
    return this.isComplete() || this.isFailed();
  }

  // Time-based queries
  getDuration(): Duration | null {
    if (!this.startedAt) return null;
    const end = this.completedAt || Timestamp.now();
    return this.startedAt.difference(end);
  }

  getTimeSinceStart(): Duration | null {
    if (!this.startedAt) return null;
    return this.startedAt.timeSince(Timestamp.now());
  }

  // Display
  get label(): string {
    const labels: Record<StageName, string> = {
      UPLOADING: "Uploading",
      VALIDATING: "Validating",
      QUEUED: "Queued",
      PROCESSING: "Processing",
      TRANSCRIBING: "Transcribing",
      FINALIZING: "Finalizing",
      COMPLETED: "Completed",
      FAILED: "Failed"
    };
    return labels[this.name];
  }

  get icon(): string {
    const icons: Record<StageName, string> = {
      UPLOADING: "upload",
      VALIDATING: "check-circle",
      QUEUED: "clock",
      PROCESSING: "settings",
      TRANSCRIBING: "audio",
      FINALIZING: "file-text",
      COMPLETED: "check",
      FAILED: "alert-circle"
    };
    return icons[this.name];
  }
}

enum StageName {
  UPLOADING = "UPLOADING",
  VALIDATING = "VALIDATING",
  QUEUED = "QUEUED",
  PROCESSING = "PROCESSING",
  TRANSCRIBING = "TRANSCRIBING",
  FINALIZING = "FINALIZING",
  COMPLETED = "COMPLETED",
  FAILED = "FAILED"
}

enum StageStatus {
  PENDING = "PENDING",
  IN_PROGRESS = "IN_PROGRESS",
  COMPLETED = "COMPLETED",
  FAILED = "FAILED"
}
```

### 3.6 TimeEstimate (Value Object)

**Purpose**: Calculate and store time estimates

**Immutable**: Yes

```typescript
class TimeEstimate {
  private readonly totalSeconds: number;
  private readonly confidence: number;  // 0-1
  private readonly algorithm: EstimationAlgorithm;
  private readonly calculatedAt: Timestamp;

  private constructor(
    totalSeconds: number,
    confidence: number,
    algorithm: EstimationAlgorithm,
    calculatedAt: Timestamp
  ) {
    if (totalSeconds < 0) {
      throw new Error("Time estimate cannot be negative");
    }
    if (confidence < 0 || confidence > 1) {
      throw new Error("Confidence must be between 0 and 1");
    }
    this.totalSeconds = totalSeconds;
    this.confidence = confidence;
    this.algorithm = algorithm;
    this.calculatedAt = calculatedAt;
  }

  static fromData(data: ProgressData): TimeEstimate {
    const algorithm = new EstimationAlgorithm();
    const result = algorithm.calculate(data);

    return new TimeEstimate(
      result.seconds,
      result.confidence,
      algorithm,
      Timestamp.now()
    );
  }

  static unknown(): TimeEstimate {
    return new TimeEstimate(0, 0, EstimationAlgorithm.UNKNOWN, Timestamp.now());
  }

  // Value comparison
  equals(other: TimeEstimate): boolean {
    return this.totalSeconds === other.totalSeconds &&
           this.confidence === other.confidence;
  }

  // Queries
  get remaining(): Duration {
    return Duration.ofSeconds(this.totalSeconds);
  }

  get isReliable(): boolean {
    return this.confidence >= 0.7;
  }

  get isUnknown(): boolean {
    return this.totalSeconds === 0;
  }

  get age(): Duration {
    return this.calculatedAt.timeSince(Timestamp.now());
  }

  // Display
  toDisplay(): string {
    if (this.isUnknown) {
      return "Calculating...";
    }

    if (!this.isReliable) {
      return "Estimating...";
    }

    return this.remaining.toApproximate();
  }

  toDetailedDisplay(): string {
    if (this.isUnknown) {
      return "Time estimate unknown";
    }

    const timeStr = this.remaining.toHumanReadable();
    const confidence = Math.round(this.confidence * 100);

    return `${timeStr} (${confidence}% confidence)`;
  }
}

enum EstimationAlgorithm {
  LINEAR = "LINEAR",
  HISTORICAL = "HISTORICAL",
  ML = "ML",
  UNKNOWN = "UNKNOWN"
}

interface ProgressData {
  elapsed: Duration;
  currentProgress: Percentage;
  stage?: Stage;
  historicalData?: HistoricalTaskData[];
}

interface HistoricalTaskData {
  fileSize: number;
  duration: Duration;
  fileType: string;
}

class EstimationAlgorithm {
  calculate(data: ProgressData): { seconds: number; confidence: number } {
    if (data.currentProgress.isZero || data.elapsed.inSeconds < 5) {
      return { seconds: 0, confidence: 0 };
    }

    // Linear extrapolation
    const rate = data.currentProgress.toFraction() / data.elapsed.inSeconds;
    const remainingFraction = 1 - data.currentProgress.toFraction();
    const estimateSeconds = remainingFraction / rate;

    // Confidence based on progress and time elapsed
    let confidence = Math.min(data.currentProgress.toFraction() * 2, 1);
    confidence = Math.min(confidence, data.elapsed.inSeconds / 60);

    return {
      seconds: Math.round(estimateSeconds),
      confidence: Math.round(confidence * 100) / 100
    };
  }
}
```

---

## 4. Value Object Patterns

### 4.1 Validation Pattern

```typescript
// Value objects validate themselves on construction
class EmailAddress {
  private readonly value: string;

  private constructor(value: string) {
    if (!this.isValid(value)) {
      throw new Error("Invalid email address");
    }
    this.value = value;
  }

  private isValid(email: string): boolean {
    return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
  }

  static of(value: string): EmailAddress {
    return new EmailAddress(value);
  }
}
```

### 4.2 Immutability Pattern

```typescript
// All operations return new instances
class Money {
  readonly amount: number;
  readonly currency: string;

  constructor(amount: number, currency: string) {
    this.amount = amount;
    this.currency = currency;
  }

  add(other: Money): Money {
    if (other.currency !== this.currency) {
      throw new Error("Currency mismatch");
    }
    return new Money(this.amount + other.amount, this.currency);
  }

  // No setters - never modify after creation
}
```

### 4.3 Self-Contained Behavior

```typescript
// Value objects contain their own behavior
class Distance {
  readonly meters: number;

  private constructor(meters: number) {
    this.meters = meters;
  }

  static ofKilometers(km: number): Distance {
    return new Distance(km * 1000);
  }

  static ofMiles(miles: number): Distance {
    return new Distance(miles * 1609.344);
  }

  toKilometers(): number {
    return this.meters / 1000;
  }

  toMiles(): number {
    return this.meters / 1609.344;
  }

  format(unit: 'm' | 'km' | 'miles'): string {
    switch (unit) {
      case 'm': return `${this.meters} m`;
      case 'km': return `${this.toKilometers().toFixed(2)} km`;
      case 'miles': return `${this.toMiles().toFixed(2)} miles`;
    }
  }
}
```

---

*End of Entities and Value Objects Documentation*
