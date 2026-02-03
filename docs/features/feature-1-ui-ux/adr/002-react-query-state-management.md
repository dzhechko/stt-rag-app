# ADR-002: React Query for State Management

| Status | Proposed by | Decision date | Effective date |
|--------|-------------|---------------|---------------|
| Accepted | System Architect | 2025-02-03 | 2025-02-03 |

---

## Context

The UI/UX improvements require managing various types of state:

1. **Server State**: Task progress, transcripts, notifications (from API)
2. **Client State**: UI mode, theme preferences, form inputs
3. **URL State**: Current view, filters, search params
4. **Transient State**: Hover states, focus states, modal open/close

Current implementation lacks a formal state management solution, leading to:
- Prop drilling for shared state
- Duplicate data fetching
- Stale data displays
- Complex useEffect dependencies
- Difficulty caching API responses

## Decision

Use **React Query (TanStack Query)** for server state management, combined with **React Context** for client state.

### Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         State Management Layer                          │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                    React Query (Server State)                   │   │
│  │  ┌────────────────────────────────────────────────────────────┐ │   │
│  │  │ Queries (Data Fetching):                                  │ │   │
│  │  │  • useTaskProgress(taskId)                                │ │   │
│  │  │  • useTranscript(taskId)                                  │ │   │
│  │  │  • useNotificationHistory()                               │ │   │
│  │  │  • useUploadStatus(uploadId)                              │ │   │
│  │  └────────────────────────────────────────────────────────────┘ │   │
│  │  ┌────────────────────────────────────────────────────────────┐ │   │
│  │  │ Mutations (Data Updates):                                 │ │   │
│  │  │  • useUploadFile()                                        │ │   │
│  │  │  • useUpdatePreferences()                                 │ │   │
│  │  │  • useDismissNotification()                               │ │   │
│  │  │  • useReportError()                                       │ │   │
│  │  └────────────────────────────────────────────────────────────┘ │   │
│  │  ┌────────────────────────────────────────────────────────────┐ │   │
│  │  │ Cache Management:                                         │ │   │
│  │  │  • Automatic caching & revalidation                       │ │   │
│  │  │  • Optimistic updates                                     │ │   │
│  │  │  • Invalidation & refetching                              │ │   │
│  │  └────────────────────────────────────────────────────────────┘ │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                              │                                          │
│                              │ Integration                              │
│                              │                                          │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                    React Context (Client State)                 │   │
│  │  ┌────────────────────────────────────────────────────────────┐ │   │
│  │  │ ThemeContext:                                              │ │   │
│  │  │  • theme, accentColor, highContrast                        │ │   │
│  │  │  • setTheme(), setAccentColor()                            │ │   │
│  │  └────────────────────────────────────────────────────────────┘ │   │
│  │  ┌────────────────────────────────────────────────────────────┐ │   │
│  │  │ NotificationContext:                                       │ │   │
│  │  │  • permission, preferences                                │ │   │
│  │  │  • requestPermission(), sendNotification()                │ │   │
│  │  └────────────────────────────────────────────────────────────┘ │   │
│  │  ┌────────────────────────────────────────────────────────────┐ │   │
│  │  │ ErrorContext:                                              │ │   │
│  │  │  • currentError, recoveryActions                           │ │   │
│  │  │  • setError(), clearError()                                │ │   │
│  │  └────────────────────────────────────────────────────────────┘ │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                              │                                          │
│                              │ Usage                                    │
│                              ▼                                          │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                         React Components                        │   │
│  │  • ProgressBar, UploadZone, TranscriptDisplay, etc.            │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### Implementation Details

#### React Query Setup

