/**
 * React Testing Library utilities and custom render functions
 *
 * This module provides reusable testing utilities, custom render functions,
 * mock data generators, and helper functions for testing React components.
 *
 * @module tests/utils/test-utils
 */

import React from 'react'
import { render, RenderOptions } from '@testing-library/react'
import { MemoryRouter, Routes, Route } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { vi } from 'vitest'

// =============================================================================
// Mock Data Generators
// =============================================================================

/**
 * Generate a random ID
 * @returns {string} Random ID string
 */
export const generateId = () => `mock-${Math.random().toString(36).substr(2, 9)}`

/**
 * Generate a random timestamp
 * @param {number} daysBack - Number of days back from now
 * @returns {string} ISO timestamp
 */
export const generateTimestamp = (daysBack = 0) => {
  const date = new Date()
  date.setDate(date.getDate() - daysBack)
  return date.toISOString()
}

/**
 * Create a mock transcript object
 * @param {Object} overrides - Properties to override
 * @returns {Object} Mock transcript
 */
export const createMockTranscript = (overrides = {}) => ({
  id: generateId(),
  original_filename: 'test-audio.mp3',
  file_path: '/uploads/test-audio.mp3',
  file_size: 1024000,
  duration_seconds: 120.5,
  language: 'en',
  status: 'completed',
  transcription_text: 'This is a test transcription.',
  transcription_json: {
    language: 'english',
    duration: 120.5,
    words: [
      { word: 'This', start: 0.0, end: 0.3 },
      { word: 'is', start: 0.3, end: 0.5 },
      { word: 'a', start: 0.5, end: 0.6 },
      { word: 'test', start: 0.6, end: 0.9 }
    ],
    segments: [
      { start: 0, end: 1, text: 'This is a test' }
    ]
  },
  transcription_srt: '1\n00:00:00,000 --> 00:00:01,000\nThis is a test',
  created_at: generateTimestamp(),
  updated_at: generateTimestamp(),
  tags: ['test', 'sample'],
  category: 'meeting',
  extra_metadata: {},
  ...overrides
})

/**
 * Create multiple mock transcripts
 * @param {number} count - Number of transcripts to create
 * @param {Object} overrides - Properties to override in each
 * @returns {Array} Array of mock transcripts
 */
export const createMockTranscripts = (count = 5, overrides = {}) =>
  Array.from({ length: count }, (_, i) =>
    createMockTranscript({
      original_filename: `test-audio-${i}.mp3`,
      ...overrides
    })
  )

/**
 * Create a mock summary object
 * @param {Object} overrides - Properties to override
 * @returns {Object} Mock summary
 */
export const createMockSummary = (overrides = {}) => ({
  id: generateId(),
  transcript_id: generateId(),
  summary_text: 'This is a mock summary of the transcript.',
  summary_template: 'meeting',
  summary_config: {
    participants: true,
    decisions: true,
    deadlines: false,
    topics: true
  },
  model_used: 'GigaChat-2-Max',
  created_at: generateTimestamp(),
  updated_at: generateTimestamp(),
  ...overrides
})

/**
 * Create a mock processing job
 * @param {Object} overrides - Properties to override
 * @returns {Object} Mock processing job
 */
export const createMockJob = (overrides = {}) => ({
  id: generateId(),
  transcript_id: generateId(),
  job_type: 'transcription',
  status: 'completed',
  progress: 1.0,
  error_message: null,
  retry_count: 0,
  created_at: generateTimestamp(),
  updated_at: generateTimestamp(),
  ...overrides
})

/**
 * Create a mock RAG session
 * @param {Object} overrides - Properties to override
 * @returns {Object} Mock RAG session
 */
export const createMockRAGSession = (overrides = {}) => ({
  id: generateId(),
  session_name: 'Test Session',
  transcript_ids: [generateId(), generateId()],
  created_at: generateTimestamp(),
  updated_at: generateTimestamp(),
  ...overrides
})

/**
 * Create a mock RAG message
 * @param {Object} overrides - Properties to override
 * @returns {Object} Mock RAG message
 */
export const createMockRAGMessage = (overrides = {}) => ({
  id: generateId(),
  session_id: generateId(),
  question: 'What was discussed in the meeting?',
  answer: 'The meeting discussed various topics including project planning.',
  quality_score: 0.85,
  retrieved_documents: [
    {
      content: 'Sample document content',
      score: 0.95,
      transcript_id: generateId()
    }
  ],
  created_at: generateTimestamp(),
  ...overrides
})

/**
 * Create a mock file object
 * @param {string} filename - Filename
 * @param {number} size - File size in bytes
 * @param {string} type - MIME type
 * @returns {File} Mock file object
 */
export const createMockFile = (
  filename = 'test.mp3',
  size = 1024000,
  type = 'audio/mp3'
) => {
  const file = new File(['mock content'], filename, { type })
  Object.defineProperty(file, 'size', { value: size })
  Object.defineProperty(file, 'name', { value: filename })
  return file
}

