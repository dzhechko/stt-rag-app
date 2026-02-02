import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import RAGChatPage from '../../../src/pages/RAGChatPage'
import * as client from '../../../src/api/client'
import clientInstance from '../../../src/api/client'

// Mock the API client
vi.mock('../../../src/api/client', () => ({
  getTranscripts: vi.fn(),
  getRAGSessions: vi.fn(),
  createRAGSession: vi.fn(),
  deleteRAGSession: vi.fn()
}))

vi.mock('../../../src/api/client', async () => {
  const actual = await vi.importActual('../../../src/api/client')
  return {
    default: {
      get: vi.fn(),
      post: vi.fn()
    },
    ...actual
  }
})

const mockNavigate = vi.fn()
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom')
  return {
    ...actual,
    useNavigate: () => mockNavigate,
    useParams: () => ({ sessionId: undefined })
  }
})

const mockTranscripts = [
  {
    id: 'transcript-1',
    original_filename: 'meeting1.mp3',
    status: 'completed',
    language: 'ru',
    file_size: 1024000,
    created_at: '2024-01-15T10:30:00',
    transcription_text: 'First meeting transcript'
  },
  {
    id: 'transcript-2',
    original_filename: 'meeting2.mp3',
    status: 'completed',
    language: 'en',
    file_size: 2048000,
    created_at: '2024-01-14T10:30:00',
    transcription_text: 'Second meeting transcript'
  }
]

const mockSessions = [
  {
    id: 'session-1',
    session_name: 'Test Session',
    transcript_ids: ['transcript-1'],
    created_at: '2024-01-15T10:00:00'
  },
  {
    id: 'session-2',
    session_name: 'Another Session',
    transcript_ids: [],
    created_at: '2024-01-14T10:00:00'
  }
]

const mockMessages = [
  {
    id: 'msg-1',
    question: 'What was discussed?',
    answer: 'The meeting covered several topics.',
    quality_score: 4.5,
    quality_metrics: {
      groundedness: 0.9,
      completeness: 0.85,
      relevance: 0.92
    },
    retrieved_chunks: [
      {
        chunk_text: 'Meeting discussed important topics.',
        score: 0.95,
        transcript_id: 'transcript-1'
      }
    ]
  }
]

