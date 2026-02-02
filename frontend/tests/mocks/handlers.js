/**
 * MSW (Mock Service Worker) API handlers
 *
 * This module provides comprehensive API request/response mocks for testing.
 * All handlers are configurable and can be easily overridden for specific test scenarios.
 *
 * @module tests/mocks/handlers
 */

import { http, HttpResponse, delay } from 'msw'

// =============================================================================
// Base URL Configuration
// =============================================================================

const API_BASE = '/api'

// =============================================================================
// Mock Data Generators
// =============================================================================

const generateId = () => `mock-${Math.random().toString(36).substr(2, 9)}`

const createTranscript = (overrides = {}) => ({
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
    ],
    segments: []
  },
  transcription_srt: '1\n00:00:00,000 --> 00:00:01,000\nThis is a test',
  created_at: new Date().toISOString(),
  updated_at: new Date().toISOString(),
  tags: ['test'],
  category: 'meeting',
  extra_metadata: {},
  ...overrides
})

const createSummary = (overrides = {}) => ({
  id: generateId(),
  transcript_id: generateId(),
  summary_text: 'This is a mock summary.',
  summary_template: 'meeting',
  summary_config: { participants: true, decisions: true },
  model_used: 'GigaChat-2-Max',
  created_at: new Date().toISOString(),
  updated_at: new Date().toISOString(),
  ...overrides
})

const createRAGSession = (overrides = {}) => ({
  id: generateId(),
  session_name: 'Test Session',
  transcript_ids: [generateId()],
  created_at: new Date().toISOString(),
  updated_at: new Date().toISOString(),
  ...overrides
})

// =============================================================================
// Transcript Handlers
// =============================================================================

/**
 * GET /api/transcripts - List all transcripts
 */
export const getTranscriptsHandler = http.get(`${API_BASE}/transcripts`, async ({ request }) => {
  const url = new URL(request.url)
  const skip = parseInt(url.searchParams.get('skip') || '0')
  const limit = parseInt(url.searchParams.get('limit') || '100')
  const status = url.searchParams.get('status')
  const language = url.searchParams.get('language')
  const search = url.searchParams.get('search')

  // Simulate network delay
  await delay(100)

  // Generate mock transcripts
  const transcripts = Array.from({ length: 10 }, (_, i) =>
    createTranscript({
      original_filename: `meeting-${i + 1}.mp3`,
      status: status || ['pending', 'processing', 'completed', 'failed'][i % 4],
      language: language || ['en', 'ru'][i % 2]
    })
  )

  // Filter by search term
  let filtered = transcripts
  if (search) {
    filtered = transcripts.filter(t =>
      t.original_filename.toLowerCase().includes(search.toLowerCase()) ||
      (t.transcription_text && t.transcription_text.toLowerCase().includes(search.toLowerCase()))
    )
  }

  // Apply pagination
  const paginated = filtered.slice(skip, skip + limit)

  return HttpResponse.json({
    transcripts: paginated,
    total: filtered.length,
    skip,
    limit
  })
})

/**
 * GET /api/transcripts/:id - Get transcript by ID
 */
export const getTranscriptHandler = http.get(`${API_BASE}/transcripts/:id`, async ({ params }) => {
  await delay(50)

  return HttpResponse.json(
    createTranscript({
      id: params.id,
      original_filename: 'meeting.mp3',
      status: 'completed'
    })
  )
})

/**
 * POST /api/transcripts/upload - Upload transcript
 */
export const uploadTranscriptHandler = http.post(`${API_BASE}/transcripts/upload`, async ({ request }) => {
  await delay(200)

  // In a real scenario, we'd parse FormData here
  // For testing, we'll just return a mock response

  return HttpResponse.json(
    createTranscript({
      status: 'pending',
      transcription_text: null
    }),
    { status: 201 }
  )
})

/**
 * DELETE /api/transcripts/:id - Delete transcript
 */
export const deleteTranscriptHandler = http.delete(`${API_BASE}/transcripts/:id`, async () => {
  await delay(100)

  return new HttpResponse(null, { status: 204 })
})

/**
 * PUT /api/transcripts/:id - Update transcript
 */
export const updateTranscriptHandler = http.put(`${API_BASE}/transcripts/:id`, async ({ params, request }) => {
  await delay(100)

  const body = await request.json()

  return HttpResponse.json(
    createTranscript({
      id: params.id,
      ...body
    })
  )
})

// =============================================================================
// Summary Handlers
// =============================================================================

/**
 * POST /api/transcripts/:id/summarize - Create summary
 */
