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

### Current State Analysis

**Bundle Composition (estimated):**
- React + React DOM: ~150KB
- Material-UI: ~800KB
- React Router: ~50KB
- Audio Players: ~400KB
- RAG Components: ~600KB
- Other Libraries: ~500KB
- Application Code: ~500KB
- **Total: ~3MB (gzipped: ~800KB)**

**Performance Metrics (Current):**
| Metric | Value | Target |
|--------|-------|--------|
| Initial Bundle Size | 3MB | <500KB |
| First Contentful Paint (FCP) | 2.5s | <1.5s |
| Time to Interactive (TTI) | 5.2s | <3s |
| Largest Contentful Paint (LCP) | 3.8s | <2.5s |
| Total Blocking Time (TBT) | 800ms | <300ms |

---

## Decision

Implement route-based code splitting and component lazy loading using Vite.

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Entry Chunk (~150KB)                   │
│  - React core                                               │
│  - Router setup                                             │
│  - Loading skeletons                                        │
└───────────────────────────┬─────────────────────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        │                   │                   │
        ▼                   ▼                   ▼
┌───────────────┐   ┌───────────────┐   ┌───────────────┐
│  Transcripts  │   │  Transcript   │   │     RAG       │
│  Chunk        │   │  Detail Chunk │   │   Chunk       │
│  (~80KB)      │   │  (~120KB)     │   │  (~200KB)     │
└───────────────┘   └───────────────┘   └───────────────┘
        │                   │                   │
        └───────────────────┼───────────────────┘
                            ▼
        ┌───────────────────────────────────────────┐
        │          Shared Vendor Chunks             │
        │  - react-vendor (~150KB)                  │
        │  - ui-vendor (~400KB)                     │
        │  - utils (~50KB)                          │
        └───────────────────────────────────────────┘
```

---

## Implementation

### Route-Based Splitting

```typescript
// frontend/src/App.tsx
import { lazy, Suspense } from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { CircularProgress, Box } from '@mui/material';

// Lazy load routes
const TranscriptsPage = lazy(() => import('./pages/TranscriptsPage'));
const TranscriptDetailPage = lazy(() => import('./pages/TranscriptDetailPage'));
const RAGPage = lazy(() => import('./pages/RAGPage'));

// Loading fallback
const PageLoader = () => (
  <Box
    display="flex"
    justifyContent="center"
    alignItems="center"
    minHeight="100vh"
  >
    <CircularProgress />
  </Box>
);

function App() {
  return (
    <BrowserRouter>
      <Suspense fallback={<PageLoader />}>
        <Routes>
          <Route path="/" element={<TranscriptsPage />} />
          <Route path="/transcripts/:id" element={<TranscriptDetailPage />} />
          <Route path="/rag" element={<RAGPage />} />
        </Routes>
      </Suspense>
    </BrowserRouter>
  );
}

export default App;
```

### Component-Level Lazy Loading

```typescript
// frontend/src/components/LazyAudioPlayer.tsx
import { lazy, Suspense, useState } from 'react';
import { Button } from '@mui/material';

const AudioPlayer = lazy(() => import('./AudioPlayer'));

interface LazyAudioPlayerProps {
  src: string;
  transcriptId: string;
}

export function LazyAudioPlayer({ src, transcriptId }: LazyAudioPlayerProps) {
  const [shouldLoad, setShouldLoad] = useState(false);

  if (!shouldLoad) {
    return (
      <Button
        variant="contained"
        onClick={() => setShouldLoad(true)}
        fullWidth
      >
        Load Audio Player
      </Button>
    );
  }

  return (
    <Suspense fallback={<CircularProgress />}>
      <AudioPlayer src={src} transcriptId={transcriptId} />
    </Suspense>
  );
}
```

### Viewport-Based Loading

```typescript
// frontend/src/hooks/useIntersectionObserver.ts
export function useIntersectionObserver(
  ref: React.RefObject<Element>,
  options?: IntersectionObserverInit
) {
  const [isVisible, setIsVisible] = useState(false);

  useEffect(() => {
    const observer = new IntersectionObserver(([entry]) => {
      if (entry.isIntersecting) {
        setIsVisible(true);
        observer.disconnect();
      }
    }, options);

    if (ref.current) {
      observer.observe(ref.current);
    }

    return () => observer.disconnect();
  }, [ref, options]);

  return isVisible;
}

