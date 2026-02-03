# Bounded Contexts
## Feature 1: UI/UX Improvements - Strategic Domain-Driven Design

| Version | Date | Author | Status |
|---------|------|--------|--------|
| 1.0 | 2025-02-03 | System Architect | Draft |

---

## 1. Bounded Context Definitions

### 1.1 Progress Tracking Context

**Purpose**: Track and visualize the progress of long-running transcription tasks.

**Core Domain**: This is a **Core Domain** as it directly impacts user experience and is a key differentiator.

**Responsibilities**:
- Track transcription progress through multiple stages
- Calculate and display time estimates
- Manage progress state across page refreshes
- Handle progress updates from backend via WebSocket
- Provide progress visualization components

**Ubiquitous Language**:
| Term | Definition |
|------|------------|
| Progress | The current state of a transcription task (0-100%) |
| Stage | A phase of transcription (Upload, Processing, Transcribing, Finalizing) |
| Progress Tracker | The entity that manages progress state |
| Progress Update | An event indicating progress has changed |
| Time Estimate | Calculated completion time based on progress rate |

**Core Subdomains**:
1. **Progress Tracking** - Track percentage, stage, time
2. **Estimation** - Calculate ETA based on historical data
3. **Persistence** - Save/restore progress state
4. **Visualization** - Render progress components

---

### 1.2 Notification Context

**Purpose**: Deliver timely, non-intrusive notifications to users about transcription events.

**Core Domain**: This is a **Supporting Subdomain** (Generic) as notification systems are well-solved problems.

**Responsibilities**:
- Request and manage notification permissions
- Display browser notifications
- Display in-app toast notifications
- Manage notification history
- Handle notification preferences

**Ubiquitous Language**:
| Term | Definition |
|------|------------|
| Notification | A message delivered to the user about an event |
| Notification Channel | The delivery mechanism (browser, in-app, sound) |
| Notification Manager | Entity managing notification delivery |
| Notification Preference | User's notification settings |
| Toast | Temporary in-app notification |

**Core Subdomains**:
1. **Permission Management** - Request and store permissions
2. **Delivery** - Send notifications via channels
3. **History** - Maintain notification log
4. **Preferences** - User notification settings

---

### 1.3 File Upload Context

**Purpose**: Handle file selection, validation, and upload with user-friendly feedback.

**Core Domain**: This is a **Generic Subdomain** as file upload is a common web pattern.

**Responsibilities**:
- Handle drag-and-drop file selection
- Validate file formats and sizes
- Show file previews
- Manage upload queue
- Display upload progress

**Ubiquitous Language**:
| Term | Definition |
|------|------------|
| Upload | The act of transferring a file from client to server |
| File Validation | Checking if a file meets requirements |
| Upload Queue | Ordered list of files to upload |
| Drag Zone | UI area accepting dropped files |
| Upload Manager | Entity coordinating upload process |

**Core Subdomains**:
1. **File Selection** - Drag-drop, file picker
2. **Validation** - Format, size checks
3. **Upload Coordination** - Queue management
4. **Progress Reporting** - Upload status

---

### 1.4 Transcript Display Context

**Purpose**: Present transcribed content with enhanced navigation and export capabilities.

**Core Domain**: This is a **Core Domain** as it's the primary value delivery to users.

**Responsibilities**:
- Display formatted transcript with timestamps
- Enable timestamp navigation
- Support search within transcript
- Handle speaker label display
- Provide export functionality

**Ubiquitous Language**:
| Term | Definition |
|------|------------|
| Transcript | The transcribed text from audio/video |
| Timestamp | Time marker in transcript (HH:MM:SS) |
| Speaker Label | Identifier for different speakers |
| Transcript Segment | A portion of transcript with metadata |
| Export | Saving transcript in different formats |

---

### 1.5 Error Handling Context

**Purpose**: Provide clear, actionable error messages and recovery options.

**Core Domain**: This is a **Supporting Subdomain**.