```typescript
// src/lib/api/react-query-setup.ts
import { QueryClient, QueryCache } from '@tanstack/react-query';

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      // Time data stays fresh (progress updates via WebSocket)
      staleTime: 0,
      // Don't refetch on window focus (WebSocket handles updates)
      refetchOnWindowFocus: false,
      // Retry failed requests
      retry: (failureCount, error) => {
        // Don't retry 4xx errors
        if (error instanceof Error && error.message.includes('4')) {
          return false;
        }
        return failureCount < 3;
      },
      // Query key separator
      queryKeyHashFn: (queryKey) => JSON.stringify(queryKey),
    },
    mutations: {
      // Retry mutations
      retry: 1,
    },
  },
  // Global error handling
  queryCache: new QueryCache({
    onError: (error) => {
      console.error('Query error:', error);
      // Global error handler can dispatch to error context
    },
  }),
});

// Query key factory (type-safe query keys)
export const queryKeys = {
  tasks: {
    all: ['tasks'] as const,
    detail: (id: string) => ['tasks', id] as const,
    progress: (id: string) => ['tasks', id, 'progress'] as const,
  },
  transcripts: {
    all: ['transcripts'] as const,
    detail: (id: string) => ['transcripts', id] as const,
  },
  uploads: {
    all: ['uploads'] as const,
    detail: (id: string) => ['uploads', id] as const,
  },
  notifications: {
    all: ['notifications'] as const,
    history: () => ['notifications', 'history'] as const,
  },
};
```

#### Custom Hooks for Queries

```typescript
// src/lib/api/queries/use-task-progress.ts
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { queryKeys } from '../react-query-setup';
import { api } from '../api-client';

export function useTaskProgress(taskId: string) {
  const queryClient = useQueryClient();

  const query = useQuery({
    queryKey: queryKeys.tasks.progress(taskId),
    queryFn: () => api.getTaskProgress(taskId),
    // Disable auto-refetch (WebSocket updates)
    refetchInterval: false,
    // Keep data in cache longer
    gcTime: 5 * 60 * 1000, // 5 minutes
  });

  // Listen for WebSocket updates
  useEffect(() => {
    const unsubscribe = websocketManager.subscribe(
      `progress:${taskId}`,
      (update) => {
        // Optimistically update cache
        queryClient.setQueryData(
          queryKeys.tasks.progress(taskId),
          update
        );
      }
    );

    return unsubscribe;
  }, [taskId, queryClient]);

  return query;
}

// src/lib/api/queries/use-transcript.ts
export function useTranscript(taskId: string) {
  return useQuery({
    queryKey: queryKeys.transcripts.detail(taskId),
    queryFn: () => api.getTranscript(taskId),
    enabled: !!taskId,
    staleTime: 10 * 60 * 1000, // 10 minutes (transcript doesn't change)
  });
}

// src/lib/api/queries/use-notification-history.ts
export function useNotificationHistory(limit: number = 10) {
  return useQuery({
    queryKey: queryKeys.notifications.history(),
    queryFn: () => api.getNotificationHistory(limit),
    staleTime: 0, // Always refetch history
  });
}
```

#### Custom Hooks for Mutations

```typescript
// src/lib/api/mutations/use-upload-file.ts
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { queryKeys } from '../react-query-setup';
import { api } from '../api-client';

export function useUploadFile() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (file: File) => api.uploadFile(file),

    // Optimistic update
    onMutate: async (file) => {
      // Cancel ongoing refetches
      await queryClient.cancelQueries({ queryKey: queryKeys.uploads.all });

      // Snapshot previous value
      const previousUploads = queryClient.getQueryData(
        queryKeys.uploads.all
      );

      // Optimistically update
      queryClient.setQueryData(
        queryKeys.uploads.all,
        (old: any[]) => [...old, { id: 'temp', file, status: 'pending' }]
      );

      // Return context with previous value
      return { previousUploads };
    },

    // Rollback on error
    onError: (err, variables, context) => {
      if (context?.previousUploads) {
        queryClient.setQueryData(
          queryKeys.uploads.all,
          context.previousUploads
        );
      }
    },

    // Refetch after success
    onSuccess: (result) => {
      // Invalidate related queries
      queryClient.invalidateQueries({
        queryKey: queryKeys.tasks.detail(result.taskId)
      });
    },
  });
}

// src/lib/api/mutations/use-update-theme-preference.ts
export function useUpdateThemePreference() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (preferences: ThemePreferences) =>
      api.updateThemePreferences(preferences),

    onSuccess: (newPreferences) => {
      // Update theme context
      themeContext.setPreferences(newPreferences);

      // Invalidate preferences query
      queryClient.invalidateQueries({
        queryKey: ['preferences', 'theme']
      });
    },
  });
}
```