/**
 * Create mock files for testing upload scenarios
 * @param {Array<{filename: string, size: number, type: string}>} specs - File specifications
 * @returns {Array<File>} Array of mock files
 */
export const createMockFiles = (specs = []) =>
  specs.map(spec => createMockFile(spec.filename, spec.size, spec.type))

/**
 * Create a mock progress event
 * @param {number} loaded - Bytes loaded
 * @param {number} total - Total bytes
 * @returns {Object} Progress event object
 */
export const createMockProgressEvent = (loaded = 50, total = 100) => ({
  loaded,
  total,
  lengthComputable: true
})

/**
 * Create a mock FormData object
 * @returns {Object} Mock FormData
 */
export const createMockFormData = () => {
  const data = {}
  return {
    append: vi.fn((key, value) => {
      data[key] = value
    }),
    get: vi.fn(key => data[key]),
    getAll: vi.fn(key => (Array.isArray(data[key]) ? data[key] : [data[key]])),
    has: vi.fn(key => key in data),
    delete: vi.fn(key => {
      delete data[key]
    }),
    _data: data // For testing purposes
  }
}

// =============================================================================
// Custom Render Functions
// =============================================================================

/**
 * Create a test QueryClient with sensible defaults
 * @param {Object} options - QueryClient options
 * @returns {QueryClient} Configured QueryClient
 */
export const createTestQueryClient = (options = {}) =>
  new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        gcTime: 0,
        staleTime: Infinity,
        ...options.queries
      },
      mutations: {
        retry: false,
        ...options.mutations
      }
    },
    logger: {
      log: console.log,
      warn: console.warn,
      error: () => {}, // Suppress error logging in tests
    }
  })

/**
 * Custom render function with providers
 * @param {React.ReactNode} ui - Component to render
 * @param {Object} options - Render options
 * @returns {import('@testing-library/react').RenderResult} Render result
 */
export function renderWithProviders(
  ui,
  {
    route = '/',
    queryClient = createTestQueryClient(),
    routerOptions = {},
    ...renderOptions
  } = {}
) {
  function Wrapper({ children }) {
    return (
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={[route]} {...routerOptions}>
          {children}
        </MemoryRouter>
      </QueryClientProvider>
    )
  }

  return render(ui, { wrapper: Wrapper, ...renderOptions })
}

/**
 * Render with a specific route
 * @param {React.ReactNode} ui - Component to render
 * @param {string} path - Route path
 * @param {string} initialRoute - Initial route entry
 * @param {Object} options - Additional render options
 * @returns {import('@testing-library/react').RenderResult} Render result
 */
export function renderWithRoute(
  ui,
  path = '/',
  initialRoute = '/',
  options = {}
) {
  const queryClient = createTestQueryClient()

  function Wrapper({ children }) {
    return (
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={[initialRoute]}>
          <Routes>
            <Route path={path} element={children} />
          </Routes>
        </MemoryRouter>
      </QueryClientProvider>
    )
  }

  return render(ui, { wrapper: Wrapper, ...options })
}

/**
 * Render with authentication context
 * @param {React.ReactNode} ui - Component to render
 * @param {Object} user - Mock user object
 * @param {Object} options - Additional render options
 * @returns {import('@testing-library/react').RenderResult} Render result
 */
export function renderWithAuth(
  ui,
  user = { id: 'test-user', name: 'Test User', email: 'test@example.com' },
  options = {}
) {
  // If you have an AuthProvider, wrap it here
  return renderWithProviders(ui, {
    ...options,
    // Add auth context mock here if needed
  })
}

// =============================================================================
// Async Utilities
// =============================================================================

/**
 * Wait for a specified number of milliseconds
 * @param {number} ms - Milliseconds to wait
 * @returns {Promise<void>}
 */
export const wait = ms => new Promise(resolve => setTimeout(resolve, ms))

/**
 * Wait for the next tick
 * @returns {Promise<void>}
 */
export const tick = () => new Promise(resolve => setTimeout(resolve, 0))

/**
 * Wait for all pending promises to resolve
 * @returns {Promise<void>}
 */
export const flushPromises = () => new Promise(resolve => setImmediate(resolve))

/**
 * Wait for element to appear in DOM
 * @param {Function} callback - Callback that returns the element
 * @param {Object} options - Options
 * @returns {Promise<Element>}
 */
export const waitForElement = async (
  callback,
  { timeout = 1000, interval = 50 } = {}
) => {
  const startTime = Date.now()

  while (Date.now() - startTime < timeout) {
    try {
      const element = await callback()
      if (element) {
        return element
      }
    } catch (e) {
      // Continue waiting
    }
    await wait(interval)
  }

  throw new Error(`Element not found within ${timeout}ms`)
}