// Usage
const LazyRAGChat = () => {
  const ref = useRef<HTMLDivElement>(null);
  const isVisible = useIntersectionObserver(ref, { threshold: 0.1 });

  return (
    <div ref={ref} style={{ minHeight: '400px' }}>
      {isVisible ? (
        <Suspense fallback={<Skeleton />}>
          <RAGChat transcriptId={transcriptId} />
        </Suspense>
      ) : (
        <Skeleton variant="rectangular" height={400} />
      )}
    </div>
  );
};
```

### Vite Configuration

```typescript
// vite.config.ts
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { visualizer } from 'rollup-plugin-visualizer';

export default defineConfig({
  plugins: [
    react(),
    visualizer({
      open: true,
      gzipSize: true,
      brotliSize: true,
    }),
  ],
  build: {
    rollupOptions: {
      output: {
        manualChunks: (id) => {
          // Vendor chunks
          if (id.includes('node_modules')) {
            // React core
            if (id.includes('react') || id.includes('react-dom')) {
              return 'react-vendor';
            }
            // Router
            if (id.includes('react-router')) {
              return 'router-vendor';
            }
            // UI library
            if (id.includes('@mui')) {
              return 'ui-vendor';
            }
            // Other vendors
            return 'vendor';
          }

          // Application chunks
          if (id.includes('/pages/TranscriptsPage')) {
            return 'transcripts';
          }
          if (id.includes('/pages/TranscriptDetailPage')) {
            return 'transcript-detail';
          }
          if (id.includes('/pages/RAGPage')) {
            return 'rag';
          }
        },
      },
    },
    chunkSizeWarningLimit: 300,
    minify: 'terser',
    sourcemap: true,
  },
  server: {
    port: 3000,
  },
});
```

---

## Alternatives Considered

### 1. Single Bundle (Current)

**Pros:** Simple, no splitting overhead
**Cons:** 3MB initial load, slow TTI
**Decision:** Being replaced

### 2. Webpack Code Splitting

**Pros:** Industry standard, mature
**Cons:** Complex configuration, slower builds
**Decision:** Vite preferred for dev experience

### 3. Micro-frontends (Module Federation)

**Pros:** Independent deployments, tech stack flexibility
**Cons:** High complexity, overhead for small app
**Decision:** Overkill for current scale

### 4. Server-Side Rendering (Next.js)

**Pros:** SEO, faster FCP
**Cons:** Complex setup, server requirements
**Decision:** Not needed for internal tool

---

## Migration Path

### Phase 1: Enable Code Splitting (Week 1)

```bash
# Update dependencies
npm install --save-dev vite-plugin-visualizer

# Update vite.config.ts
# Add lazy loading to App.tsx
```

### Phase 2: Component Lazy Loading (Week 2)

```typescript
// Identify heavy components:
// - AudioPlayer (~200KB)
// - RAGChat (~300KB)
// - WaveformVisualizer (~150KB)

// Wrap with lazy()
// Add Suspense boundaries
```

### Phase 3: Performance Optimization (Week 3)

- Analyze bundle sizes
- Optimize chunk splitting
- Add preload hints
- Implement service worker caching

### Phase 4: Validation (Week 4)

```bash
# Run Lighthouse audits
npx lighthouse http://localhost:3000 --view