export const createSummaryHandler = http.post(`${API_BASE}/transcripts/:id/summarize`, async ({ params, request }) => {
  await delay(500) // Summarization takes longer

  const body = await request.json()

  return HttpResponse.json(
    createSummary({
      transcript_id: params.id,
      template: body.template,
      model_used: body.model || 'GigaChat-2-Max'
    }),
    { status: 201 }
  )
})

/**
 * GET /api/transcripts/:id/summaries - Get transcript summaries
 */
export const getSummariesHandler = http.get(`${API_BASE}/transcripts/:id/summaries`, async ({ params }) => {
  await delay(100)

  return HttpResponse.json({
    summaries: [
      createSummary({ transcript_id: params.id, template: 'meeting' }),
      createSummary({ transcript_id: params.id, template: 'interview' })
    ],
    total: 2
  })
})

/**
 * GET /api/summaries/:id - Get summary by ID
 */
export const getSummaryHandler = http.get(`${API_BASE}/summaries/:id`, async ({ params }) => {
  await delay(50)

  return HttpResponse.json(
    createSummary({ id: params.id })
  )
})

/**
 * DELETE /api/summaries/:id - Delete summary
 */
export const deleteSummaryHandler = http.delete(`${API_BASE}/summaries/:id`, async () => {
  await delay(100)

  return new HttpResponse(null, { status: 204 })
})

// =============================================================================
// Processing Job Handlers
// =============================================================================

/**
 * GET /api/transcripts/:id/jobs - Get processing jobs
 */
export const getJobsHandler = http.get(`${API_BASE}/transcripts/:id/jobs`, async ({ params }) => {
  await delay(50)

  return HttpResponse.json({
    jobs: [
      {
        id: generateId(),
        transcript_id: params.id,
        job_type: 'transcription',
        status: 'completed',
        progress: 1.0,
        retry_count: 0,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString()
      }
    ]
  })
})

/**
 * GET /api/jobs/:id - Get job by ID
 */
export const getJobHandler = http.get(`${API_BASE}/jobs/:id`, async ({ params }) => {
  await delay(50)

  return HttpResponse.json({
    id: params.id,
    transcript_id: generateId(),
    job_type: 'transcription',
    status: 'processing',
    progress: 0.65,
    retry_count: 0,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString()
  })
})

// =============================================================================
// RAG (Retrieval-Augmented Generation) Handlers
// =============================================================================

/**
 * POST /api/rag/sessions - Create RAG session
 */
export const createRAGSessionHandler = http.post(`${API_BASE}/rag/sessions`, async ({ request }) => {
  await delay(100)

  const body = await request.json()

  return HttpResponse.json(
    createRAGSession({
      session_name: body.session_name,
      transcript_ids: body.transcript_ids
    }),
    { status: 201 }
  )
})

/**
 * GET /api/rag/sessions - List RAG sessions
 */
export const getRAGSessionsHandler = http.get(`${API_BASE}/rag/sessions`, async () => {
  await delay(100)

  return HttpResponse.json({
    sessions: [
      createRAGSession({ session_name: 'Meeting Analysis' }),
      createRAGSession({ session_name: 'Project Planning' }),
      createRAGSession({ session_name: 'Research Notes' })
    ],
    total: 3
  })
})

/**
 * GET /api/rag/sessions/:id - Get RAG session
 */
export const getRAGSessionHandler = http.get(`${API_BASE}/rag/sessions/:id`, async ({ params }) => {
  await delay(50)

  return HttpResponse.json(
    createRAGSession({ id: params.id })
  )
})

/**
 * DELETE /api/rag/sessions/:id - Delete RAG session
 */
export const deleteRAGSessionHandler = http.delete(`${API_BASE}/rag/sessions/:id`, async () => {
  await delay(100)

  return new HttpResponse(null, { status: 204 })
})

/**
 * POST /api/rag/ask - Ask a question
 */
export const askRAGHandler = http.post(`${API_BASE}/rag/ask`, async ({ request }) => {
  await delay(300) // RAG takes time

  const body = await request.json()

  return HttpResponse.json({
    answer: `Based on the transcripts, here's an answer to: "${body.question}". The meeting discussed various topics including project planning and task assignments.`,
    sources: [
      {
        transcript_id: generateId(),
        filename: 'meeting-1.mp3',
        relevance_score: 0.95
      }
    ],
    quality_score: 4.2,
    retrieved_chunks: [
      {
        chunk_text: 'Sample chunk text from the transcript...',
        score: 0.95,
        transcript_id: generateId(),
        start_time: 0,
        end_time: 30
      }
    ],
    quality_metrics: {
      groundedness: 0.9,
      completeness: 0.85,
      relevance: 0.92,
      overall_score: 4.2
    },
    message_id: generateId()
  })
})

