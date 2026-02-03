# ADR-003: Notification System Architecture

| Status | Proposed by | Decision date | Effective date |
|--------|-------------|---------------|---------------|
| Accepted | System Architect | 2025-02-03 | 2025-02-03 |

---

## Context

The STT application processes files asynchronously. Users need to be notified when:
1. Transcription completes
2. Errors occur
3. Progress reaches milestones
4. Other significant events happen

Multiple notification channels are needed:
- **Browser notifications**: Work when user is on another tab
- **In-app toasts**: Non-blocking, always visible
- **Sound**: Optional audio cue
- **Email**: Future enhancement for long-running tasks

## Decision

Implement a **multi-channel notification system** with the following architecture:

```
┌─────────────────────────────────────────────────────────────────────────┐
│                      Notification System Architecture                  │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                   Notification Aggregator                       │   │
│  │  • Receives notification requests from all sources              │   │
│  │  • Determines which channels to use                             │   │
│  │  • Manages notification queue                                   │   │
│  │  • Handles permission state                                     │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                              │                                          │
│                              ▼                                          │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                    Notification Channels                         │   │
│  │                                                                  │   │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  │   │
│  │  │   Browser       │  │    In-App       │  │     Sound       │  │   │
│  │  │   Notification  │  │    Toast        │  │     Audio       │  │   │
│  │  │                 │  │                 │  │                 │  │   │
│  │  │  • Native API   │  │  • React Portal │  │  • Audio API    │  │   │
│  │  │  • Permission   │  │  • Animations   │  │  • Volume ctrl  │  │   │
│  │  │  • Badge count  │  │  • Auto-dismiss │  │  • Mute option  │  │   │
│  │  └─────────────────┘  └─────────────────┘  └─────────────────┘  │   │
│  │                                                                  │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                              │                                          │
│                              ▼                                          │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                    Notification History                         │   │
│  │  • Append-only log of all notifications                         │   │
│  │  • Persists across sessions                                     │   │
│  │  • Accessible via notification center                           │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### Implementation Details

#### Core Notification Service

```typescript
// src/lib/notifications/notification-service.ts

export interface NotificationRequest {
  id?: string;
  type: NotificationType;
  title: string;
  message: string;
  icon?: string;
  image?: string;
  actions?: NotificationAction[];
  duration?: number;  // Auto-dismiss after ms (for toasts)
  priority: NotificationPriority;
  channels: NotificationChannel[];
  data?: Record<string, unknown>;
}

export interface NotificationAction {
  id: string;
  label: string;
  icon?: string;
  action: () => void | Promise<void>;
  primary?: boolean;
}

export enum NotificationType {
  INFO = "info",
  SUCCESS = "success",
  WARNING = "warning",
  ERROR = "error",
}

export enum NotificationPriority {
  LOW = "low",
  NORMAL = "normal",
  HIGH = "high",
  URGENT = "urgent",
}

export enum NotificationChannel {
  BROWSER = "browser",
  IN_APP = "in_app",
  SOUND = "sound",
}

class NotificationService {
  private browserPermission: NotificationPermission = "default";
  private preferences: NotificationPreferences;
  private history: NotificationRecord[] = [];

  constructor() {
    this.preferences = this.loadPreferences();
    this.history = this.loadHistory();
    this.initBrowserPermission();
  }

  // Public API
  async send(request: NotificationRequest): Promise<string> {
    const notificationId = request.id || this.generateId();

    // Filter channels based on permission and preferences
    const enabledChannels = this.filterEnabledChannels(request.channels);

    if (enabledChannels.length === 0) {
      console.warn("No enabled notification channels for request", request);
      return notificationId;
    }

    // Record notification
    const record: NotificationRecord = {
      id: notificationId,
      request,
      channels: enabledChannels,
      timestamp: new Date().toISOString(),
      status: "pending",
    };
    this.history.unshift(record);
    this.saveHistory();

    // Send to each channel
    const results = await Promise.allSettled([
      enabledChannels.includes(NotificationChannel.BROWSER) &&
        this.sendBrowserNotification(record),
      enabledChannels.includes(NotificationChannel.IN_APP) &&
        this.sendInAppNotification(record),
      enabledChannels.includes(NotificationChannel.SOUND) &&
        this.sendSoundNotification(record),
    ]);

    // Check if any succeeded
    const anySuccess = results.some(r => r.status === "fulfilled");
    record.status = anySuccess ? "delivered" : "failed";
    this.saveHistory();

    return notificationId;
  }

  private filterEnabledChannels(channels: NotificationChannel[]): NotificationChannel[] {
    return channels.filter(channel => {
      switch (channel) {
        case NotificationChannel.BROWSER:
          return this.browserPermission === "granted" &&
                 this.preferences.browserEnabled;
        case NotificationChannel.IN_APP:
          return this.preferences.inAppEnabled;
        case NotificationChannel.SOUND:
          return this.preferences.soundEnabled;
      }
    });
  }