#### WebSocket Integration with React Query

```typescript
// src/lib/api/websocket-query-integration.ts
import { useQueryClient } from '@tanstack/react-query';
import { queryKeys } from './react-query-setup';
import { websocketManager } from './websocket-manager';

export function useWebSocketQueryIntegration(taskId: string) {
  const queryClient = useQueryClient();

  useEffect(() => {
    const unsubscribe = websocketManager.subscribe(taskId, (message) => {
      switch (message.type) {
        case 'progress_update':
          // Update progress cache
          queryClient.setQueryData(
            queryKeys.tasks.progress(taskId),
            message.payload
          );
          break;

        case 'stage_change':
          // Update progress with new stage
          queryClient.setQueryData(
            queryKeys.tasks.progress(taskId),
            (old: any) => ({
              ...old,
              stage: message.payload.toStage
            })
          );
          break;

        case 'complete':
          // Invalidate to trigger refetch of transcript
          queryClient.invalidateQueries({
            queryKey: queryKeys.transcripts.detail(taskId)
          });
          break;

        case 'error':
          // Set error state
          queryClient.setQueryData(
            queryKeys.tasks.progress(taskId),
            (old: any) => ({
              ...old,
              error: message.payload
            })
          );
          break;
      }
    });

    return unsubscribe;
  }, [taskId, queryClient]);
}
```

#### React Context for Client State

```typescript
// src/contexts/theme-context.tsx
import { createContext, useContext, useState, useCallback } from 'react';

interface ThemeContextValue {
  theme: 'light' | 'dark' | 'high-contrast';
  accentColor: string;
  setTheme: (theme: string) => void;
  setAccentColor: (color: string) => void;
  toggleHighContrast: () => void;
}

const ThemeContext = createContext<ThemeContextValue | null>(null);

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [theme, setThemeState] = useState(() => {
    // Load from localStorage or system preference
    const saved = localStorage.getItem('theme');
    if (saved) return saved;
    return window.matchMedia('(prefers-color-scheme: dark)').matches
      ? 'dark'
      : 'light';
  });

  const [accentColor, setAccentColorState] = useState(() =>
    localStorage.getItem('accentColor') || '#3B82F6'
  );

  const setTheme = useCallback((newTheme: string) => {
    setThemeState(newTheme);
    localStorage.setItem('theme', newTheme);
    document.documentElement.setAttribute('data-theme', newTheme);
  }, []);

  const setAccentColor = useCallback((color: string) => {
    setAccentColorState(color);
    localStorage.setItem('accentColor', color);
    document.documentElement.style.setProperty('--accent-color', color);
  }, []);

  const toggleHighContrast = useCallback(() => {
    setThemeState((prev) => {
      const newTheme = prev === 'high-contrast' ? 'dark' : 'high-contrast';
      localStorage.setItem('theme', newTheme);
      document.documentElement.setAttribute('data-theme', newTheme);
      return newTheme;
    });
  }, []);

  return (
    <ThemeContext.Provider
      value={{
        theme,
        accentColor,
        setTheme,
        setAccentColor,
        toggleHighContrast,
      }}
    >
      {children}
    </ThemeContext.Provider>
  );
}

export function useTheme() {
  const context = useContext(ThemeContext);
  if (!context) {
    throw new Error('useTheme must be used within ThemeProvider');
  }
  return context;
}
```

### Usage in Components