/**
 * GET /api/rag/sessions/:id/messages - Get session messages
 */
export const getRAGMessagesHandler = http.get(`${API_BASE}/rag/sessions/:id/messages`, async ({ params }) => {
  await delay(100)

  return HttpResponse.json({
    messages: [
      {
        id: generateId(),
        session_id: params.id,
        question: 'What was discussed?',
        answer: 'The meeting discussed project planning.',
        quality_score: 4.5,
        created_at: new Date().toISOString()
      },
      {
        id: generateId(),
        session_id: params.id,
        question: 'What decisions were made?',
        answer: 'Several decisions were made regarding the project timeline.',
        quality_score: 4.3,
        created_at: new Date().toISOString()
      }
    ],
    total: 2
  })
})

/**
 * POST /api/rag/messages/:id/feedback - Submit feedback
 */
export const submitFeedbackHandler = http.post(`${API_BASE}/rag/messages/:id/feedback`, async () => {
  await delay(100)

  return HttpResponse.json({
    success: true,
    message: 'Feedback submitted successfully'
  })
})

// =============================================================================
// Error Handlers
// =============================================================================

/**
 * 404 Not Found handler
 */
export const notFoundHandler = http.all(`${API_BASE}/*`, () => {
  return HttpResponse.json(
    { error: 'Resource not found' },
    { status: 404 }
  )
})

/**
 * 500 Server Error handler (can be enabled for error testing)
 */
export const serverErrorHandler = http.all(`${API_BASE}/transcripts/:id/error`, () => {
  return HttpResponse.json(
    { error: 'Internal server error' },
    { status: 500 }
  )
})

/**
 * 401 Unauthorized handler
 */
export const unauthorizedHandler = http.get(`${API_BASE}/auth-required`, () => {
  return HttpResponse.json(
    { error: 'Unauthorized' },
    { status: 401 }
  )
})

/**
 * 403 Forbidden handler
 */
export const forbiddenHandler = http.delete(`${API_BASE}/transcripts/:id/forbidden`, () => {
  return HttpResponse.json(
    { error: 'Forbidden' },
    { status: 403 }
  )
})

/**
 * 429 Rate Limit handler
 */
export const rateLimitHandler = http.get(`${API_BASE}/rate-limited`, () => {
  return HttpResponse.json(
    { error: 'Too many requests' },
    { status: 429 }
  )
})

// =============================================================================
// Combined Handlers
// =============================================================================

/**
 * Default handlers to use in tests
 */
export const handlers = [
  // Transcript endpoints
  getTranscriptsHandler,
  getTranscriptHandler,
  uploadTranscriptHandler,
  deleteTranscriptHandler,
  updateTranscriptHandler,

  // Summary endpoints
  createSummaryHandler,
  getSummariesHandler,
  getSummaryHandler,
  deleteSummaryHandler,

  // Processing job endpoints
  getJobsHandler,
  getJobHandler,

  // RAG endpoints
  createRAGSessionHandler,
  getRAGSessionsHandler,
  getRAGSessionHandler,
  deleteRAGSessionHandler,
  askRAGHandler,
  getRAGMessagesHandler,
  submitFeedbackHandler,

  // Error handlers (commented out by default, uncomment as needed)
  // notFoundHandler,
  // serverErrorHandler,
  // unauthorizedHandler,
  // forbiddenHandler,
  // rateLimitHandler,
]

// =============================================================================
// Handler Configuration Helpers
// =============================================================================

/**
 * Create handlers with custom delay
 * @param {number} delayMs - Delay in milliseconds
 * @returns {Array} Handlers with custom delay
 */
export const createDelayedHandlers = (delayMs) => {
  // You can modify this function to apply delays to all handlers
  return handlers
}

/**
 * Create handlers that simulate errors
 * @param {string} endpoint - Endpoint pattern to make fail
 * @param {number} statusCode - HTTP status code to return
 * @returns {Array} Modified handlers
 */
export const createFailingHandlers = (endpoint, statusCode = 500) => {
  return handlers.map(handler => {
    // Modify specific handler to return error
    // This is a simplified example
    return handler
  })
}

/**
 * Create handlers with empty responses
 * @returns {Array} Handlers returning empty data
 */
export const createEmptyHandlers = () => {
  return [
    http.get(`${API_BASE}/transcripts`, () => {
      return HttpResponse.json({ transcripts: [], total: 0 })
    }),
    http.get(`${API_BASE}/transcripts/:id`, () => {
      return HttpResponse.json({ error: 'Not found' }, { status: 404 })
    }),
    // Add more empty handlers as needed
  ]
}