  // Browser Notifications
  private async initBrowserPermission(): Promise<void> {
    if (!("Notification" in window)) {
      this.browserPermission = "denied";
      return;
    }

    this.browserPermission = Notification.permission;

    if (this.browserPermission === "default") {
      // Don't request immediately, wait for user interaction
      this.setupPermissionRequestTrigger();
    }
  }

  private async requestBrowserPermission(): Promise<NotificationPermission> {
    if (!("Notification" in window)) {
      return "denied";
    }

    const permission = await Notification.requestPermission();
    this.browserPermission = permission;

    // Emit event
    if (permission === "granted") {
      this.emit("permission-granted");
    } else if (permission === "denied") {
      this.emit("permission-denied");
    }

    return permission;
  }

  private async sendBrowserNotification(record: NotificationRecord): Promise<void> {
    if (this.browserPermission !== "granted") {
      return;
    }

    const notification = new Notification(record.request.title, {
      body: record.request.message,
      icon: record.request.icon,
      image: record.request.image,
      tag: record.id,
      requireInteraction: record.request.priority === NotificationPriority.URGENT,
      actions: record.request.actions?.map(a => ({
        action: a.id,
        title: a.label,
        icon: a.icon,
      })),
    });

    // Handle action clicks
    notification.onclick = (event) => {
      event.preventDefault();
      window.focus();
      this.handleNotificationClick(record.id);
    };

    notification.onclose = () => {
      this.handleNotificationDismiss(record.id, "closed");
    };

    // Auto-close based on priority
    if (record.request.priority !== NotificationPriority.URGENT) {
      setTimeout(() => notification.close(), 5000);
    }
  }

  // In-App Toast Notifications
  private async sendInAppNotification(record: NotificationRecord): Promise<void> {
    // Emit event that toast component listens to
    this.emit("toast-request", record);
  }

  // Sound Notifications
  private async sendSoundNotification(record: NotificationRecord): Promise<void> {
    if (!this.preferences.soundEnabled) {
      return;
    }

    const soundUrl = this.getSoundUrl(record.request.type);
    const audio = new Audio(soundUrl);
    audio.volume = this.preferences.soundVolume;

    try {
      await audio.play();
    } catch (error) {
      console.error("Failed to play notification sound:", error);
    }
  }

  private getSoundUrl(type: NotificationType): string {
    const sounds: Record<NotificationType, string> = {
      [NotificationType.INFO]: "/sounds/info.mp3",
      [NotificationType.SUCCESS]: "/sounds/success.mp3",
      [NotificationType.WARNING]: "/sounds/warning.mp3",
      [NotificationType.ERROR]: "/sounds/error.mp3",
    };
    return sounds[type];
  }

  // History Management
  private loadHistory(): NotificationRecord[] {
    const stored = localStorage.getItem("notification-history");
    return stored ? JSON.parse(stored) : [];
  }

  private saveHistory(): void {
    // Keep only last 100 notifications
    const trimmed = this.history.slice(0, 100);
    localStorage.setItem("notification-history", JSON.stringify(trimmed));
  }

  getHistory(limit: number = 10): NotificationRecord[] {
    return this.history.slice(0, limit);
  }

  clearHistory(): void {
    this.history = [];
    localStorage.removeItem("notification-history");
  }

  // Preferences
  private loadPreferences(): NotificationPreferences {
    const stored = localStorage.getItem("notification-preferences");
    return {
      browserEnabled: true,
      inAppEnabled: true,
      soundEnabled: false,
      soundVolume: 0.5,
      ...stored ? JSON.parse(stored) : {},
    };
  }

  updatePreferences(updates: Partial<NotificationPreferences>): void {
    this.preferences = { ...this.preferences, ...updates };
    localStorage.setItem("notification-preferences", JSON.stringify(this.preferences));
    this.emit("preferences-updated", this.preferences);
  }

