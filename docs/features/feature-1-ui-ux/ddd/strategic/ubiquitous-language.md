# Ubiquitous Language
## Feature 1: UI/UX Improvements - Domain-Driven Design

| Version | Date | Author | Status |
|---------|------|--------|--------|
| 1.0 | 2025-02-03 | System Architect | Draft |

---

## 1. Language Philosophy

The Ubiquitous Language is the shared vocabulary used by both domain experts (product managers, UX designers, users) and technical experts (developers, architects) to discuss the STT application's UI/UX improvements.

**Principles**:
1. **User-Centric**: Language reflects how users think about the system
2. **Precise**: Each term has a single, clear definition
3. **Ubiquitous**: Used consistently across code, documentation, and conversations
4. **Evolving**: Language grows and refines as understanding deepens

---

## 2. Core Concepts (The Language of Progress)

### 2.1 Task Concepts

| Term | Definition | Examples | Anti-patterns |
|------|------------|----------|---------------|
| **Task** | A single unit of work representing a transcription request for one file | "Transcribe meeting.mp3" | "Job", "Work item", "Process" |
| **Task ID** | Unique identifier for a task, used for tracking across systems | "task_abc123" | "UUID", "PK", "Record ID" |
| **Task Lifecycle** | The complete journey of a task from creation to completion or failure | Pending → In Progress → Complete | "State machine", "Status flow" |

### 2.2 Progress Concepts

| Term | Definition | Examples | Anti-patterns |
|------|------------|----------|---------------|
| **Progress** | The degree of completion of a task, expressed as a percentage | "75% complete" | "Percentage done", "Completion" |
| **Progress State** | The current status of progress tracking (active, paused, completed, failed) | "Active", "Paused" | "Status", "State" |
| **Percentage** | A value from 0-100 representing completion | Percentage.of(45) | "Percent", "Pct", "Ratio" |
| **Progress Bar** | Visual component displaying progress as a filled bar | The horizontal bar that fills up | "Loader", "Spinner", "Indicator" |

### 2.3 Stage Concepts

| Term | Definition | Examples | Anti-patterns |
|------|------------|----------|---------------|
| **Stage** | A distinct phase of task execution with specific characteristics | "Upload", "Processing", "Transcribing" | "Step", "Phase", "Level" |
| **Current Stage** | The stage currently being executed | "Currently in Transcribing stage" | "Active step", "Running phase" |
| **Stage Progress** | Progress within the current stage (0-100%) | "Upload stage: 60% complete" | "Step progress", "Phase completion" |
| **Stage Transition** | Moving from one stage to the next | "Transitioning from Upload to Processing" | "Step change", "Phase switch" |

**Valid Stages**:
```typescript
enum Stage {
  UPLOADING = "uploading",        // File being uploaded to server
  VALIDATING = "validating",      // File format/size validation
  QUEUED = "queued",              // Waiting in processing queue
  PROCESSING = "processing",      // Audio preprocessing (normalization, etc.)
  TRANSCRIBING = "transcribing",  // Converting speech to text
  FINALIZING = "finalizing",      // Post-processing, formatting
  COMPLETED = "completed",        // Successfully finished
  FAILED = "failed"               // Ended with error
}
```

### 2.4 Time Concepts

| Term | Definition | Examples | Anti-patterns |
|------|------------|----------|---------------|
| **Time Estimate** | Calculated prediction of remaining time | "About 15 minutes remaining" | "ETA", "Time left" |
| **Time Elapsed** | Actual time passed since task start | "12:34 have passed" | "Duration", "Time spent" |
| **Time Remaining** | Predicted time until completion | "8:26 remaining" | "ETA", "Time to go" |
| **Update Interval** | Frequency of progress updates | "Every 1% change" | "Refresh rate", "Tick rate" |

---

## 3. The Language of Notification

### 3.1 Notification Concepts

| Term | Definition | Examples | Anti-patterns |
|------|------------|----------|---------------|
| **Notification** | A message delivered to the user about a significant event | "Transcription complete" | "Alert", "Message", "Toast" |
| **Notification Channel** | The mechanism used to deliver a notification | Browser, In-app, Sound | "Delivery method", "Channel type" |
| **Notification Permission** | User's consent to receive browser notifications | Granted, Denied, Default | "Browser permission", "Notification access" |
| **Toast** | Temporary, non-blocking in-app notification | Floating notification at bottom-right | "Popup", "Inline message" |
| **Notification Action** | Button or link in notification for user response | "View Transcript", "Dismiss" | "Action button", "Link" |

