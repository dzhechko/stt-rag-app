# C4 Model: System Context Diagram
## Feature 1: UI/UX Improvements for STT Application

| Version | Date | Author | Status |
|---------|------|--------|--------|
| 1.0 | 2025-02-03 | System Architect | Draft |

---

## 1. System Context (Level 1)

The System Context diagram shows the STT application in its environment, connecting to users and external systems.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        System Context - STT Application                     │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│                              ┌──────────────────┐                            │
│                              │  Content Creator │                            │
│                              │  (Podcaster)     │                            │
│                              └────────┬─────────┘                            │
│                                       │                                       │
│                                       │ Uploads audio/video files            │
│                                       │ Views progress                       │
│                                       │ Receives notifications               │
│                                       │ Reads transcripts                    │
│                                       │                                       │
│                                       ▼                                       │
│      ┌──────────────────────────────────────────────────────────────────┐   │
│      │                                                                  │   │
│      │                     STT Application                              │   │
│      │                                                                  │   │
│      │  A web application that transcribes audio/video files            │   │
│      │  into text with real-time progress tracking, notifications,      │   │
│      │  and an enhanced user experience.                                │   │
│      │                                                                  │   │
│      └──────────────────────────┬───────────────────────────────────────┘   │
│                                 │                                           │
│                                 │ REST API                                  │
│                                 │ WebSocket                                 │
│                                 │                                           │
│                    ┌────────────▼────────────┐                             │
│                    │  STT Backend Service    │                             │
│                    │  (FastAPI)              │                             │
│                    └─────────────────────────┘                             │
│                                                                              │
│      ┌─────────────────────────────────────────────────────────────────┐   │
│      │                        Browser                                   │   │
│      │  • Renders UI components                                          │   │
│      │  • Executes JavaScript for real-time updates                      │   │
│      │  • Manages WebSocket connections                                   │   │
│      │  • Stores theme/preferences in localStorage                       │   │
│      └─────────────────────────────────────────────────────────────────┘   │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

### System Context Description

| Element | Description | Responsibilities |
|---------|-------------|------------------|
| **STT Application** | The software system being designed | Provides speech-to-text transcription with enhanced UX |
| **Content Creator** | Primary user (podcaster, journalist, student) | Uploads files, monitors progress, receives notifications, reads transcripts |
| **STT Backend Service** | External service providing transcription | Processes audio/video, returns transcripts, provides progress updates |
| **Browser** | Web browser running the application | Renders UI, executes JavaScript, manages connections |

### User Interactions

| User | Interaction | Description |
|------|-------------|-------------|
| Content Creator | Upload file | Selects or drags audio/video file to upload |
| Content Creator | View progress | Monitors real-time progress bar and time estimate |
| Content Creator | Receive notification | Gets notified when transcription completes or errors occur |
| Content Creator | Read transcript | Views formatted transcript with timestamps |
| Content Creator | Search transcript | Finds specific text within transcript |
| Content Creator | Export transcript | Downloads transcript in various formats (TXT, SRT, JSON) |
| Content Creator | Toggle theme | Switches between light/dark/high-contrast modes |

### System Goals

1. **Provide accurate time estimates** so users can plan their time
2. **Keep users informed** with real-time progress updates
3. **Notify users promptly** when tasks complete or fail
4. **Make file upload easy** with drag-drop and validation
5. **Display transcripts clearly** with timestamps and speaker labels
6. **Handle errors gracefully** with clear messages and recovery options
7. **Work on all devices** with responsive design
8. **Support accessibility** with keyboard navigation and screen reader support

### External Systems

| System | Type | Interaction |
|--------|------|-------------|
| STT Backend Service | REST API, WebSocket | File upload, progress updates, transcript retrieval |
| Browser Notification API | Browser API | Display system notifications |
| Local Storage | Browser Storage | Persist theme, preferences, notification history |

---

## 2. Container Diagram (Level 2)