# Analyze bundle
npm run build -- --analyze
```

---

## Performance Targets

### Bundle Size Targets

| Chunk | Current | Target | Strategy |
|-------|---------|--------|----------|
| Entry | 3MB | <150KB | Route splitting |
| Vendor | 2.5MB | <600KB | Manual chunks |
| Transcripts | - | <100KB | Code splitting |
| Transcript Detail | - | <150KB | Lazy components |
| RAG | - | <250KB | Lazy load |

### Metrics Targets

| Metric | Current | Target | Improvement |
|--------|---------|--------|-------------|
| Initial Bundle | 3MB | <150KB | **95% reduction** |
| FCP | 2.5s | <1.5s | **40% faster** |
| TTI | 5.2s | <3s | **42% faster** |
| LCP | 3.8s | <2.5s | **34% faster** |
| TBT | 800ms | <300ms | **63% reduction** |

---

## Before/After Metrics

### Current Bundle (3MB single file)

```
Entry Point (3MB)
├── React Core (150KB)
├── Material-UI (800KB)
├── All Pages (1MB)
├── All Components (800KB)
└── Other (250KB)

Load Time: 5.2s (TTI)
First Paint: 2.5s
```

### After Optimization (Split chunks)

```
Entry Chunk (150KB)
├── React Core
├── Router Setup
└── Loading Skeletons

On-Demand Chunks:
├── transcripts (80KB) - loaded on home
├── transcript-detail (120KB) - loaded on detail
├── rag (200KB) - loaded on RAG page
├── react-vendor (150KB) - shared
├── ui-vendor (400KB) - shared
└── vendor (100KB) - shared

Load Time: 1.8s (TTI) - 65% faster
First Paint: 1.2s - 52% faster
```

---

## Consequences

### Positive

1. **Performance:** 65% faster TTI (5.2s → 1.8s)
2. **Bandwidth:** 95% smaller initial bundle (3MB → 150KB)
3. **UX:** Progressive loading, faster perception of speed
4. **Caching:** Better cache hit rates for vendor chunks
5. **SEO:** Improved Core Web Vitals scores

### Negative

1. **Complexity:** More complex build configuration
2. **Route Transitions:** Slight delay when loading new routes (~100-200ms)
3. **Development:** Need to handle Suspense boundaries
4. **Testing:** More test scenarios for loading states
5. **Bundle Management:** Need to monitor chunk sizes

### Mitigations

- Use skeleton screens during transitions
- Prefetch routes on hover/navigation
- Monitor bundle sizes in CI/CD
- Add integration tests for lazy routes
- Use React.SuspenseList for coordinated loading

---

## Rollback Strategy

### Feature Flag

```typescript
// frontend/src/config/features.ts
export const FEATURES = {
  CODE_SPLITTING: import.meta.env.VITE_ENABLE_CODE_SPLITTING !== 'false',
  LAZY_COMPONENTS: import.meta.env.VITE_ENABLE_LAZY_COMPONENTS === 'true',
};

// Conditional lazy loading
const TranscriptsPage = FEATURES.CODE_SPLITTING
  ? lazy(() => import('./pages/TranscriptsPage'))
  : () => import('./pages/TranscriptsPage');
```

### Rollback Steps

1. Disable feature flag: `VITE_ENABLE_CODE_SPLITTING=false`
2. Rebuild without splitting: `npm run build`
3. Deploy previous version
4. Monitor metrics

---

## Monitoring

### Bundle Size Monitoring

```javascript
// .github/workflows/bundle-size.yml
name: Bundle Size

on: [pull_request]

jobs:
  bundle-size:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - run: npm ci
      - run: npm run build
      - name: Check bundle size
        run: |
          ENTRY_SIZE=$(stat -f%z dist/assets/index-*.js 2>/dev/null || stat -c%s dist/assets/index-*.js)
          if [ $ENTRY_SIZE -gt 200000 ]; then
            echo "Entry chunk too large: $ENTRY_SIZE bytes"
            exit 1
          fi
```

### Runtime Monitoring

```typescript
// frontend/src/utils/performance.ts
export function reportWebVitals() {
  if (import.meta.env.PROD) {
    import('web-vitals').then(({ getCLS, getFID, getFCP, getLCP, getTTFB }) => {
      getCLS(console.log);
      getFID(console.log);
      getFCP(console.log);
      getLCP(console.log);
      getTTFB(console.log);
    });
  }
}
```

---

**Document Control**

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-02-03 | Performance Team | Initial ADR |
| 1.1 | 2026-02-03 | Performance Team | Added alternatives, metrics, migration path, expanded consequences |
