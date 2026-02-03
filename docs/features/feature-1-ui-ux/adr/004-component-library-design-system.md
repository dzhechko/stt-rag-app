# ADR-004: Component Library and Design System

| Status | Proposed by | Decision date | Effective date |
|--------|-------------|---------------|---------------|
| Accepted | System Architect | 2025-02-03 | 2025-02-03 |

---

## Context

The UI/UX improvements require many new UI components:
- Progress bars with stages
- Toast notifications
- File upload drag-drop zone
- Transcript display with timestamps
- Theme toggle
- Error states and retry options

Without a cohesive design system:
- Components look inconsistent
- Repeated styling code
- Hard to maintain visual consistency
- Difficult to implement dark mode
- Accessibility issues

## Decision

Implement a **headless UI component library** (Radix UI) with **custom styling** using CSS variables for theming.

### Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    Design System Architecture                          │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                    Application Layer                             │   │
│  │  ProgressBar, UploadZone, TranscriptDisplay, etc.               │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                              │                                          │
│                              │ Uses                                     │
│                              ▼                                          │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                    Component Library                             │   │
│  │  ┌────────────────────────────────────────────────────────────┐ │   │
│  │  │ Headless Primitives (Radix UI):                            │ │   │
│  │  │  • Dialog, Popover, Tooltip, Dropdown Menu                 │ │   │
│  │  │  • Tabs, Accordion, Switch, Slider                         │ │   │
│  │  │  • Progress (for simple progress bars)                     │ │   │
│  │  └────────────────────────────────────────────────────────────┘ │   │
│  │  ┌────────────────────────────────────────────────────────────┐ │   │
│  │  │ Custom Components:                                         │ │   │
│  │  │  • ProgressBar (staged, time estimate)                     │ │   │
│  │  │  • UploadZone (drag-drop)                                 │ │   │
│  │  │  • TranscriptDisplay (timestamps, speakers)                │ │   │
│  │  │  • Toast (notification)                                   │ │   │
│  │  │  • ErrorBoundary (error handling)                         │ │   │
│  │  └────────────────────────────────────────────────────────────┘ │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                              │                                          │
│                              │ Styled with                              │
│                              ▼                                          │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                    Design Tokens (CSS Variables)                 │   │
│  │  ┌────────────────────────────────────────────────────────────┐ │   │
│  │  │ Colors:                                                    │ │   │
│  │  │  • --color-primary, --color-success, --color-error         │ │   │
│  │  │  • --bg-primary, --bg-secondary, --bg-tertiary            │ │   │
│  │  │  • --text-primary, --text-secondary, --text-muted         │ │   │
│  │  └────────────────────────────────────────────────────────────┘ │   │
│  │  ┌────────────────────────────────────────────────────────────┐ │   │
│  │  │ Typography:                                               │ │   │
│  │  │  • --font-size-base, --font-size-sm, --font-size-lg        │ │   │
│  │  │  • --font-weight-normal, --font-weight-semibold           │ │   │
│  │  │  • --line-height-tight, --line-height-normal              │ │   │
│  │  └────────────────────────────────────────────────────────────┘ │   │
│  │  ┌────────────────────────────────────────────────────────────┐ │   │
│  │  │ Spacing:                                                  │ │   │
│  │  │  • --space-1, --space-2, --space-4, --space-8            │ │   │
│  │  │  • --radius-sm, --radius-md, --radius-lg                  │ │   │
│  │  └────────────────────────────────────────────────────────────┘ │   │
│  │  ┌────────────────────────────────────────────────────────────┐ │   │
│  │  │ Motion:                                                   │ │   │
│  │  │  • --duration-fast, --duration-normal, --duration-slow    │ │   │
│  │  │  • --easing-ease, --easing-ease-in-out                    │ │   │
│  │  └────────────────────────────────────────────────────────────┘ │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                              │                                          │
│                              │ Theme variants                           │
│                              ▼                                          │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                         Themes                                   │   │
│  │  • Light Theme (default)                                        │   │
│  │  • Dark Theme                                                   │   │
│  │  • High Contrast Theme                                          │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### Implementation Details

#### Design Tokens (CSS Variables)