describe('RAGChatPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.useFakeTimers()
    client.getTranscripts.mockResolvedValue({ transcripts: mockTranscripts })
    client.getRAGSessions.mockResolvedValue(mockSessions)
    clientInstance.get.mockResolvedValue({ data: mockMessages })
    clientInstance.post.mockResolvedValue({
      data: {
        answer: 'Test answer',
        quality_score: 4.0,
        retrieved_chunks: [],
        message_id: 'new-msg-1'
      }
    })
  })

  afterEach(() => {
    vi.runOnlyPendingTimers()
    vi.useRealTimers()
  })

  const renderComponent = (route = '/rag') => {
    return render(
      <MemoryRouter initialEntries={[route]}>
        <Routes>
          <Route path="/rag" element={<RAGChatPage />} />
          <Route path="/rag/sessions/:sessionId" element={<RAGChatPage />} />
        </Routes>
      </MemoryRouter>
    )
  }

  describe('Rendering', () => {
    it('should render the chat page', () => {
      renderComponent()

      expect(screen.getByText('RAG Chat')).toBeInTheDocument()
    })

    it('should display transcripts sidebar', async () => {
      renderComponent()

      await waitFor(() => {
        expect(screen.getByText('Выбрать транскрипты')).toBeInTheDocument()
        expect(screen.getByText('meeting1.mp3')).toBeInTheDocument()
        expect(screen.getByText('meeting2.mp3')).toBeInTheDocument()
      })
    })

    it('should display empty chat state initially', async () => {
      renderComponent()

      await waitFor(() => {
        expect(screen.getByText('Задайте вопрос о ваших транскриптах')).toBeInTheDocument()
      })
    })

    it('should display input field', () => {
      renderComponent()

      const input = screen.getByPlaceholderText('Задайте вопрос...')
      expect(input).toBeInTheDocument()
    })

    it('should display send button', () => {
      renderComponent()

      const sendButton = screen.container.querySelector('button[disabled]')
      expect(sendButton).toBeInTheDocument()
    })
  })

  describe('Chat Message Display', () => {
    it('should display user questions', async () => {
      renderComponent()

      const input = screen.getByPlaceholderText('Задайте вопрос...')
      const sendButton = screen.container.querySelector('button:not([disabled])')

      await userEvent.type(input, 'What was discussed?')
      fireEvent.click(sendButton)

      await waitFor(() => {
        expect(screen.getByText(/Вы:/)).toBeInTheDocument()
        expect(screen.getByText('What was discussed?')).toBeInTheDocument()
      })
    })

    it('should display assistant answers', async () => {
      renderComponent()

      const input = screen.getByPlaceholderText('Задайте вопрос...')
      const sendButton = screen.container.querySelector('button:not([disabled])')

      await userEvent.type(input, 'Test question')
      fireEvent.click(sendButton)

      await waitFor(() => {
        expect(screen.getByText(/Ассистент:/)).toBeInTheDocument()
        expect(screen.getByText('Test answer')).toBeInTheDocument()
      })
    })

    it('should display quality score for answers', async () => {
      renderComponent()

      const input = screen.getByPlaceholderText('Задайте вопрос...')
      const sendButton = screen.container.querySelector('button:not([disabled])')

      await userEvent.type(input, 'Test question')
      fireEvent.click(sendButton)

      await waitFor(() => {
        expect(screen.getByText(/Качество: 4\.0\/5\.0/)).toBeInTheDocument()
      })
    })

    it('should display quality metrics', async () => {
      clientInstance.post.mockResolvedValue({
        data: {
          answer: 'Test answer',
          quality_score: 4.5,
          quality_metrics: {
            groundedness: 0.9,
            completeness: 0.85,
            relevance: 0.92
          },
          retrieved_chunks: []
        }
      })

      renderComponent()

      const input = screen.getByPlaceholderText('Задайте вопрос...')
      const sendButton = screen.container.querySelector('button:not([disabled])')

      await userEvent.type(input, 'Test question')
      fireEvent.click(sendButton)

      await waitFor(() => {
        expect(screen.getByText(/Обоснованность: 90%/)).toBeInTheDocument()
        expect(screen.getByText(/Полнота: 85%/)).toBeInTheDocument()
        expect(screen.getByText(/Релевантность: 92%/)).toBeInTheDocument()
      })
    })

    it('should display retrieved chunks', async () => {
      clientInstance.post.mockResolvedValue({
        data: {
          answer: 'Test answer',
          quality_score: 4.0,
          retrieved_chunks: [
            {
              chunk_text: 'Relevant chunk text',
              score: 0.95,
              transcript_id: 'transcript-1'
            }
          ]
        }
      })

      renderComponent()

      const input = screen.getByPlaceholderText('Задайте вопрос...')
      const sendButton = screen.container.querySelector('button:not([disabled])')

      await userEvent.type(input, 'Test question')
      fireEvent.click(sendButton)

      await waitFor(() => {
        expect(screen.getByText(/Использовано 1 источник/)).toBeInTheDocument()
      })
    })

    it('should display error messages', async () => {
      clientInstance.post.mockRejectedValue({
        response: { data: { detail: 'Connection error' } }
      })

      renderComponent()

      const input = screen.getByPlaceholderText('Задайте вопрос...')
      const sendButton = screen.container.querySelector('button:not([disabled])')

      await userEvent.type(input, 'Test question')
      fireEvent.click(sendButton)

      await waitFor(() => {
        expect(screen.getByText(/Connection error/)).toBeInTheDocument()
      })
    })
  })

  describe('Input Handling', () => {
    it('should send message on Enter key', async () => {
      renderComponent()

      const input = screen.getByPlaceholderText('Задайте вопрос...')

      await userEvent.type(input, 'Test question{Enter}')

      await waitFor(() => {
        expect(clientInstance.post).toHaveBeenCalled()
      })
    })

    it('should not send message on Enter+Shift', async () => {
      renderComponent()

      const input = screen.getByPlaceholderText('Задайте вопрос...')

      await userEvent.type(input, 'Test question{Shift>}{Enter}{/Shift}')

      await waitFor(() => {
        expect(input).toHaveValue('Test question\n')
      })
    })

    it('should clear input after sending', async () => {
      renderComponent()

      const input = screen.getByPlaceholderText('Задайте вопрос...')
      const sendButton = screen.container.querySelector('button:not([disabled])')

      await userEvent.type(input, 'Test question')
      fireEvent.click(sendButton)

      await waitFor(() => {
        expect(input).toHaveValue('')
      })
    })

    it('should disable send button while loading', async () => {
      clientInstance.post.mockImplementation(() => new Promise(() => {}))

      renderComponent()

      const input = screen.getByPlaceholderText('Задайте вопрос...')
      const sendButton = screen.container.querySelector('button:not([disabled])')

      await userEvent.type(input, 'Test question')
      fireEvent.click(sendButton)

      await waitFor(() => {
        const disabledButton = screen.container.querySelector('button[disabled]')
        expect(disabledButton).toBeInTheDocument()
      })
    })

    it('should not send empty messages', async () => {
      renderComponent()

      const sendButton = screen.container.querySelector('button[disabled]')
      fireEvent.click(sendButton)

      expect(clientInstance.post).not.toHaveBeenCalled()
    })
  })

  describe('Transcript Selection', () => {
    it('should display transcript checkboxes', async () => {
      renderComponent()

      await waitFor(() => {
        const checkboxes = screen.container.querySelectorAll('input[type="checkbox"]')
        expect(checkboxes.length).toBeGreaterThan(0)
      })
    })

    it('should select transcript when checkbox clicked', async () => {
      renderComponent()

      await waitFor(() => {
        const checkbox = screen.container.querySelector('input[type="checkbox"]')
        fireEvent.click(checkbox)
      })

      await waitFor(() => {
        const checkedCheckbox = screen.container.querySelector('input[type="checkbox"]:checked')
        expect(checkedCheckbox).toBeInTheDocument()
      })
    })

    it('should show info when no transcripts selected', async () => {
      renderComponent()

      await waitFor(() => {
        expect(screen.getByText('Транскрипты не выбраны - поиск по всем')).toBeInTheDocument()
      })
    })

    it('should show empty state when no transcripts available', async () => {
      client.getTranscripts.mockResolvedValue({ transcripts: [] })

      renderComponent()

      await waitFor(() => {
        expect(screen.getByText('Транскрипты не найдены. Сначала загрузите файлы!')).toBeInTheDocument()
      })
    })
  })

  describe('Session Management', () => {
    it('should display session toggle', () => {
      renderComponent()

      expect(screen.getByText('Использовать историю')).toBeInTheDocument()
    })

    it('should enable session mode when toggle clicked', async () => {
      renderComponent()

      const toggle = screen.getByLabelText('Использовать историю')
      fireEvent.click(toggle)

      await waitFor(() => {
        expect(toggle).toBeChecked()
      })
    })

    it('should show session selector when enabled', async () => {
      renderComponent()

      const toggle = screen.getByLabelText('Использовать историю')
      fireEvent.click(toggle)

      await waitFor(() => {
        expect(screen.getByText('Выбрать сессию')).toBeInTheDocument()
      })
    })

    it('should display session list', async () => {
      renderComponent()

      const toggle = screen.getByLabelText('Использовать историю')
      fireEvent.click(toggle)

      const selectButton = await screen.findByText('Выбрать сессию')
      fireEvent.click(selectButton)

      await waitFor(() => {
        expect(screen.getByText('Test Session')).toBeInTheDocument()
        expect(screen.getByText('Another Session')).toBeInTheDocument()
      })
    })

    it('should select session when clicked', async () => {
      renderComponent()

      const toggle = screen.getByLabelText('Использовать историю')
      fireEvent.click(toggle)

      const selectButton = await screen.findByText('Выбрать сессию')
      fireEvent.click(selectButton)

      await waitFor(() => {
        const sessionItem = screen.getByText('Test Session').closest('.session-item')
        fireEvent.click(sessionItem)
      })

      expect(mockNavigate).toHaveBeenCalledWith('/rag/sessions/session-1')
    })

    it('should create new session', async () => {
      client.createRAGSession.mockResolvedValue({
        id: 'new-session-1',
        session_name: 'New Session'
      })

      renderComponent()

      const toggle = screen.getByLabelText('Использовать историю')
      fireEvent.click(toggle)

      const selectButton = await screen.findByText('Выбрать сессию')
      fireEvent.click(selectButton)

      const input = screen.getByPlaceholderText('Название новой сессии...')
      await userEvent.type(input, 'New Session{Enter}')

      await waitFor(() => {
        expect(client.createRAGSession).toHaveBeenCalledWith({
          session_name: 'New Session',
          transcript_ids: []
        })
      })
    })

    it('should delete session when delete clicked', async () => {
      client.deleteRAGSession.mockResolvedValue()
      window.confirm = vi.fn(() => true)

      renderComponent()

      const toggle = screen.getByLabelText('Использовать историю')
      fireEvent.click(toggle)

      const selectButton = await screen.findByText('Выбрать сессию')
      fireEvent.click(selectButton)

      await waitFor(() => {
        const deleteButton = screen.container.querySelector('.btn-delete-session')
        fireEvent.click(deleteButton)
      })

      expect(window.confirm).toHaveBeenCalled()
    })

    it('should clear history when button clicked', async () => {
      renderComponent()

      const toggle = screen.getByLabelText('Использовать историю')
      fireEvent.click(toggle)

      const selectButton = await screen.findByText('Выбрать сессию')
      fireEvent.click(selectButton)

      const clearButton = await screen.findByText('Очистить историю')
      fireEvent.click(clearButton)

      expect(mockNavigate).toHaveBeenCalledWith('/rag')
    })
  })

  describe('Session Loading', () => {
    it('should load session messages when sessionId in URL', async () => {
      const { rerender } = render(
        <MemoryRouter initialEntries={['/rag/sessions/session-1']}>
          <Routes>
            <Route path="/rag/sessions/:sessionId" element={<RAGChatPage />} />
          </Routes>
        </MemoryRouter>
      )

      await waitFor(() => {
        expect(clientInstance.get).toHaveBeenCalledWith('/rag/sessions/session-1/messages')
      })
    })

    it('should display session messages', async () => {
      clientInstance.get.mockResolvedValue({ data: mockMessages })

      render(
        <MemoryRouter initialEntries={['/rag/sessions/session-1']}>
          <Routes>
            <Route path="/rag/sessions/:sessionId" element={<RAGChatPage />} />
          </Routes>
        </MemoryRouter>
      )

      await waitFor(() => {
        expect(screen.getByText('What was discussed?')).toBeInTheDocument()
        expect(screen.getByText('The meeting covered several topics.')).toBeInTheDocument()
      })
    })

    it('should display error on session load failure', async () => {
      clientInstance.get.mockRejectedValue({
        response: { data: { detail: 'Session not found' } }
      })

      render(
        <MemoryRouter initialEntries={['/rag/sessions/session-1']}>
          <Routes>
            <Route path="/rag/sessions/:sessionId" element={<RAGChatPage />} />
          </Routes>
        </MemoryRouter>
      )

      await waitFor(() => {
        expect(screen.getByText(/Session not found/)).toBeInTheDocument()
      })
    })
  })

  describe('Settings', () => {
    it('should open settings modal', async () => {
      renderComponent()

      const settingsButton = await screen.findByText('Настройки')
      fireEvent.click(settingsButton)

      await waitFor(() => {
        expect(screen.getByText('Настройки RAG')).toBeInTheDocument()
      })
    })

    it('should update top_k setting', async () => {
      renderComponent()

      const settingsButton = await screen.findByText('Настройки')
      fireEvent.click(settingsButton)

      const topKInput = screen.getByLabelText(/Количество чанков/)
      fireEvent.change(topKInput, { target: { value: '10' } })

      await waitFor(() => {
        expect(topKInput).toHaveValue(10)
      })
    })

    it('should update model setting', async () => {
      renderComponent()

      const settingsButton = await screen.findByText('Настройки')
      fireEvent.click(settingsButton)

      const modelSelect = screen.getByLabelText(/Модель для генерации ответа:/)
      fireEvent.change(modelSelect, { target: { value: 'Qwen/Qwen3-235B-A22B-Instruct-2507' } })

      await waitFor(() => {
        expect(modelSelect).toHaveValue('Qwen/Qwen3-235B-A22B-Instruct-2507')
      })
    })

    it('should update temperature setting', async () => {
      renderComponent()

      const settingsButton = await screen.findByText('Настройки')
      fireEvent.click(settingsButton)

      const temperatureInput = screen.getByLabelText(/Температура:/)
      fireEvent.change(temperatureInput, { target: { value: '0.7' } })

      await waitFor(() => {
        expect(temperatureInput).toHaveValue(0.7)
      })
    })

    it('should toggle query expansion', async () => {
      renderComponent()

      const settingsButton = await screen.findByText('Настройки')
      fireEvent.click(settingsButton)

      const checkbox = screen.getByLabelText(/Включить расширение запроса/)
      fireEvent.click(checkbox)

      await waitFor(() => {
        expect(checkbox).toBeChecked()
      })
    })
  })

  describe('Loading States', () => {
    it('should show loading indicator while processing', async () => {
      clientInstance.post.mockImplementation(() => new Promise(() => {}))

      renderComponent()

      const input = screen.getByPlaceholderText('Задайте вопрос...')
      const sendButton = screen.container.querySelector('button:not([disabled])')

      await userEvent.type(input, 'Test question')
      fireEvent.click(sendButton)

      await waitFor(() => {
        expect(screen.getByText('Думаю...')).toBeInTheDocument()
      })
    })
  })

  describe('Feedback Buttons', () => {
    it('should display feedback buttons for answers', async () => {
      clientInstance.post.mockResolvedValue({
        data: {
          answer: 'Test answer',
          message_id: 'msg-123'
        }
      })

      renderComponent()

      const input = screen.getByPlaceholderText('Задайте вопрос...')
      const sendButton = screen.container.querySelector('button:not([disabled])')

      await userEvent.type(input, 'Test question')
      fireEvent.click(sendButton)

      await waitFor(() => {
        expect(screen.getByText('Полезно')).toBeInTheDocument()
        expect(screen.getByText('Не полезно')).toBeInTheDocument()
      })
    })

    it('should submit positive feedback', async () => {
      clientInstance.post.mockImplementation((url, data) => {
        if (url.includes('/feedback')) {
          return Promise.resolve()
        }
        return Promise.resolve({
          data: {
            answer: 'Test answer',
            message_id: 'msg-123'
          }
        })
      })

      renderComponent()

      const input = screen.getByPlaceholderText('Задайте вопрос...')
      const sendButton = screen.container.querySelector('button:not([disabled])')

      await userEvent.type(input, 'Test question')
      fireEvent.click(sendButton)

      const feedbackButton = await screen.findByText('Полезно')
      fireEvent.click(feedbackButton)

      await waitFor(() => {
        expect(clientInstance.post).toHaveBeenCalledWith('/rag/messages/msg-123/feedback', {
          feedback_type: 'positive',
          comment: null
        })
      })
    })
  })

  describe('Copy Button', () => {
    it('should copy answer to clipboard', async () => {
      renderComponent()

      const input = screen.getByPlaceholderText('Задайте вопрос...')
      const sendButton = screen.container.querySelector('button:not([disabled])')

      await userEvent.type(input, 'Test question')
      fireEvent.click(sendButton)

      await waitFor(() => {
        const copyButton = screen.getByText('Копировать ответ')
        fireEvent.click(copyButton)
      })

      await waitFor(() => {
        expect(navigator.clipboard.writeText).toHaveBeenCalledWith('Test answer')
      })
    })
  })

  describe('Navigation', () => {
    it('should navigate back to transcripts when back button clicked', () => {
      renderComponent()

      const backButton = screen.getByText('Back')
      fireEvent.click(backButton)

      expect(mockNavigate).toHaveBeenCalledWith('/transcripts')
    })
  })

  describe('Accessibility', () => {
    it('should have proper heading structure', () => {
      renderComponent()

      const heading = screen.getByRole('heading', { level: 1 })
      expect(heading).toHaveTextContent('RAG Chat')
    })

    it('should be keyboard navigable', async () => {
      renderComponent()

      const input = screen.getByPlaceholderText('Задайте вопрос...')
      input.focus()

      expect(input).toHaveFocus()

      await userEvent.keyboard('Test question')

      expect(input).toHaveValue('Test question')
    })
  })

  describe('Responsive Behavior', () => {
    it('should display messages in scrollable container', async () => {
      renderComponent()

      const messagesContainer = screen.container.querySelector('.messages-container')
      expect(messagesContainer).toBeInTheDocument()
    })
  })
})