### 3.2 Notification States

| State | Definition | User Behavior |
|-------|------------|---------------|
| **Requested** | Notification has been requested but not yet sent | Waiting for permission or delivery |
| **Sent** | Notification has been delivered to the user | User can see it |
| **Clicked** | User clicked on the notification | User navigated to content |
| **Dismissed** | User closed the notification | User chose to ignore |
| **Expired** | Notification auto-dismissed after timeout | Time-based dismissal |

---

## 4. The Language of File Upload

### 4.1 Upload Concepts

| Term | Definition | Examples | Anti-patterns |
|------|------------|----------|---------------|
| **Upload** | Act of transferring a file from client to server | "Upload meeting.mp3" | "Transfer", "Send", "Post" |
| **Drag Zone** | UI area where files can be dropped | Dashed border area | "Drop zone", "Drop area" |
| **File Validation** | Process of checking file meets requirements | Format check, size check | "Validation", "File check" |
| **Upload Queue** | Ordered list of files waiting or being uploaded | Queue of 3 files | "Upload list", "Pending uploads" |
| **Upload Chunk** | Portion of file uploaded in a single request | 1MB chunk for resumability | "Block", "Part", "Segment" |

### 4.2 File Concepts

| Term | Definition | Examples | Anti-patterns |
|------|------------|----------|---------------|
| **File** | Audio or video file to be transcribed | meeting.mp3, interview.mp4 | "Document", "Media", "Asset" |
| **File Size** | Size of file in human-readable format | "45 MB", "1.2 GB" | "Size in bytes", "File length" |
| **File Format** | File extension/MIME type | "audio/mpeg", ".wav" | "File type", "Extension", "MIME" |
| **Supported Format** | File format accepted by the system | MP3, WAV, M4A, MP4, WEBM | "Allowed type", "Valid format" |

---

## 5. The Language of Transcript Display

### 5.1 Transcript Concepts

| Term | Definition | Examples | Anti-patterns |
|------|------------|----------|---------------|
| **Transcript** | Complete text output from speech-to-text conversion | Full text of meeting | "Text", "Output", "Result" |
| **Transcript Segment** | Portion of transcript with associated metadata | Segment with timestamp and speaker | "Chunk", "Block", "Section" |
| **Timestamp** | Time marker in transcript (HH:MM:SS or HH:MM:SS.mmm) | 00:15:30, 01:23:45.500 | "Time code", "Time marker", "TC" |
| **Speaker Label** | Identifier for different speakers in audio | Speaker A, Speaker B | "Speaker ID", "Participant", "Name" |
| **Confidence Score** | Algorithm's confidence in transcription accuracy (0-1) | 0.95, 0.87 | "Accuracy", "Score", "Reliability" |

### 5.2 Display Concepts

| Term | Definition | Examples | Anti-patterns |
|------|------------|----------|---------------|
| **Timestamp Navigation** | Clicking timestamp to seek audio player | Click 01:23:45 → audio seeks there | "Time seeking", "Jump to time" |
| **Speaker Highlighting** | Visual distinction of different speakers | Color-coded speaker labels | "Speaker colors", "Participant highlighting" |
| **Search Result** | Match of search query in transcript | Highlighted "keyword" | "Match", "Hit", "Found text" |

---

## 6. The Language of Error Handling

### 6.1 Error Concepts

| Term | Definition | Examples | Anti-patterns |
|------|------------|----------|---------------|
| **Error State** | Condition where operation cannot proceed normally | Upload failed, transcription error | "Failure", "Problem", "Issue" |
| **Error Message** | Human-readable explanation of what went wrong | "Network connection lost" | "Error text", "Failure description" |
| **Recovery Action** | Action user can take to resolve error | "Retry Upload", "Choose different file" | "Fix", "Solution", "Next step" |
| **Graceful Degradation** | Functioning with reduced capability when something fails | Show partial transcript on error | "Fallback", "Reduced mode" |

### 6.2 Error Categories

| Category | Definition | Examples |
|----------|------------|----------|
| **Network Error** | Connection or server communication failure | Timeout, connection lost, 500 error |
| **Validation Error** | Input doesn't meet requirements | Invalid format, file too large |
| **Processing Error** | Backend processing failure | Transcription failed, audio corrupted |
| **Permission Error** | User denied necessary permission | Notification permission denied |

---

## 7. The Language of Theme