The Container diagram shows the major containers (applications, data stores, services) that make up the STT application.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                      Containers - STT Application                           │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                         User                                        │   │
│  └──────────────────────────────────────┬──────────────────────────────┘   │
│                                         │                                     │
│                                         │ HTTPS                               │
│                                         │                                     │
│  ┌─────────────────────────────────────▼─────────────────────────────────┐   │
│  │                                                                     │   │
│  │  ┌───────────────────────────────────────────────────────────────┐ │   │
│  │  │                   Single-Page Application                     │ │   │
│  │  │  (React 18 + TypeScript)                                      │ │   │
│  │  │                                                                │ │   │
│  │  │  Responsibilities:                                            │ │   │
│  │  │  • Render UI components                                       │ │   │
│  │  │  • Manage application state (React Query)                     │ │   │
│  │  │  • Handle user interactions                                   │ │   │
│  │  │  • Display real-time progress                                 │ │   │
│  │  │  • Show notifications (in-app + browser)                       │ │   │
│  │  │  • Handle file upload (drag-drop)                             │ │   │
│  │  │  • Display transcripts with timestamps                        │ │   │
│  │  │  • Support theme switching                                    │ │   │
│  │  └────────────────────────────────────────────────────────────────┘ │   │
│  │                                                                     │   │
│  │  ┌───────────────────────────────────────────────────────────────┐ │   │
│  │  │                Static Asset Server                             │ │   │
│  │  │  (CDN: Cloudflare / AWS CloudFront)                           │ │   │
│  │  │                                                                │ │   │
│  │  │  Responsibilities:                                            │ │   │
│  │  │  • Serve JavaScript bundles                                    │ │   │
│  │  │  • Serve CSS stylesheets                                       │ │   │
│  │  │  • Serve images and assets                                     │ │   │
│  │  │  • Cache static content                                        │ │   │
│  │  └────────────────────────────────────────────────────────────────┘ │   │
│  │                                                                     │   │
│  └──────────────────────────────────────┬──────────────────────────────┘   │
│                                         │                                     │
│                    ┌────────────────────┼────────────────────┐               │
│                    │                    │                    │               │
│                    │ REST API           │ WebSocket          │               │
│                    │                    │                    │               │
│  ┌─────────────▼──────────────┐  ┌─────▼──────────┐  ┌─────▼──────────┐   │
│  │   STT Backend API         │  │  WebSocket     │  │  Notification  │   │
│  │   (FastAPI)               │  │  Server        │  │  Service API   │   │
│  │                            │  │  (FastAPI)     │  │  (Browser)     │   │
│  │  • File upload endpoint    │  │                │  │                │   │
│  │  • Progress query          │  │  • Real-time   │  │  • Permission  │   │
│  │  • Transcript retrieval    │  │    progress    │  │    request     │   │
│  │  • Error reporting         │  │  • Stage       │  │  • Show        │   │
│  │                            │  │    updates    │  │    notify      │   │
│  └────────────────────────────┘  └────────────────┘  └────────────────┘   │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    Browser Local Storage                            │   │
│  │                                                                    │   │
│  │  • Theme preference (light/dark)                                   │   │
│  │  • Accent color                                                    │   │
│  │  • Notification history                                            │   │
│  │  • User preferences                                                │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

### Container Descriptions

| Container | Technology | Responsibilities |
|-----------|------------|------------------|
| **Single-Page Application** | React 18, TypeScript, React Query | Main web application UI |
| **Static Asset Server** | CDN (Cloudflare/AWS) | Serves optimized static assets |
| **STT Backend API** | FastAPI, Python | RESTful API for uploads, transcripts |
| **WebSocket Server** | FastAPI, WebSockets | Real-time progress updates |
| **Browser Local Storage** | localStorage, IndexedDB | Client-side data persistence |
| **Notification Service** | Browser Notification API | System notifications |

### Container Interactions

| From | To | Interaction | Technology |
|------|-----|-------------|-------------|
| User | SPA | Interacts with UI | Browser |
| SPA | Backend API | Upload file, query progress | REST API (HTTP) |
| SPA | WebSocket Server | Subscribe to progress, receive updates | WebSocket |
| SPA | Notification Service | Request permission, show notification | Browser API |
| SPA | Local Storage | Save/load preferences | localStorage API |
| SPA | Static Server | Load JS bundles, assets | HTTP |