// =============================================================================
// Mock Data Sets
// =============================================================================

/**
 * Pre-configured mock data for common scenarios
 */
export const mockData = {
  transcript: createMockTranscript(),
  transcripts: createMockTranscripts(10),
  summary: createMockSummary(),
  job: createMockJob(),
  ragSession: createMockRAGSession(),
  ragMessage: createMockRAGMessage(),

  // Status variations
  pendingTranscript: createMockTranscript({ status: 'pending' }),
  processingTranscript: createMockTranscript({ status: 'processing' }),
  failedTranscript: createMockTranscript({ status: 'failed' }),

  // Language variations
  englishTranscript: createMockTranscript({ language: 'en' }),
  russianTranscript: createMockTranscript({ language: 'ru' }),
  spanishTranscript: createMockTranscript({ language: 'es' }),

  // Category variations
  meetingTranscript: createMockTranscript({ category: 'meeting' }),
  interviewTranscript: createMockTranscript({ category: 'interview' }),
  lectureTranscript: createMockTranscript({ category: 'lecture' }),
}

// =============================================================================
// API Response Mocks
// =============================================================================

/**
 * Create a mock successful API response
 * @param {any} data - Response data
 * @param {Object} options - Additional response options
 * @returns {Object} Mock response object
 */
export const createMockResponse = (data, options = {}) => ({
  ok: true,
  status: 200,
  statusText: 'OK',
  data,
  headers: new Headers(),
  json: async () => data,
  text: async () => JSON.stringify(data),
  ...options
})

/**
 * Create a mock error response
 * @param {number} status - HTTP status code
 * @param {string} message - Error message
 * @returns {Object} Mock error response
 */
export const createMockErrorResponse = (status = 500, message = 'Internal Server Error') => ({
  ok: false,
  status,
  statusText: message,
  data: { error: message },
  json: async () => ({ error: message }),
  text: async () => message,
})

// =============================================================================
// Event Mocking Utilities
// =============================================================================

/**
 * Create a mock change event
 * @param {any} value - Event value
 * @returns {Object} Change event object
 */
export const createMockChangeEvent = value => ({
  target: { value },
  preventDefault: vi.fn(),
  stopPropagation: vi.fn()
})

/**
 * Create a mock submit event
 * @returns {Object} Submit event object
 */
export const createMockSubmitEvent = () => ({
  preventDefault: vi.fn(),
  stopPropagation: vi.fn(),
  currentTarget: {
    checkValidity: vi.fn(() => true),
    reportValidity: vi.fn()
  }
})

/**
 * Create a mock drag event
 * @param {Array<File>} files - Files being dragged
 * @returns {Object} Drag event object
 */
export const createMockDragEvent = files => ({
  preventDefault: vi.fn(),
  stopPropagation: vi.fn(),
  dataTransfer: {
    files,
    items: Array.from(files).map(file => ({
      kind: 'file',
      getAsFile: () => file
    }))
  }
})

/**
 * Create a mock keyboard event
 * @param {string} key - Key pressed
 * @param {Object} modifiers - Modifier keys (ctrl, shift, alt, meta)
 * @returns {Object} Keyboard event object
 */
export const createMockKeyboardEvent = (key, modifiers = {}) => ({
  key,
  code: key,
  keyCode: key.charCodeAt(0),
  which: key.charCodeAt(0),
  ctrlKey: modifiers.ctrl || false,
  shiftKey: modifiers.shift || false,
  altKey: modifiers.alt || false,
  metaKey: modifiers.meta || false,
  preventDefault: vi.fn(),
  stopPropagation: vi.fn()
})

// =============================================================================
// Component Testing Helpers
// =============================================================================

/**
 * Test that a component renders without errors
 * @param {React.ReactNode} component - Component to test
 * @param {Object} options - Render options
 * @returns {import('@testing-library/react').RenderResult} Render result
 */
export const testRender = (component, options = {}) => {
  const renderResult = renderWithProviders(component, options)

  expect(renderResult.container).toBeInTheDocument()

  return renderResult
}

/**
 * Test that a component matches snapshot
 * @param {React.ReactNode} component - Component to test
 * @param {Object} options - Render options
 */
export const testSnapshot = (component, options = {}) => {
  const renderResult = renderWithProviders(component, options)
  expect(renderResult.container).toMatchSnapshot()
}

/**
 * Get a data-testid attribute selector
 * @param {string} id - Test ID value
 * @returns {string} Selector string
 */
export const byTestId = id => `[data-testid="${id}"]`

/**
 * Get a role selector
 * @param {string} role - Role value
 * @returns {string} Selector string (for getByRole)
 */
export const byRole = role => role

// =============================================================================
// Re-exports from React Testing Library
// =============================================================================

export * from '@testing-library/react'
export { default as userEvent } from '@testing-library/user-event'