```css
/* src/styles/tokens.css */

:root {
  /* ========== Colors ========== */

  /* Primary - Brand/Accent */
  --color-primary: 3B82F6;
  --color-primary-light: 60A5FA;
  --color-primary-dark: 2563EB;

  /* Semantic Colors */
  --color-success: 10B981;
  --color-success-light: 34D399;
  --color-warning: F59E0B;
  --color-warning-light: FBBF24;
  --color-error: EF4444;
  --color-error-light: F87171;
  --color-info: 6366F1;
  --color-info-light: 818CF8;

  /* Neutral Palette */
  --gray-50: F9FAFB;
  --gray-100: F3F4F6;
  --gray-200: E5E7EB;
  --gray-300: D1D5DB;
  --gray-400: 9CA3AF;
  --gray-500: 6B7280;
  --gray-600: 4B5563;
  --gray-700: 374151;
  --gray-800: 1F2937;
  --gray-900: 111827;

  /* ========== Typography ========== */

  /* Font Families */
  --font-family-base: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto,
                       "Helvetica Neue", Arial, sans-serif;
  --font-family-mono: ui-monospace, SFMono-Regular, "SF Mono", Monaco,
                      Consolas, monospace;

  /* Font Sizes */
  --font-size-xs: 0.75rem;     /* 12px */
  --font-size-sm: 0.875rem;    /* 14px */
  --font-size-base: 1rem;      /* 16px */
  --font-size-lg: 1.125rem;    /* 18px */
  --font-size-xl: 1.25rem;     /* 20px */
  --font-size-2xl: 1.5rem;     /* 24px */
  --font-size-3xl: 1.875rem;   /* 30px */
  --font-size-4xl: 2.25rem;    /* 36px */

  /* Font Weights */
  --font-weight-normal: 400;
  --font-weight-medium: 500;
  --font-weight-semibold: 600;
  --font-weight-bold: 700;

  /* Line Heights */
  --line-height-tight: 1.25;
  --line-height-normal: 1.5;
  --line-height-relaxed: 1.75;

  /* ========== Spacing ========== */

  /* Base unit: 4px */
  --space-0: 0;
  --space-1: 0.25rem;   /* 4px */
  --space-2: 0.5rem;    /* 8px */
  --space-3: 0.75rem;   /* 12px */
  --space-4: 1rem;      /* 16px */
  --space-5: 1.25rem;   /* 20px */
  --space-6: 1.5rem;    /* 24px */
  --space-8: 2rem;      /* 32px */
  --space-10: 2.5rem;   /* 40px */
  --space-12: 3rem;     /* 48px */
  --space-16: 4rem;     /* 64px */

  /* Border Radius */
  --radius-none: 0;
  --radius-sm: 0.25rem;   /* 4px */
  --radius-md: 0.375rem;  /* 6px */
  --radius-lg: 0.5rem;    /* 8px */
  --radius-xl: 0.75rem;   /* 12px */
  --radius-2xl: 1rem;     /* 16px */
  --radius-full: 9999px;

  /* ========== Motion ========== */

  /* Durations */
  --duration-instant: 150ms;
  --duration-fast: 200ms;
  --duration-normal: 300ms;
  --duration-slow: 500ms;
  --duration-slower: 700ms;

  /* Easing Functions */
  --easing-linear: linear;
  --easing-ease: ease;
  --easing-ease-in: cubic-bezier(0.4, 0, 1, 1);
  --easing-ease-out: cubic-bezier(0, 0, 0.2, 1);
  --easing-ease-in-out: cubic-bezier(0.4, 0, 0.2, 1);

  /* ========== Shadows ========== */

  --shadow-xs: 0 1px 2px 0 rgba(0, 0, 0, 0.05);
  --shadow-sm: 0 1px 3px 0 rgba(0, 0, 0, 0.1), 0 1px 2px 0 rgba(0, 0, 0, 0.06);
  --shadow-md: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
  --shadow-lg: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05);
  --shadow-xl: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04);

  /* ========== Z-Index ========== */

  --z-index-dropdown: 1000;
  --z-index-sticky: 1020;
  --z-index-fixed: 1030;
  --z-index-modal-backdrop: 1040;
  --z-index-modal: 1050;
  --z-index-popover: 1060;
  --z-index-tooltip: 1070;
  --z-index-toast: 1080;
}

/* ========== Theme Variants ========== */

/* Light Theme (default) */
:root,
[data-theme="light"] {
  --bg-primary: #FFFFFF;
  --bg-secondary: var(--gray-50);
  --bg-tertiary: var(--gray-100);
  --bg-hover: var(--gray-100);
  --bg-active: var(--gray-200);

  --text-primary: var(--gray-900);
  --text-secondary: var(--gray-700);
  --text-muted: var(--gray-500);
  --text-inverse: #FFFFFF;

  --border-color: var(--gray-200);
  --border-color-hover: var(--gray-300);

  --shadow-color: rgba(0, 0, 0, 0.1);
}

/* Dark Theme */
[data-theme="dark"] {
  --bg-primary: #111827;
  --bg-secondary: #1F2937;
  --bg-tertiary: #374151;
  --bg-hover: #374151;
  --bg-active: #4B5563;

  --text-primary: #F9FAFB;
  --text-secondary: #D1D5DB;
  --text-muted: #9CA3AF;
  --text-inverse: #111827;

  --border-color: #374151;
  --border-color-hover: #4B5563;

  --shadow-color: rgba(0, 0, 0, 0.3);
}

/* High Contrast Theme */
[data-theme="high-contrast"] {
  --bg-primary: #000000;
  --bg-secondary: #000000;
  --bg-tertiary: #000000;
  --bg-hover: #1a1a1a;
  --bg-active: #333333;

  --text-primary: #FFFFFF;
  --text-secondary: #FFFFFF;
  --text-muted: #FFFF00;
  --text-inverse: #000000;

  --border-color: #FFFFFF;
  --border-color-hover: #FFFFFF;

  --shadow-color: transparent;
}
```

