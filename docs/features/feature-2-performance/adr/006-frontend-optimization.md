# ADR-006: Frontend Code Splitting and Lazy Loading

**Status:** Accepted
**Date:** 2026-02-03
**Context:** Performance Optimization Feature

---

## Context

The STT application frontend currently bundles all JavaScript into a single large file (~3MB), causing:
1. Slow initial page load (>5 seconds)
2. Poor Time to Interactive (TTI)
3. Wasted bandwidth for unused features
4. No progressive loading

---

## Decision

Implement route-based code splitting and component lazy loading using Vite.

### Route-Based Splitting

```typescript
// frontend/src/App.tsx
import { lazy, Suspense } from 'react';

// Lazy load routes
const TranscriptsPage = lazy(() => import('./pages/TranscriptsPage'));
const TranscriptDetailPage = lazy(() => import('./pages/TranscriptDetailPage'));
const RAGPage = lazy(() => import('./pages/RAGPage'));

function App() {
  return (
    <Suspense fallback={<LoadingSpinner />}>
      <Routes>
        <Route path="/" element={<TranscriptsPage />} />
        <Route path="/transcripts/:id" element={<TranscriptDetailPage />} />
        <Route path="/rag" element={<RAGPage />} />
      </Routes>
    </Suspense>
  );
}
```

### Lazy Loading Components

```typescript
// Lazy load heavy components
const AudioPlayer = lazy(() => import('./components/AudioPlayer'));
const RAGChat = lazy(() => import('./components/RAGChat'));

function TranscriptDetailPage() {
  return (
    <div>
      <h1>Transcript</h1>

      {/* Lazy load audio player when in viewport */}
      <ViewportObserver>
        <AudioPlayer src={audioUrl} />
      </ViewportObserver>

      {/* Lazy load RAG chat */}
      <Suspense fallback={<button>Load Chat</button>}>
        <RAGChat transcriptId={id} />
      </Suspense>
    </div>
  );
}
```

### Vite Configuration

```javascript
// vite.config.ts
export default defineConfig({
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          // Vendor chunk
          'react-vendor': ['react', 'react-dom', 'react-router-dom'],
          // UI library
          'ui-vendor': ['@mui/material', '@emotion/react', '@emotion/styled'],
        }
      }
    },
    chunkSizeWarningLimit: 500
  }
});
```

---

## Consequences

**Positive:**
- Initial bundle <500KB (6x reduction)
- TTI <3 seconds
- Progressive loading

**Negative:**
- Slight delay when loading new routes
- More complex build configuration

---

**Document Control**

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-02-03 | Performance Team | Initial ADR |