---

## 3. Component Diagram (Level 3)

The Component diagram shows the internal structure of key containers.

### SPA Components

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    Components - Single-Page Application                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                        Pages Layer                                  │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────┐  │   │
│  │  │ UploadPage   │  │ Transcripts  │  │   TranscriptDetailPage    │  │   │
│  │  │              │  │ Page         │  │                          │  │   │
│  │  │ • UploadZone │  │ • Transcript │  │ • TranscriptDisplay      │  │   │
│  │  │ • FileQueue  │  │   List       │  │ • TimestampNavigation     │  │   │
│  │  │ • ProgressBar│  │ • SearchBar  │  │ • Search                  │  │   │
│  │  └──────────────┘  └──────────────┘  │ • ExportButtons           │  │   │
│  │                                       └──────────────────────────┘  │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                      │                                     │
│                                      ▼                                     │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                     Feature Components                               │   │
│  │  ┌──────────────────────┐  ┌────────────────────────────────────┐  │   │
│  │  │  Progress Tracking    │  │    Notifications                  │  │   │
│  │  │                       │  │                                    │  │   │
│  │  │ • ProgressBar         │  │ • ToastProvider                   │  │   │
│  │  │ • StageIndicator      │  │ • Toast                           │  │   │
│  │  │ • TimeEstimateDisplay │  │ • NotificationPermissionRequest    │  │   │
│  │  │ • ProgressStates      │  │ • NotificationHistory             │  │   │
│  │  └──────────────────────┘  └────────────────────────────────────┘  │   │
│  │                                                                    │   │
│  │  ┌──────────────────────┐  ┌────────────────────────────────────┐  │   │
│  │  │  File Upload          │  │    Transcript Display              │  │   │
│  │  │                       │  │                                    │  │   │
│  │  │ • UploadZone          │  │ • TranscriptContent               │  │   │
│  │  │ • DragDropHandler     │  │ • TimestampLink                   │  │   │
│  │  │ • FilePreview         │  │ • SpeakerLabel                    │  │   │
│  │  │ • FileValidation      │  │ • SearchHighlight                 │  │   │
│  │  │ • UploadQueue         │  │ • ExportMenu                      │  │   │
│  │  └──────────────────────┘  └────────────────────────────────────┘  │   │
│  │                                                                    │   │
│  │  ┌──────────────────────┐  ┌────────────────────────────────────┐  │   │
│  │  │  Error Handling       │  │    Theme System                    │  │   │
│  │  │                       │  │                                    │  │   │
│  │  │ • ErrorBoundary       │  │ • ThemeProvider                   │  │   │
│  │  │ • ErrorMessage        │  │ • ThemeToggle                     │  │   │
│  │  │ • RetryButton         │  │ • ColorPicker                     │  │   │
│  │  │ • RecoveryActions     │  │ • ThemeCSSVariables               │  │   │
│  │  └──────────────────────┘  └────────────────────────────────────┘  │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                      │                                     │
│                                      ▼                                     │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                      Shared Components (UI Library)                   │   │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐  │   │
│  │  │  Button  │ │   Input  │ │  Modal   │ │ Dropdown │ │  Badge   │  │   │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘  │   │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐  │   │
│  │  │   Card   │ │ Avatar   │ │ Tooltip  │ │  Switch  │ │  Slider  │  │   │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘  │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                      │                                     │
│                                      ▼                                     │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                       Services Layer                                │   │
│  │  ┌────────────────────────────────────────────────────────────────┐ │   │
│  │  │  API Services                                                  │ │   │
│  │  │  • apiClient (Axios)                                           │ │   │
│  │  │  • uploadApi                                                   │ │   │
│  │  │  • transcriptApi                                               │ │   │
│  │  │  • notificationApi                                              │ │   │
│  │  └────────────────────────────────────────────────────────────────┘ │   │
│  │  ┌────────────────────────────────────────────────────────────────┐ │   │
│  │  │  WebSocket Services                                            │ │   │
│  │  │  • WebSocketManager                                            │ │   │
│  │  │  • ProgressWebSocketClient                                     │ │   │
│  │  │  • ReconnectionHandler                                         │ │   │
│  │  └────────────────────────────────────────────────────────────────┘ │   │
│  │  ┌────────────────────────────────────────────────────────────────┐ │   │
│  │  │  Notification Services                                         │ │   │
│  │  │  • NotificationService                                         │ │   │
│  │  │  • BrowserNotificationAdapter                                  │ │   │
│  │  │  • ToastNotificationService                                    │ │   │
│  │  └────────────────────────────────────────────────────────────────┘ │   │
│  │  ┌────────────────────────────────────────────────────────────────┐ │   │
│  │  │  Utility Services                                              │ │   │
│  │  │  • TimeEstimationAlgorithm                                     │ │   │
│  │  │  • FileValidator                                               │ │   │
│  │  │  • ExportService                                               │ │   │
│  │  └────────────────────────────────────────────────────────────────┘ │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                      │                                     │
│                                      ▼                                     │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                       State Management                              │   │
│  │  ┌────────────────────────────────────────────────────────────────┐ │   │
│  │  │  React Query (Server State)                                    │ │   │
│  │  │  • useTaskProgress                                             │ │   │
│  │  │  • useTranscript                                               │ │   │
│  │  │  • useUploadFile                                               │ │   │
│  │  │  • QueryClient                                                 │ │   │
│  │  └────────────────────────────────────────────────────────────────┘ │   │
│  │  ┌────────────────────────────────────────────────────────────────┐ │   │
│  │  │  React Context (Client State)                                  │ │   │
│  │  │  • ThemeContext                                                │ │   │
│  │  │  • NotificationContext                                         │ │   │
│  │  │  • ErrorContext                                                │ │   │
│  │  └────────────────────────────────────────────────────────────────┘ │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