#### Component Structure

```
src/components/
├── ui/                    # Base UI components (headless + styling)
│   ├── button/
│   │   ├── button.tsx
│   │   ├── button.test.tsx
│   │   └── button.stories.tsx
│   ├── input/
│   ├── dropdown/
│   └── ...
├── progress/              # Feature-specific components
│   ├── progress-bar/
│   │   ├── progress-bar.tsx
│   │   ├── progress-bar.test.tsx
│   │   ├── progress-bar.stories.tsx
│   │   └── types.ts
│   ├── stage-indicator/
│   ├── time-estimate/
│   └── index.ts
├── upload/
│   ├── upload-zone/
│   ├── file-preview/
│   └── index.ts
├── transcript/
│   ├── transcript-display/
│   ├── timestamp-link/
│   └── index.ts
└── lib/                   # Component utilities
    ├── compound-patterns.ts
    ├── forwarded-refs.ts
    └──.ts
```

#### ProgressBar Component Example

```typescript
// src/components/progress/progress-bar/progress-bar.tsx
import * as React from "react";
import * as ProgressPrimitive from "@radix-ui/react-progress";
import { cn } from "@/lib/utils/cn";

interface ProgressBarProps extends React.ComponentProps<typeof ProgressPrimitive.Root> {
  percentage: number;
  size?: "sm" | "md" | "lg";
  showLabel?: boolean;
  label?: string;
  variant?: "default" | "success" | "warning" | "error";
}

export const ProgressBar = React.forwardRef<
  React.ElementRef<typeof ProgressPrimitive.Root>,
  ProgressBarProps
>(
  (
    {
      percentage,
      size = "md",
      showLabel = true,
      label,
      variant = "default",
      className,
      ...props
    },
    ref
  ) => {
    const clampedPercentage = Math.min(100, Math.max(0, percentage));

    return (
      <div className="progress-bar-container">
        {(showLabel || label) && (
          <div className="progress-bar-label">
            {label ?? `${clampedPercentage}%`}
          </div>
        )}

        <ProgressPrimitive.Root
          ref={ref}
          className={cn(
            "progress-bar",
            `progress-bar--${size}`,
            `progress-bar--${variant}`,
            className
          )}
          value={clampedPercentage}
          {...props}
        >
          <ProgressPrimitive.Indicator
            className="progress-bar__indicator"
            style={{ transform: `translateX(-${100 - clampedPercentage}%)` }}
          />
        </ProgressPrimitive.Root>
      </div>
    );
  }
);

ProgressBar.displayName = "ProgressBar";
```