### 7.1 Theme Concepts

| Term | Definition | Examples | Anti-patterns |
|------|------------|----------|---------------|
| **Theme** | Visual appearance scheme of the application | Light, Dark, High Contrast | "Color scheme", "Appearance", "Style" |
| **Theme Mode** | Specific theme variant | Light mode, Dark mode | "Theme type", "Variant" |
| **Accent Color** | Primary brand/user-defined color | #3B82F6 (blue), #EF4444 (red) | "Primary color", "Brand color" |
| **System Preference** | User's OS-level theme setting | prefers-color-scheme: dark | "OS theme", "System setting" |
| **Theme Persistence** | Saving theme choice across sessions | localStorage, cookie | "Theme storage", "Saving preference" |

---

## 8. The Language of Accessibility

### 8.1 Accessibility Concepts

| Term | Definition | Examples | Anti-patterns |
|------|------------|----------|---------------|
| **Accessibility** | Design for users with disabilities | WCAG compliance, keyboard navigation | "A11y", "Inclusive design" |
| **ARIA Attribute** | Accessible Rich Internet Applications property | aria-label, aria-live, aria-current | "Aria tag", "Accessibility prop" |
| **Focus Indicator** | Visual cue showing which element has keyboard focus | Blue outline on focused button | "Focus ring", "Focus state" |
| **Screen Reader** | Assistive technology that reads screen content aloud | NVDA, JAWS, VoiceOver | "AT", "Assistive tech" |
| **Keyboard Navigation** | Using application without mouse | Tab, Enter, Space, Arrow keys | "Keyboard-only", "No mouse" |
| **Color Contrast** | Ratio between foreground and background colors | 4.5:1 for normal text | "Contrast ratio", "Color difference" |

---

## 9. State Language

### 9.1 Task States

| State | Definition | Visual Indicator |
|-------|------------|------------------|
| **Pending** | Task created but not started | Gray icon, "Waiting..." |
| **In Progress** | Task actively processing | Blue spinner, progress bar filling |
| **Completed** | Task finished successfully | Green checkmark |
| **Failed** | Task ended with error | Red X, error message |
| **Cancelled** | Task stopped by user | Gray X, "Cancelled" |
| **Paused** | Task temporarily suspended | Yellow pause icon |

### 9.2 Component States

| Component | States |
|-----------|--------|
| **Progress Bar** | Empty, Filling, Complete, Error |
| **Notification** | Showing, Dismissing, Dismissed |
| **Upload Zone** | Idle, Drag Over, Processing, Error |
| **Button** | Default, Hover, Active, Disabled, Loading |
| **Input** | Default, Focused, Error, Disabled |

---

## 10. Action Language (Verbs)

### 10.1 User Actions

| Verb | Definition | Direct Object |
|------|------------|---------------|
| **Upload** | Send file to server | File, Document |
| **Transcribe** | Convert audio to text | File, Recording |
| **Cancel** | Stop before completion | Task, Upload |
| **Retry** | Attempt again after failure | Task, Upload |
| **Search** | Find text within transcript | Query, Keyword |
| **Export** | Save transcript in specific format | Transcript (as SRT, TXT) |
| **Seek** | Jump to specific timestamp | Timestamp, Time |
| **Dismiss** | Close notification | Notification, Toast |
| **Toggle** | Switch between two states | Theme, Speaker labels |
| **Grant** | Give permission | Notification access |

### 10.2 System Actions

| Verb | Definition | Subject |
|------|------------|---------|
| **Notify** | Send notification to user | System, Application |
| **Validate** | Check if input meets requirements | File, Input |
| **Estimate** | Calculate predicted value | Time, Duration |
| **Update** | Change to new value | Progress, Status |
| **Persist** | Save for later retrieval | State, Preference |
| **Resume** | Continue after pause | Upload, Task |
| **Degradate** | Function with reduced capability | Gracefully, Fallback |

---

## 11. Bounded Context Language Summary

### 11.1 Progress Tracking Context

**Core Terms**: Task, Progress, Stage, Percentage, Time Estimate, Time Remaining, Time Elapsed

**Key Phrases**:
- "Track progress of transcription task"
- "Calculate time estimate based on stage"
- "Update progress percentage"

### 11.2 Notification Context

**Core Terms**: Notification, Notification Channel, Toast, Notification Permission, Notification Action

**Key Phrases**:
- "Send notification on task completion"
- "Request notification permission"
- "Display toast notification"