### Component Descriptions

#### Progress Tracking Components

| Component | Responsibility |
|-----------|---------------|
| **ProgressBar** | Visual progress bar with percentage |
| **StageIndicator** | Shows current and upcoming stages with icons |
| **TimeEstimateDisplay** | Displays time remaining with confidence level |
| **ProgressStates** | Manages loading, active, complete, error states |

#### Notification Components

| Component | Responsibility |
|-----------|---------------|
| **ToastProvider** | Portal container for toast notifications |
| **Toast** | Individual toast notification component |
| **NotificationPermissionRequest** | UI for requesting notification permission |
| **NotificationHistory** | List of past notifications |

#### File Upload Components

| Component | Responsibility |
|-----------|---------------|
| **UploadZone** | Drag-drop area for file selection |
| **DragDropHandler** | Manages drag-drop events |
| **FilePreview** | Shows selected file info |
| **FileValidation** | Validates file format and size |
| **UploadQueue** | Manages multiple file uploads |

#### Transcript Display Components

| Component | Responsibility |
|-----------|---------------|
| **TranscriptContent** | Displays full transcript text |
| **TimestampLink** | Clickable timestamp that seeks audio |
| **SpeakerLabel** | Shows speaker identification |
| **SearchHighlight** | Highlights search results |
| **ExportMenu** | Dropdown for export format selection |

---

## 4. Data Flow Diagrams