```css
/* src/components/progress/progress-bar/progress-bar.css */
.progress-bar-container {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.progress-bar-label {
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-medium);
  color: var(--text-secondary);
}

.progress-bar {
  position: relative;
  overflow: hidden;
  background: var(--bg-tertiary);
  border-radius: var(--radius-full);
  width: 100%;
}

.progress-bar--sm {
  height: var(--space-2);
}

.progress-bar--md {
  height: var(--space-3);
}

.progress-bar--lg {
  height: var(--space-4);
}

.progress-bar__indicator {
  height: 100%;
  width: 100%;
  background: var(--color-primary);
  border-radius: var(--radius-full);
  transition: transform var(--duration-normal) var(--easing-ease-out);
}

.progress-bar--success .progress-bar__indicator {
  background: var(--color-success);
}

.progress-bar--warning .progress-bar__indicator {
  background: var(--color-warning);
}

.progress-bar--error .progress-bar__indicator {
  background: var(--color-error);
}

/* Animated stripes for progress */
.progress-bar--animated .progress-bar__indicator {
  background-image: linear-gradient(
    45deg,
    rgba(255, 255, 255, 0.15) 25%,
    transparent 25%,
    transparent 50%,
    rgba(255, 255, 255, 0.15) 50%,
    rgba(255, 255, 255, 0.15) 75%,
    transparent 75%,
    transparent
  );
  background-size: 1rem 1rem;
  animation: progress-stripes 1s linear infinite;
}

@keyframes progress-stripes {
  from {
    background-position: 1rem 0;
  }
  to {
    background-position: 0 0;
  }
}
```

## Alternatives Considered

### Alternative 1: Full Component Library (MUI, Chakra)

**Description**: Use a comprehensive component library with pre-styled components.

**Pros**:
- Quick to start
- Consistent design
- Good documentation

**Cons**:
- Heavy bundle size
- Harder to customize
- Tight coupling to library
- May not match brand

**Rejected because**: Bundle size and customization are important.

### Alternative 2: Tailwind CSS Only

**Description**: Use Tailwind utility classes without component library.

**Pros**:
- Highly flexible
- Small bundle (purge unused)
- Fast development

**Cons**:
- Inconsistent styles
- Repetitive class names
- Harder to maintain
- No pre-built components

**Rejected because**: Need consistent component library.

### Alternative 3: Custom Everything

**Description**: Build all components from scratch, including headless primitives.

**Pros**:
- Full control
- No dependencies

**Cons**:
- Re-inventing the wheel
- Accessibility burden on us
- Maintenance burden
- More code to test

**Rejected because**: Leverage proven solutions for headless primitives.

## Consequences

### Positive

1. **Accessibility**: Radix UI handles ARIA, keyboard, focus management
2. **Theming**: CSS variables make dark mode easy
3. **Bundle size**: Tree-shakeable, smaller than full libraries
4. **Customization**: Full control over styling
5. **Consistency**: Design tokens ensure visual consistency
6. **TypeScript**: First-class TS support

### Negative

1. **Learning curve**: Team learns Radix UI patterns
2. **Setup time**: Initial design token setup required
3. **Maintenance**: Maintain custom component styles
4. **Documentation**: Need to document custom components
5. **Stories overhead**: Storybook setup and maintenance

### Mitigations

1. Provide component documentation and examples
2. Create Storybook for visual documentation
3. Use strict TypeScript for safety
4. Automated testing for accessibility
5. Design system documentation site

## Implementation Roadmap

1. **Phase 1**: Design tokens
   - Define CSS variables
   - Create theme variants
   - Document tokens

2. **Phase 2**: Base components
   - Button, Input, Dropdown
   - Card, Badge, Avatar
   - Dialog, Popover, Tooltip

3. **Phase 3**: Feature components
   - ProgressBar with stages
   - UploadZone with drag-drop
   - TranscriptDisplay
   - Toast notification

4. **Phase 4**: Documentation
   - Storybook setup
   - Component documentation
   - Design system site

## References

- [Radix UI](https://www.radix-ui.com/)
- [Tailwind CSS](https://tailwindcss.com/)
- [Design Tokens](https://css-tricks.com/what-are-design-tokens/)
- [Storybook](https://storybook.js.org/)

---

*End of ADR-004*