**Responsibilities**:
- Display error messages clearly
- Provide recovery suggestions
- Enable retry functionality
- Log errors for support
- Offer graceful degradation

**Ubiquitous Language**:
| Term | Definition |
|------|------------|
| Error State | A failure condition requiring user attention |
| Recovery Action | User action to resolve error |
| Error Message | Human-readable error explanation |
| Retry | Attempting the failed operation again |
| Graceful Degradation | Functioning with reduced capability |

---

### 1.6 Theme Context

**Purpose**: Manage visual appearance including light/dark mode and customization.

**Core Domain**: This is a **Generic Subdomain**.

**Responsibilities**:
- Toggle between light/dark themes
- Detect system theme preference
- Persist theme choice
- Support high contrast mode
- Allow custom accent colors

**Ubiquitous Language**:
| Term | Definition |
|------|------------|
| Theme | Visual appearance scheme (light/dark) |
| System Preference | OS-level theme setting |
| Accent Color | User-defined primary color |
| Theme Manager | Entity managing theme state |
| High Contrast | Accessibility-focused color scheme |

---

### 1.7 Accessibility Context

**Purpose**: Ensure the application is usable by people with disabilities.

**Core Domain**: This is a **Generic Subdomain** but with critical importance.

**Responsibilities**:
- Provide ARIA labels and roles
- Support keyboard navigation
- Maintain focus management
- Ensure color contrast compliance
- Support screen readers

**Ubiquitous Language**:
| Term | Definition |
|------|------------|
| Accessibility | Usability for people with disabilities |
| ARIA | Accessible Rich Internet Applications attributes |
| Focus Indicator | Visual cue showing focused element |
| Keyboard Navigation | Using keyboard without mouse |
| Screen Reader | Assistive technology for visually impaired |

---

## 2. Context Map

### 2.1 Context Relationship Map

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         STT Application Context Map                         │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌──────────────────┐                                                      │
│  │   Upstream       │                                                      │
│  │  (Transcription  │───┐                                                  │
│  │   Backend API)   │   │                                                  │
│  └──────────────────┘   │                                                  │
│                        │                                                   │
│                        ▼                                                   │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    UI/UX Improvement Layer                          │   │
│  ├─────────────────────────────────────────────────────────────────────┤   │
│  │                                                                     │   │
│  │  ┌──────────────────┐    ┌──────────────────┐                      │   │
│  │  │   Progress       │    │   Notification    │                      │   │
│  │  │   Tracking       │◄──►│   Context        │                      │   │
│  │  │   Context        │    │                  │                      │   │
│  │  │  (CORE DOMAIN)   │    │ (SUPPORTING)     │                      │   │
│  │  └──────────────────┘    └──────────────────┘                      │   │
│  │         │                         │                                │   │
│  │         │                         │                                │   │
│  │         ▼                         ▼                                │   │
│  │  ┌───────────────────────────────────────────────────────────┐    │   │
│  │  │              Shared Kernel (Event Bus)                    │    │   │
│  │  │     • ProgressUpdate     • NotificationEvent              │    │   │
│  │  │     • StageChangeEvent   • ErrorEvent                     │    │   │
│  │  │     • CompletionEvent    • ThemeChangeEvent               │    │   │
│  │  └───────────────────────────────────────────────────────────┘    │   │
│  │         │                         │                                │   │
│  │         ▼                         ▼                                │   │
│  │  ┌──────────────────┐    ┌──────────────────┐                      │   │
│  │  │   File Upload    │    │   Transcript     │                      │   │
│  │  │   Context        │    │   Display        │                      │   │
│  │  │   (GENERIC)      │    │   (CORE)         │                      │   │
│  │  └──────────────────┘    └──────────────────┘                      │   │
│  │                                                                     │   │
│  │  ┌──────────────────┐    ┌──────────────────┐                      │   │
│  │  │   Error          │    │   Theme          │                      │   │
│  │  │   Handling       │    │   Context        │                      │   │
│  │  │   (SUPPORTING)   │    │   (GENERIC)      │                      │   │
│  │  └──────────────────┘    └──────────────────┘                      │   │
│  │                                                                     │   │
│  │  ┌──────────────────┐                                              │   │
│  │  │   Accessibility  │                                              │   │
│  │  │   Context        │───►(All Contexts)                            │   │
│  │  │   (GENERIC*)     │     (Cross-cutting concern)                  │   │
│  │  └──────────────────┘                                              │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘

Relationship Types:
━━━━  Partnership (bidirectional, frequent communication)
─────  Upstream (provides data/services)
....  Anticorruption Layer (protects from external systems)
```

### 2.2 Context Relationships

| Context A | Context B | Relationship Type | Description |
|-----------|-----------|-------------------|-------------|
| Progress Tracking | Notification | Partnership | Progress triggers completion notifications |
| Progress Tracking | Transcript Display | Upstream/Downstream | Progress leads to transcript availability |
| File Upload | Progress Tracking | Upstream/Downstream | Upload initiates progress tracking |
| Error Handling | All Contexts | Partnership | Errors can occur anywhere |
| Theme | All Contexts | Partnership | Theme affects all UI components |
| Accessibility | All Contexts | Cross-cutting | Applies to all UI elements |

### 2.3 Integration Patterns

| Pattern | Contexts | Description |
|---------|----------|-------------|
| **Domain Events** | Progress → Notification | Progress completion triggers notification |
| **Shared Kernel** | All contexts | Common event types, state interfaces |
| **ACL (Anticorruption Layer)** | Backend API → All | Adapts backend responses to domain models |
| **Aggregator** | Transcript Display | Combines transcript + progress + errors |

---

## 3. Ubiquitous Language (Cross-Context)

### 3.1 Core Terms

| Term | Definition | Used In Contexts |
|------|------------|------------------|
| **Task** | A transcription job for a single file | All |
| **Progress** | Current completion state (0-100%) | Progress, Upload |
| **Stage** | Phase of task execution | Progress, Upload |
| **Notification** | User-visible message | Notification, Error |
| **Theme** | Visual appearance scheme | Theme, All UI |
| **Error** | Failure state | Error, All |
| **User** | Person using the application | All |
| **Session** | User's active browser session | Progress, Theme |

### 3.2 Action Terms

| Term | Definition |
|------|------------|
| **Upload** | Transfer file from client to server |
| **Transcribe** | Convert audio/video to text |
| **Notify** | Send message to user |
| **Progress** | Move forward in completion |
| **Complete** | Finish successfully |
| **Fail** | Finish unsuccessfully |
| **Retry** | Attempt again after failure |
| **Cancel** | Stop before completion |

### 3.3 State Terms

| Term | Definition |
|------|------------|
| **Pending** | Not started yet |
| **In Progress** | Currently executing |
| **Completed** | Finished successfully |
| **Failed** | Finished with error |
| **Cancelled** | Stopped by user |
| **Paused** | Temporarily stopped |

---

## 4. Domain Events

### 4.1 Progress Context Events

| Event | Payload | Consumers | Description |
|-------|---------|-----------|-------------|
| `ProgressUpdated` | `{ taskId, percentage, stage, speed }` | Progress UI, Notification | Progress percentage changed |
| `StageChanged` | `{ taskId, fromStage, toStage }` | Progress UI, Notification | Task entered new stage |
| `ProgressStarted` | `{ taskId, fileName, estimatedDuration }` | Progress UI, Notification | Task began processing |
| `ProgressCompleted` | `{ taskId, duration, resultUrl }` | Notification, Transcript Display | Task finished successfully |
| `ProgressFailed` | `{ taskId, error, retryable }` | Error, Notification, Progress UI | Task failed |
| `TimeEstimateUpdated` | `{ taskId, estimatedTimeRemaining }` | Progress UI | Time estimate recalculated |

### 4.2 Notification Context Events

| Event | Payload | Consumers | Description |
|-------|---------|-----------|-------------|
| `NotificationRequested` | `{ type, message, actions }` | Notification Manager | Request to send notification |
| `NotificationPermissionGranted` | `{ }` | Notification Manager | User allowed notifications |
| `NotificationPermissionDenied` | `{ }` | Notification Manager | User blocked notifications |
| `NotificationClicked` | `{ notificationId, action }` | App Router | User clicked notification |
| `NotificationDismissed` | `{ notificationId }` | Notification Manager | User closed notification |

### 4.3 File Upload Context Events

| Event | Payload | Consumers | Description |
|-------|---------|-----------|-------------|
| `FileSelected` | `{ file, name, size, type }` | Upload Manager, Validation | User chose file |
| `FileDropped` | `{ files[] }` | Upload Manager, Validation | User dropped files |
| `FileValidated` | `{ file, valid, errors[] }` | Upload UI | Validation completed |
| `UploadStarted` | `{ taskId, file, uploadId }` | Progress, Upload UI | Upload began |
| `UploadProgress` | `{ uploadId, loaded, total }` | Upload UI, Progress | Upload chunk completed |
| `UploadCompleted` | `{ uploadId, taskId }` | Progress, Upload UI | Upload finished |

### 4.4 Transcript Display Context Events

| Event | Payload | Consumers | Description |
|-------|---------|-----------|-------------|
| `TranscriptLoaded` | `{ taskId, transcript }` | Transcript UI, Search | Transcript data available |
| `TimestampClicked` | `{ taskId, timestamp }` | Audio Player, Transcript UI | User clicked timestamp |
| `SearchRequested` | `{ taskId, query }` | Transcript UI, Search | User searched transcript |
| `ExportRequested` | `{ taskId, format }` | Export Service | User requested export |
| `SpeakerLabelToggled` | `{ taskId, showLabels }` | Transcript UI | User toggled speaker display |

### 4.5 Error Handling Context Events

| Event | Payload | Consumers | Description |
|-------|---------|-----------|-------------|
| `ErrorOccurred` | `{ taskId, error, context }` | Error UI, Notification, Logging | Error happened |
| `RetryRequested` | `{ taskId, retryContext }` | All Contexts | User requested retry |
| `ErrorResolved` | `{ taskId, resolution }` | Error UI, Progress | Error was fixed |
| `ErrorReported` | `{ taskId, errorDetails }` | Support System | User reported issue |

### 4.6 Theme Context Events

| Event | Payload | Consumers | Description |
|-------|---------|-----------|-------------|
| `ThemeChanged` | `{ theme }` | All UI Components | Theme mode changed |
| `AccentColorChanged` | `{ color }` | All UI Components | Accent color changed |
| `SystemThemeDetected` | `{ systemTheme }` | Theme Manager | Detected OS preference |
| `HighContrastToggled` | `{ enabled }` | All UI Components | High contrast mode changed |

---

## 5. Context Responsibilities Summary

| Context | Primary Responsibility | Key Entities | External Dependencies |
|---------|----------------------|--------------|----------------------|
| **Progress Tracking** | Track and visualize task progress | ProgressTracker, Stage, TimeEstimate | Backend WebSocket API |
| **Notification** | Deliver messages to users | Notification, NotificationPreference, NotificationHistory | Browser Notification API |
| **File Upload** | Handle file selection and upload | UploadManager, FileValidation, UploadQueue | Backend Upload API |
| **Transcript Display** | Present transcribed content | Transcript, TranscriptSegment, Timestamp | Backend Transcript API |
| **Error Handling** | Display errors and recovery options | ErrorState, RecoveryAction | All contexts |
| **Theme** | Manage visual appearance | Theme, ThemePreference | Browser MatchMedia API |
| **Accessibility** | Ensure accessibility compliance | AccessibilityManager | WCAG guidelines |

---

## 6. Strategic Pattern Decisions

### 6.1 Core Domain Investments

**Progress Tracking Context** - Invest heavily here:
- Rich time estimation algorithms
- Smooth, performant animations
- Cross-session persistence
- Robust WebSocket handling

**Transcript Display Context** - Invest heavily here:
- Advanced search capabilities
- Smooth timestamp seeking
- Multiple export formats
- Speaker diarization visualization

### 6.2 Generic Subdomain Strategies

**Notification Context** - Use off-the-shelf solution:
- React Hot Toast or similar library
- Minimal custom logic
- Focus on integration

**Theme Context** - Use established patterns:
- CSS variables with React context
- Industry-standard dark mode implementation
- Follow Material Design or similar guidelines

**File Upload Context** - Use proven libraries:
- React Dropzone for drag-drop
- Axios for upload with progress
- Follow established patterns

### 6.3 Cross-Cutting Concerns

| Concern | Strategy | Implementation |
|---------|----------|----------------|
| **Accessibility** | Apply everywhere | ARIA attributes, keyboard support, color contrast |
| **Error Handling** | Centralized error boundary | React Error Boundary + error context |
| **Logging** | Centralized logging service | Send errors to backend + console |
| **Performance** | Code splitting, lazy loading | React.lazy, Suspense |
| **Internationalization** | Prepare for future i18n | Externalize all strings |

---

## 7. Context Evolution Roadmap

### Phase 1: Foundation
- Implement Progress Tracking Context (core value)
- Implement Notification Context (essential for UX)
- Basic Error Handling Context

### Phase 2: Enhancement
- Enhanced Transcript Display Context
- File Upload Context improvements
- Theme Context implementation

### Phase 3: Polish
- Accessibility Context improvements
- Advanced features (offline mode, PWA)
- Performance optimization across contexts

---

## 8. Anti-Corruption Layers

### 8.1 Backend API ACL

**Problem**: Backend API responses don't match our domain models.

**Solution**: Implement ACL to transform backend data.

```typescript
// Backend response format
interface BackendProgressResponse {
  status: string;
  pct: number;
  current_step: string;
}