### 4.1 Upload Progress Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        Upload Progress Data Flow                           │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  User drops file on UploadZone                                              │
│       │                                                                     │
│       ▼                                                                     │
│  DragDropHandler.onDrop()                                                   │
│       │                                                                     │
│       ├─► FileValidation.validate(file)                                     │
│       │    ├─► Check format (MP3, WAV, M4A, MP4, WEBM)                      │
│       │    ├─► Check size (< 1GB)                                           │
│       │    └─► Return ValidationResult                                     │
│       │                                                                     │
│       ├─► UploadQueue.add(file)                                            │
│       │                                                                     │
│       ├─► React Query: useUploadFile.mutate(file)                          │
│       │    │                                                               │
│       │    ▼                                                               │
│       │  apiClient.uploadFile(file)                                        │
│       │       │                                                            │
│       │       ├─► POST /api/upload (chunked)                               │
│       │       │                                                            │
│       │       ├─► Backend: Begin upload                                    │
│       │       │                                                            │
│       │       └─► Return { uploadId, taskId }                              │
│       │                                                                    │
│       ├─► WebSocketManager.connect(taskId)                                 │
│       │       │                                                            │
│       │       ├─► ws://api.example.com/ws/progress/{taskId}                 │
│       │       │                                                            │
│       │       └─► Subscribe to progress messages                            │
│       │                                                                    │
│       └─► Update UI state (ProgressTracker)                                │
│            │                                                               │
│            ▼                                                               │
│      Backend sends progress updates:                                       │
│      { type: "progress_update", percentage: 45, stage: "uploading" }        │
│            │                                                               │
│            ├─► WebSocketManager.onMessage()                                │
│            │                                                               │
│            ├─► Update React Query cache                                   │
│            │    queryClient.setQueryData(['tasks', taskId, 'progress'])    │
│            │                                                               │
│            └─► ProgressBar re-renders with new percentage                  │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

### 4.2 Notification Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         Notification Data Flow                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  Task completes (Backend)                                                   │
│       │                                                                     │
│       ▼                                                                     │
│  WebSocket message: { type: "complete", taskId, resultUrl }                  │
│       │                                                                     │
│       ▼                                                                     │
│  WebSocketManager.onMessage()                                               │
│       │                                                                     │
│       ├─► Emit: ProgressCompletedEvent                                     │
│       │                                                                     │
│       ├─► React Query: Invalidate transcript query                          │
│       │    queryClient.invalidateQueries(['transcripts', taskId])          │
│       │                                                                     │
│       └─► NotificationService.send({                                       │
│              type: SUCCESS,                                                │
│              title: "Transcription Complete",                               │
│              message: "Your transcript is ready",                           │
│              channels: [BROWSER, IN_APP, SOUND],                            │
│              actions: [{ label: "View", primary: true }]                    │
│            })                                                               │
│             │                                                               │
│             ├─► Check browser permission                                    │
│             │    │  Granted → new Notification(title, { body, icon })       │
│             │    │  Denied → Skip                                          │
│             │    │                                                         │
│             ├─► Emit: toast-request event                                   │
│             │    │                                                         │
│             │    └─► ToastProvider displays Toast component                 │
│             │              │                                               │
│             │              ├─► Animation in (slide up)                      │
│             │              │                                               │
│             │              ├─► Auto-dismiss after 5 seconds                 │
│             │              │                                               │
│             │              └─► Animation out (fade out)                     │
│             │                                                             │
│             └─► Play success sound (if enabled)                             │
│                  │                                                         │
│                  └─► new Audio('/sounds/success.mp3').play()                │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

### 4.3 Theme Toggle Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          Theme Toggle Data Flow                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  User clicks theme toggle button                                            │
│       │                                                                     │
│       ▼                                                                     │
│  ThemeToggle.onClick()                                                     │
│       │                                                                     │
│       ├─► ThemeContext.setTheme(newTheme)                                  │
│       │    │                                                               │
│       │    ├─► Update context state                                        │
│       │    │    setThemeState(newTheme)                                    │
│       │    │                                                               │
│       │    ├─► Save to localStorage                                        │
│       │    │    localStorage.setItem('theme', newTheme)                    │
│       │    │                                                               │
│       │    └─► Update CSS variables                                        │
│       │         document.documentElement.setAttribute('data-theme', newTheme)│
│       │                                                                     │
│       └─► React re-renders all components                                  │
│            │                                                               │
│            └─► CSS variables cascade to all children                        │
│                 │                                                         │
│                 └─► All styled components pick up new theme colors          │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

*End of C4 Diagrams Documentation*