```typescript
// src/components/progress-bar.tsx
import { useTaskProgress } from '@/lib/api/queries/use-task-progress';
import { useWebSocketQueryIntegration } from '@/lib/api/websocket-query-integration';

export function ProgressBar({ taskId }: { taskId: string }) {
  // Get progress from React Query cache
  const { data: progress, isLoading, error } = useTaskProgress(taskId);

  // WebSocket integration updates cache automatically
  useWebSocketQueryIntegration(taskId);

  if (isLoading) return <div>Loading...</div>;
  if (error) return <div>Error loading progress</div>;

  return (
    <div className="progress-bar">
      <div className="progress-fill" style={{ width: `${progress?.percentage}%` }} />
      <span>{progress?.percentage}% - {progress?.stage}</span>
    </div>
  );
}
```

## Alternatives Considered

### Alternative 1: Redux + Redux Toolkit

**Description**: Centralized store with actions and reducers.

**Pros**:
- Predictable state updates
- Excellent dev tools
- Large ecosystem

**Cons**:
- Overkill for primarily server state
- More boilerplate
- Manual cache management
- Need Redux Query or RTK Query anyway

**Rejected because**: React Query handles server state better, less boilerplate.

### Alternative 2: Zustand

**Description**: Lightweight state management library.

**Pros**:
- Simple API
- No boilerplate
- TypeScript friendly

**Cons**:
- Still need to handle server state separately
- No built-in caching or deduplication
- Manual refetching logic

**Rejected because**: React Query's server state handling is superior.

### Alternative 3: Jotai

**Description**: Atomic state management (bottom-up).

**Pros**:
- Fine-grained reactivity
- Simple atoms
- Good TypeScript support

**Cons**:
- Different paradigm (may confuse team)
- Less mature than React Query for server state
- Still need complementary solution

**Rejected because**: React Query + Context is more straightforward.

### Alternative 4: Pure React Context + useState

**Description**: Use only built-in React state management.

**Pros**:
- No additional dependencies
- Simple to understand

**Cons**:
- Prop drilling or many contexts
- No caching
- Manual refetching
- Race conditions
- Stale data issues

**Rejected because**: Doesn't scale well for complex applications.

## Consequences

### Positive

1. **Automatic caching**: Reduces duplicate requests
2. **Background refetching**: Keeps data fresh automatically
3. **Optimistic updates**: Better perceived performance
4. **Type-safe**: Full TypeScript support
5. **Dev tools**: Excellent React Query DevTools
6. **Less boilerplate**: Compared to Redux
7. **WebSocket integration**: Clean pattern for real-time updates
8. **Suspense support**: Can use with React Suspense

### Negative

1. **Learning curve**: Team must learn React Query patterns
2. **Additional dependency**: Another library to maintain
3. **Bundle size**: ~13KB minzipped
4. **Over-engineering risk**: Might be overkill for simple queries
5. **Debugging complexity**: Cache behavior can be confusing

### Mitigations

1. Provide team training on React Query
2. Create custom hooks that encapsulate complexity
3. Document patterns and best practices
4. Use React Query DevTools in development
5. Start simple, add complexity as needed

## Implementation Roadmap

1. **Phase 1**: Setup React Query
   - Install dependencies
   - Configure QueryClient
   - Set up QueryClientProvider

2. **Phase 2**: Create query hooks
   - Implement useTaskProgress
   - Implement useTranscript
   - Implement other data-fetching hooks

3. **Phase 3**: Create mutation hooks
   - Implement useUploadFile
   - Implement useUpdatePreferences
   - Implement other update hooks

4. **Phase 4**: WebSocket integration
   - Connect WebSocket to Query cache updates
   - Test real-time updates

5. **Phase 5**: Context setup
   - Create ThemeContext
   - Create NotificationContext
   - Create ErrorContext

## References

- [TanStack Query Documentation](https://tanstack.com/query/latest)
- [React Query DevTools](https://tanstack.com/query/latest/docs/devtools)
- [React Query vs State Management Libraries](https://tkdodo.eu/blog/react-query-vs-state-management)

---

*End of ADR-002*