### 11.3 File Upload Context

**Core Terms**: Upload, File, File Validation, Drag Zone, Upload Queue, Upload Chunk

**Key Phrases**:
- "Upload file to server"
- "Validate file format and size"
- "Add file to upload queue"

### 11.4 Transcript Display Context

**Core Terms**: Transcript, Transcript Segment, Timestamp, Speaker Label, Timestamp Navigation, Search Result

**Key Phrases**:
- "Display transcript with timestamps"
- "Navigate to timestamp"
- "Search within transcript"

### 11.5 Error Handling Context

**Core Terms**: Error State, Error Message, Recovery Action, Graceful Degradation

**Key Phrases**:
- "Display error with recovery action"
- "Degrade gracefully on error"
- "Retry failed operation"

### 11.6 Theme Context

**Core Terms**: Theme, Theme Mode, Accent Color, System Preference, Theme Persistence

**Key Phrases**:
- "Toggle theme mode"
- "Detect system theme preference"
- "Persist theme choice"

### 11.7 Accessibility Context

**Core Terms**: Accessibility, ARIA Attribute, Focus Indicator, Screen Reader, Keyboard Navigation

**Key Phrases**:
- "Add ARIA label for accessibility"
- "Ensure keyboard navigation works"
- "Maintain visible focus indicator"

---

## 12. Language Consistency Rules

### 12.1 Naming Conventions

**In Code**:
```typescript
// Classes: PascalCase, noun phrases
class ProgressTracker { }
class NotificationManager { }

// Methods: camelCase, verb phrases
progressTracker.updatePercentage(50)
notificationManager.sendNotification(message)

// Variables: camelCase, descriptive
const timeRemaining = calculateETA()
const currentStage = Stage.TRANSCRIBING

// Constants: SCREAMING_SNAKE_CASE
const MAX_FILE_SIZE = 1024 * 1024 * 1024 // 1GB
const UPDATE_INTERVAL_MS = 1000

// Interfaces: PascalCase with 'I' prefix or without
interface ProgressState { }
interface INotificationService { }
```

**In UI Text**:
- Use sentence case for labels: "Upload file" not "Upload File"
- Use complete sentences for errors: "Network connection lost. Please check your internet."
- Use action verbs for buttons: "Upload" not "File Upload"

### 12.2 Prohibited Terms

**Avoid using** (use preferred term instead):
| Don't Use | Use Instead | Reason |
|-----------|-------------|--------|
| "Job" | Task | "Job" implies work queue, not user-centric |
| "Percentage done" | Progress / Percentage | Clearer, more precise |
| "Step" | Stage | "Stage" is more formal and descriptive |
| "ETA" | Time Estimate / Time Remaining | More user-friendly |
| "Alert" | Notification | "Notification" is less alarming |
| "Toast message" | Toast | Redundant |
| "Drop zone" | Drag Zone | More descriptive of action |
| "Time code" | Timestamp | Industry standard |
| "A11y" | Accessibility | Use full term (except in code comments) |

---

## 13. Language Evolution

### 13.1 Language Change Process

1. **Proposal**: Team member suggests new term or definition change
2. **Discussion**: Review with domain experts and developers
3. **Decision**: Agree on change and update documentation
4. **Propagation**: Update code, UI text, and documentation
5. **Validation**: Ensure consistency across all contexts

### 13.2 Current Language Gaps

| Gap | Proposed Term | Status |
|-----|---------------|--------|
| Term for "transcription confidence display" | Confidence Indicator | Proposed |
| Term for "batch upload progress" | Batch Progress | Under discussion |
| Term for "notification while tab is hidden" | Background Notification | Proposed |

---

## 14. Language Quick Reference

### 14.1 Most Common Terms (Top 20)

1. Task
2. Progress
3. Stage
4. Percentage
5. Time Estimate
6. Time Remaining
7. Notification
8. Upload
9. File
10. Transcript
11. Timestamp
12. Speaker Label
13. Error
14. Theme
15. Retry
16. Cancel
17. Complete
18. Fail
19. Validate
20. Search

### 14.2 Common Phrases

- "Track progress of task"
- "Send notification on completion"
- "Upload file to server"
- "Display transcript with timestamps"
- "Handle error with retry option"
- "Toggle between light and dark themes"
- "Estimate time remaining for task"
- "Validate file before upload"
- "Search within transcript"
- "Navigate to timestamp"

---

*End of Ubiquitous Language Documentation*