  // Utility methods
  private generateId(): string {
    return `notif_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }

  // Simple event emitter
  private listeners = new Map<string, Set<Function>>();

  private on(event: string, callback: Function): () => void {
    if (!this.listeners.has(event)) {
      this.listeners.set(event, new Set());
    }
    this.listeners.get(event)!.add(callback);

    return () => {
      this.listeners.get(event)?.delete(callback);
    };
  }

  private emit(event: string, data?: unknown): void {
    this.listeners.get(event)?.forEach(callback => callback(data));
  }

  private setupPermissionRequestTrigger(): void {
    // Show permission request on first user interaction
    const handleInteraction = () => {
      this.requestBrowserPermission();
      document.removeEventListener("click", handleInteraction);
      document.removeEventListener("keydown", handleInteraction);
    };

    document.addEventListener("click", handleInteraction, { once: true });
    document.addEventListener("keydown", handleInteraction, { once: true });
  }
}

export const notificationService = new NotificationService();
```

#### React Hook for Notifications

```typescript
// src/hooks/use-notification.ts
import { useCallback, useEffect } from 'react';
import { notificationService, NotificationRequest } from '@/lib/notifications/notification-service';

export function useNotification() {
  const send = useCallback((request: NotificationRequest) => {
    return notificationService.send(request);
  }, []);

  const requestPermission = useCallback(() => {
    return notificationService.requestBrowserPermission();
  }, []);

  const getHistory = useCallback((limit?: number) => {
    return notificationService.getHistory(limit);
  }, []);

  const clearHistory = useCallback(() => {
    notificationService.clearHistory();
  }, []);

  return {
    send,
    requestPermission,
    getHistory,
    clearHistory,
    permission: notificationService.getBrowserPermission(),
  };
}

// Convenience hooks for specific notification types
export function useSuccessNotification() {
  const { send } = useNotification();

  return useCallback((title: string, message: string) => {
    return send({
      type: NotificationType.SUCCESS,
      title,
      message,
      channels: [NotificationChannel.IN_APP, NotificationChannel.BROWSER],
      priority: NotificationPriority.NORMAL,
    });
  }, [send]);
}

export function useErrorNotification() {
  const { send } = useNotification();

  return useCallback((title: string, message: string, actions?: NotificationAction[]) => {
    return send({
      type: NotificationType.ERROR,
      title,
      message,
      actions,
      channels: [NotificationChannel.IN_APP, NotificationChannel.BROWSER, NotificationChannel.SOUND],
      priority: NotificationPriority.HIGH,
    });
  }, [send]);
}
```

#### Toast Component

```typescript
// src/components/toast/toast-provider.tsx
import { useEffect, useState } from 'react';
import { createPortal } from 'react-dom';
import { Toast } from './toast';
import { notificationService, NotificationRecord } from '@/lib/notifications/notification-service';

export function ToastProvider() {
  const [toasts, setToasts] = useState<NotificationRecord[]>([]);

  useEffect(() => {
    // Listen for toast requests
    const unsubscribe = notificationService.on("toast-request", (record: NotificationRecord) => {
      setToasts(prev => [...prev, record]);

      // Auto-dismiss after duration
      const duration = record.request.duration || 5000;
      setTimeout(() => {
        handleDismiss(record.id);
      }, duration);
    });

    return unsubscribe;
  }, []);

  const handleDismiss = (id: string) => {
    setToasts(prev => prev.filter(t => t.id !== id));
    notificationService.handleNotificationDismiss(id, "dismissed");
  };

  const handleAction = (id: string, actionId: string) => {
    const toast = toasts.find(t => t.id === id);
    if (!toast) return;

    const action = toast.request.actions?.find(a => a.id === actionId);
    if (action) {
      action.action();
      handleDismiss(id);
    }
  };

  return createPortal(
    <div className="toast-container">
      {toasts.map(toast => (
        <Toast
          key={toast.id}
          record={toast}
          onDismiss={() => handleDismiss(toast.id)}
          onAction={(actionId) => handleAction(toast.id, actionId)}
        />
      ))}
    </div>,
    document.body
  );
}

// src/components/toast/toast.tsx
interface ToastProps {
  record: NotificationRecord;
  onDismiss: () => void;
  onAction: (actionId: string) => void;
}

export function Toast({ record, onDismiss, onAction }: ToastProps) {
  const { request } = record;

  return (
    <div className={`toast toast--${request.type}`}>
      <div className="toast__icon">
        {getIcon(request.type)}
      </div>

      <div className="toast__content">
        <div className="toast__title">{request.title}</div>
        <div className="toast__message">{request.message}</div>

        {request.actions && request.actions.length > 0 && (
          <div className="toast__actions">
            {request.actions.map(action => (
              <button
                key={action.id}
                className={`toast__action ${action.primary ? 'toast__action--primary' : ''}`}
                onClick={() => onAction(action.id)}
              >
                {action.label}
              </button>
            ))}
          </div>
        )}
      </div>

      <button className="toast__close" onClick={onDismiss}>
        <CloseIcon />
      </button>
    </div>
  );
}
```

### Notification Flows

#### Completion Notification Flow

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    Completion Notification Flow                         │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  Task Complete (Backend)                                               │
│       │                                                                │
│       ▼                                                                │
│  WebSocket Message → Frontend                                          │
│       │                                                                │
│       ▼                                                                │
│  ProgressTracker.complete()                                            │
│       │                                                                │
│       ▼                                                                │
│  Emit: ProgressCompletedEvent                                          │
│       │                                                                │
│       ▼                                                                │
│  NotificationService.send({                                           │
│    type: SUCCESS,                                                      │
│    title: "Transcription Complete",                                    │
│    message: "Your transcript is ready",                                │
│    channels: [BROWSER, IN_APP, SOUND],                                 │
│    actions: [                                                          │
│      { id: "view", label: "View", primary: true },                     │
│      { id: "dismiss", label: "Close" }                                 │
│    ]                                                                   │
│  })                                                                    │
│       │                                                                │
│       ├─► Browser Notification (if permission granted)                 │
│       │    - Shows native notification                                 │
│       │    - User clicks "View" → Navigate to transcript               │
│       │                                                                │
│       ├─► In-App Toast (always)                                       │
│       │    - Shows in toast container                                 │
│       │    - Auto-dismiss after 5 seconds                              │
│       │    - User can click action buttons                            │
│       │                                                                │
│       └─► Sound (if enabled)                                          │
│            - Plays success sound                                      │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

#### Error Notification Flow

```
┌─────────────────────────────────────────────────────────────────────────┐
│                       Error Notification Flow                           │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  Error Occurred (Backend/Frontend)                                     │
│       │                                                                │
│       ▼                                                                │
│  ErrorHandler.setError()                                              │
│       │                                                                │
│       ▼                                                                │
│  Emit: ErrorOccurredEvent                                             │
│       │                                                                │
│       ▼                                                                │
│  NotificationService.send({                                           │
│    type: ERROR,                                                        │
│    title: "Upload Failed",                                             │
│    message: "Network connection lost. Please check your internet.",    │
│    channels: [BROWSER, IN_APP, SOUND],                                 │
│    priority: HIGH,                                                     │
│    actions: [                                                          │
│      { id: "retry", label: "Retry", primary: true },                   │
│      { id: "dismiss", label: "Cancel" }                                │
│    ]                                                                   │
│  })                                                                    │
│       │                                                                │
│       ├─► Browser Notification (require interaction)                   │
│       ├─► In-App Toast (persistent until action)                       │
│       └─► Sound (error sound)                                         │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

## Alternatives Considered

### Alternative 1: Browser Notifications Only

**Description**: Use only native browser Notification API.

**Pros**:
- Native implementation
- Works when tab is hidden
- System-level integration

**Cons**:
- Requires permission (many users deny)
- No fallback if permission denied
- Limited customization
- Inconsistent across browsers

**Rejected because**: High denial rate means many users wouldn't get notifications.

### Alternative 2: In-App Only (No Browser)

**Description**: Use only in-app toast notifications.

**Pros**:
- No permission needed
- Full customization
- Consistent UX

**Cons**:
- Doesn't work when tab is hidden
- User might miss important notifications
- No system-level integration

**Rejected because**: Users need notifications when working in other tabs.

### Alternative 3: Third-Party Service (OneSignal, Pusher)

**Description**: Use external push notification service.

**Pros**:
- Works even when browser closed
- Handles push notifications
- Advanced features

**Cons**:
- Additional cost
- External dependency
- Privacy concerns
- Overkill for current needs

**Rejected because**: Browser notifications + in-app is sufficient for now.

## Consequences

### Positive

1. **Redundancy**: Multiple channels ensure delivery
2. **Graceful degradation**: Works if some channels unavailable
3. **User control**: Users can disable channels they don't want
4. **Rich interactions**: Action buttons in notifications
5. **History**: Users can review past notifications

### Negative

1. **Complexity**: Multiple channels to manage
2. **Permission friction**: Browser permission request may confuse users
3. **Sound annoyance**: Audio can be intrusive
4. **Testing complexity**: Need to test each channel
5. **Bundle size**: Additional code for notification handling

### Mitigations

1. Clear UX around permission requests
2. Sound muted by default
3. Preference panel for easy channel management
4. Comprehensive testing across browsers
5. Code splitting to minimize bundle impact

## Implementation Roadmap

1. **Phase 1**: Core notification service
   - Implement NotificationService class
   - Permission handling
   - History management

2. **Phase 2**: In-app toasts
   - Toast component
   - Animation system
   - Auto-dismiss logic

3. **Phase 3**: Browser notifications
   - Native notification wrapper
   - Permission request UI
   - Action button handling

4. **Phase 4**: Sound notifications
   - Audio file management
   - Volume controls
   - Mute option

5. **Phase 5**: Preferences & history
   - Settings panel
   - Notification center
   - History view

## References

- [Web Notifications API](https://developer.mozilla.org/en-US/docs/Web/API/Notifications_API)
- [React Hot Toast](https://react-hot-toast.com/)
- [Notification Pattern Guidelines](https://www.nngroup.com/articles/notification-placement/)

---

*End of ADR-003*