// Domain model
interface ProgressState {
  stage: Stage;
  percentage: Percentage;
  isComplete: boolean;
}

// ACL transformation
function toProgressState(
  backend: BackendProgressResponse
): ProgressState {
  return {
    stage: mapBackendStageToDomainStage(backend.current_step),
    percentage: Percentage.of(backend.pct),
    isComplete: backend.status === 'complete'
  };
}
```

### 8.2 Browser API ACL

**Problem**: Browser Notification API is inconsistent across browsers.

**Solution**: Implement compatibility layer.

```typescript
class NotificationACL {
  requestPermission(): Promise<NotificationPermission> {
    // Handle browser inconsistencies
    if (!this.isSupported()) {
      return NotificationPermission.DENIED;
    }
    // Normalize permission values
    return Notification.requestPermission().then(
      p => this.normalizePermission(p)
    );
  }
}
```

---

## 9. Organizational Alignment

### 9.1 Team Structure (Conway's Law)

| Team | Responsible Contexts | Skills Required |
|------|---------------------|-----------------|
| **Core Experience Team** | Progress Tracking, Transcript Display | React, UX, WebSocket |
| **Platform Team** | Theme, Accessibility | CSS, A11y, Design Systems |
| **Infrastructure Team** | Backend integration, Error Handling | API, DevOps, Monitoring |

### 9.2 Communication Protocols

| Context Pair | Communication Frequency | Primary Protocol |
|--------------|------------------------|------------------|
| Progress ↔ Notification | High (async events) | Domain Events |
| Progress ↔ Transcript | Medium (state sync) | Direct calls |
| All ↔ Error | Low (exceptional) | Error Events |
| All ↔ Theme | Low (configuration) | Context API |

---

*End of Bounded Contexts Documentation*
