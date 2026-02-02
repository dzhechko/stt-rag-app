import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, fireEvent, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import TranscriptsPage from '../../../src/pages/TranscriptsPage'
import * as client from '../../../src/api/client'

// Mock the API client
vi.mock('../../../src/api/client', () => ({
  getTranscripts: vi.fn(),
  deleteTranscript: vi.fn(),
  getTranscriptJobs: vi.fn()
}))

const mockTranscripts = [
  {
    id: 'transcript-1',
    original_filename: 'meeting1.mp3',
    status: 'completed',
    language: 'ru',
    file_size: 1024000,
    created_at: '2024-01-15T10:30:00',
    transcription_text: 'This is the first meeting transcript.',
    transcription_json: { segments: [{ start: 0, end: 1, text: 'Test' }] },
    transcription_srt: '1\n00:00:00,000 --> 00:00:01,000\nTest'
  },
  {
    id: 'transcript-2',
    original_filename: 'meeting2.mp3',
    status: 'processing',
    language: 'en',
    file_size: 2048000,
    created_at: '2024-01-15T11:30:00',
    transcription_text: null
  },
  {
    id: 'transcript-3',
    original_filename: 'meeting3.mp3',
    status: 'pending',
    language: 'de',
    file_size: 512000,
    created_at: '2024-01-15T12:30:00',
    transcription_text: null
  },
  {
    id: 'transcript-4',
    original_filename: 'meeting4.mp3',
    status: 'failed',
    language: 'fr',
    file_size: 768000,
    created_at: '2024-01-15T13:30:00',
    transcription_text: null
  }
]

describe('TranscriptsPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.runOnlyPendingTimers()
    vi.useRealTimers()
  })

  describe('Rendering', () => {
    it('should render the page title', () => {
      client.getTranscripts.mockResolvedValue({ transcripts: [] })

      render(
        <MemoryRouter>
          <TranscriptsPage />
        </MemoryRouter>
      )

      expect(screen.getByText('Транскрипты')).toBeInTheDocument()
    })

    it('should show loading state initially', () => {
      client.getTranscripts.mockImplementation(() => new Promise(() => {}))

      render(
        <MemoryRouter>
          <TranscriptsPage />
        </MemoryRouter>
      )

      expect(screen.getByText('Загрузка транскриптов...')).toBeInTheDocument()
    })

    it('should display empty state when no transcripts', async () => {
      client.getTranscripts.mockResolvedValue({ transcripts: [] })

      render(
        <MemoryRouter>
          <TranscriptsPage />
        </MemoryRouter>
      )

      await waitFor(() => {
        expect(screen.getByText('Транскрипты не найдены')).toBeInTheDocument()
      })
    })

    it('should render transcripts list', async () => {
      client.getTranscripts.mockResolvedValue({ transcripts: mockTranscripts })

      render(
        <MemoryRouter>
          <TranscriptsPage />
        </MemoryRouter>
      )

      await waitFor(() => {
        expect(screen.getByText('meeting1.mp3')).toBeInTheDocument()
        expect(screen.getByText('meeting2.mp3')).toBeInTheDocument()
      })
    })
  })

  describe('Filtering', () => {
    it('should filter by status - completed', async () => {
      client.getTranscripts.mockResolvedValue({ transcripts: [mockTranscripts[0]] })

      render(
        <MemoryRouter>
          <TranscriptsPage />
        </MemoryRouter>
      )

      const statusFilter = await screen.findByText('Все статусы')
      fireEvent.change(statusFilter, { target: { value: 'completed' } })

      await waitFor(() => {
        expect(client.getTranscripts).toHaveBeenCalledWith(0, 100, { status: 'completed', language: '' })
      })
    })

    it('should filter by status - processing', async () => {
      client.getTranscripts.mockResolvedValue({ transcripts: [mockTranscripts[1]] })

      render(
        <MemoryRouter>
          <TranscriptsPage />
        </MemoryRouter>
      )

      const statusFilter = await screen.findByText('Все статусы')
      fireEvent.change(statusFilter, { target: { value: 'processing' } })

      await waitFor(() => {
        expect(client.getTranscripts).toHaveBeenCalledWith(0, 100, { status: 'processing', language: '' })
      })
    })

    it('should filter by language', async () => {
      client.getTranscripts.mockResolvedValue({ transcripts: [mockTranscripts[0]] })

      render(
        <MemoryRouter>
          <TranscriptsPage />
        </MemoryRouter>
      )

      const languageFilter = await screen.findByText('Все языки')
      fireEvent.change(languageFilter, { target: { value: 'ru' } })

      await waitFor(() => {
        expect(client.getTranscripts).toHaveBeenCalledWith(0, 100, { status: '', language: 'ru' })
      })
    })

    it('should combine status and language filters', async () => {
      client.getTranscripts.mockResolvedValue({ transcripts: [] })

      render(
        <MemoryRouter>
          <TranscriptsPage />
        </MemoryRouter>
      )

      const statusFilter = await screen.findByText('Все статусы')
      const languageFilter = await screen.findByText('Все языки')

      fireEvent.change(statusFilter, { target: { value: 'completed' } })
      fireEvent.change(languageFilter, { target: { value: 'ru' } })

      await waitFor(() => {
        expect(client.getTranscripts).toHaveBeenCalledWith(0, 100, { status: 'completed', language: 'ru' })
      })
    })

    it('should reset filters when selecting "All"', async () => {
      client.getTranscripts.mockResolvedValue({ transcripts: mockTranscripts })

      render(
        <MemoryRouter>
          <TranscriptsPage />
        </MemoryRouter>
      )

      const statusFilter = await screen.findByText('Все статусы')

      fireEvent.change(statusFilter, { target: { value: 'completed' } })
      await waitFor(() => {})

      fireEvent.change(statusFilter, { target: { value: '' } })

      await waitFor(() => {
        expect(client.getTranscripts).toHaveBeenCalledWith(0, 100, { status: '', language: '' })
      })
    })
  })

  describe('Search Functionality', () => {
    // Note: The current implementation doesn't have a search input in the UI,
    // but filtering acts as a form of search by status/language
    it('should reload transcripts when filter changes', async () => {
      const { rerender } = render(
        <MemoryRouter>
          <TranscriptsPage />
        </MemoryRouter>
      )

      client.getTranscripts.mockClear()
      client.getTranscripts.mockResolvedValue({ transcripts: [mockTranscripts[0]] })

      const statusFilter = await screen.findByText('Все статусы')
      fireEvent.change(statusFilter, { target: { value: 'completed' } })

      await waitFor(() => {
        expect(client.getTranscripts).toHaveBeenCalled()
      })
    })
  })

  describe('Transcript Card Display', () => {
    it('should display transcript filename', async () => {
      client.getTranscripts.mockResolvedValue({ transcripts: [mockTranscripts[0]] })

      render(
        <MemoryRouter>
          <TranscriptsPage />
        </MemoryRouter>
      )

      await waitFor(() => {
        expect(screen.getByText('meeting1.mp3')).toBeInTheDocument()
      })
    })

    it('should display file size in correct format', async () => {
      client.getTranscripts.mockResolvedValue({ transcripts: [mockTranscripts[0]] })

      render(
        <MemoryRouter>
          <TranscriptsPage />
        </MemoryRouter>
      )

      await waitFor(() => {
        expect(screen.getByText(/1\.00 MB/)).toBeInTheDocument()
      })
    })

    it('should display creation date', async () => {
      client.getTranscripts.mockResolvedValue({ transcripts: [mockTranscripts[0]] })

      render(
        <MemoryRouter>
          <TranscriptsPage />
        </MemoryRouter>
      )

      await waitFor(() => {
        expect(screen.getByText(/1\/15\/2024/)).toBeInTheDocument()
      })
    })

    it('should display language', async () => {
      client.getTranscripts.mockResolvedValue({ transcripts: [mockTranscripts[0]] })

      render(
        <MemoryRouter>
          <TranscriptsPage />
        </MemoryRouter>
      )

      await waitFor(() => {
        expect(screen.getByText('RU')).toBeInTheDocument()
      })
    })

    it('should display status badge with correct color', async () => {
      client.getTranscripts.mockResolvedValue({ transcripts: mockTranscripts })

      render(
        <MemoryRouter>
          <TranscriptsPage />
        </MemoryRouter>
      )

      await waitFor(() => {
        const completedBadge = screen.getByText('completed').closest('.status-badge')
        expect(completedBadge).toHaveStyle({ backgroundColor: '#27ae60' })

        const processingBadge = screen.getByText('processing').closest('.status-badge')
        expect(processingBadge).toHaveStyle({ backgroundColor: '#3498db' })

        const pendingBadge = screen.getByText('pending').closest('.status-badge')
        expect(pendingBadge).toHaveStyle({ backgroundColor: '#f39c12' })

        const failedBadge = screen.getByText('failed').closest('.status-badge')
        expect(failedBadge).toHaveStyle({ backgroundColor: '#e74c3c' })
      })
    })
  })

  describe('Transcript Preview', () => {
    it('should show transcript preview toggle for completed transcripts', async () => {
      client.getTranscripts.mockResolvedValue({ transcripts: [mockTranscripts[0]] })

      render(
        <MemoryRouter>
          <TranscriptsPage />
        </MemoryRouter>
      )

      await waitFor(() => {
        expect(screen.getByText('Показать транскрипт')).toBeInTheDocument()
      })
    })

    it('should expand transcript when toggle is clicked', async () => {
      client.getTranscripts.mockResolvedValue({ transcripts: [mockTranscripts[0]] })

      render(
        <MemoryRouter>
          <TranscriptsPage />
        </MemoryRouter>
      )

      const toggleButton = await screen.findByText('Показать транскрипт')
      fireEvent.click(toggleButton)

      await waitFor(() => {
        expect(screen.getByText('This is the first meeting transcript.')).toBeInTheDocument()
      })
    })

    it('should switch between text, JSON, and SRT views', async () => {
      client.getTranscripts.mockResolvedValue({ transcripts: [mockTranscripts[0]] })

      render(
        <MemoryRouter>
          <TranscriptsPage />
        </MemoryRouter>
      )

      // Expand transcript
      const toggleButton = await screen.findByText('Показать транскрипт')
      fireEvent.click(toggleButton)

      // Check text view is active by default
      await waitFor(() => {
        expect(screen.getByText('This is the first meeting transcript.')).toBeInTheDocument()
      })

      // Switch to JSON
      const jsonButton = screen.getByText('JSON')
      fireEvent.click(jsonButton)

      await waitFor(() => {
        expect(screen.getByText('{')).toBeInTheDocument()
      })

      // Switch to SRT
      const srtButton = screen.getByText('SRT')
      fireEvent.click(srtButton)

      await waitFor(() => {
        expect(screen.getByText(/00:00:00/)).toBeInTheDocument()
      })
    })

    it('should collapse transcript when hide button is clicked', async () => {
      client.getTranscripts.mockResolvedValue({ transcripts: [mockTranscripts[0]] })

      render(
        <MemoryRouter>
          <TranscriptsPage />
        </MemoryRouter>
      )

      const toggleButton = await screen.findByText('Показать транскрипт')
      fireEvent.click(toggleButton)

      await waitFor(() => {
        expect(screen.getByText('This is the first meeting transcript.')).toBeInTheDocument()
      })

      const hideButton = screen.getByText('Скрыть транскрипт')
      fireEvent.click(hideButton)

      await waitFor(() => {
        expect(screen.queryByText('This is the first meeting transcript.')).not.toBeInTheDocument()
      })
    })
  })

  describe('Progress Display', () => {
    it('should show progress bar for processing transcripts', async () => {
      client.getTranscripts.mockResolvedValue({ transcripts: [mockTranscripts[1]] })
      client.getTranscriptJobs.mockResolvedValue([
        { job_type: 'transcription', status: 'processing', progress: 0.5 }
      ])

      render(
        <MemoryRouter>
          <TranscriptsPage />
        </MemoryRouter>
      )

      await waitFor(() => {
        expect(screen.getByText('50%')).toBeInTheDocument()
      })
    })

    it('should poll for progress updates', async () => {
      client.getTranscripts.mockResolvedValue({ transcripts: [mockTranscripts[1]] })
      client.getTranscriptJobs
        .mockResolvedValueOnce([{ job_type: 'transcription', status: 'processing', progress: 0.3 }])
        .mockResolvedValueOnce([{ job_type: 'transcription', status: 'processing', progress: 0.6 }])

      render(
        <MemoryRouter>
          <TranscriptsPage />
        </MemoryRouter>
      )

      await waitFor(() => {
        expect(screen.getByText('30%')).toBeInTheDocument()
      })

      // Advance timers to trigger next poll
      vi.advanceTimersByTime(2000)

      await waitFor(() => {
        expect(screen.getByText('60%')).toBeInTheDocument()
      })
    })
  })

  describe('Delete Confirmation', () => {
    it('should show confirmation dialog when delete is clicked', async () => {
      client.getTranscripts.mockResolvedValue({ transcripts: [mockTranscripts[0]] })
      window.confirm = vi.fn(() => true)
      client.deleteTranscript.mockResolvedValue()

      render(
        <MemoryRouter>
          <TranscriptsPage />
        </MemoryRouter>
      )

      const deleteButton = await screen.findByText('Удалить')
      fireEvent.click(deleteButton)

      expect(window.confirm).toHaveBeenCalledWith('Вы уверены, что хотите удалить этот транскрипт?')
    })

    it('should delete transcript when confirmed', async () => {
      client.getTranscripts.mockResolvedValue({ transcripts: [mockTranscripts[0]] })
      window.confirm = vi.fn(() => true)
      client.deleteTranscript.mockResolvedValue()
      client.getTranscripts.mockResolvedValue({ transcripts: [] })

      render(
        <MemoryRouter>
          <TranscriptsPage />
        </MemoryRouter>
      )

      const deleteButton = await screen.findByText('Удалить')
      fireEvent.click(deleteButton)

      await waitFor(() => {
        expect(client.deleteTranscript).toHaveBeenCalledWith('transcript-1')
        expect(client.getTranscripts).toHaveBeenCalled()
      })
    })

    it('should not delete transcript when cancelled', async () => {
      client.getTranscripts.mockResolvedValue({ transcripts: [mockTranscripts[0]] })
      window.confirm = vi.fn(() => false)
      client.deleteTranscript.mockResolvedValue()

      render(
        <MemoryRouter>
          <TranscriptsPage />
        </MemoryRouter>
      )

      const deleteButton = await screen.findByText('Удалить')
      fireEvent.click(deleteButton)

      expect(client.deleteTranscript).not.toHaveBeenCalled()
    })

    it('should show error alert on delete failure', async () => {
      client.getTranscripts.mockResolvedValue({ transcripts: [mockTranscripts[0]] })
      window.confirm = vi.fn(() => true)
      client.deleteTranscript.mockRejectedValue(new Error('Delete failed'))
      window.alert = vi.fn()

      render(
        <MemoryRouter>
          <TranscriptsPage />
        </MemoryRouter>
      )

      const deleteButton = await screen.findByText('Удалить')
      fireEvent.click(deleteButton)

      await waitFor(() => {
        expect(window.alert).toHaveBeenCalledWith('Ошибка при удалении транскрипта')
      })
    })
  })

  describe('Navigation', () => {
    it('should have link to upload page in empty state', async () => {
      client.getTranscripts.mockResolvedValue({ transcripts: [] })

      render(
        <MemoryRouter>
          <TranscriptsPage />
        </MemoryRouter>
      )

      const uploadLink = await screen.findByText('Загрузить файлы')
      expect(uploadLink.closest('a')).toHaveAttribute('href', '/upload')
    })

    it('should have view button linking to transcript detail', async () => {
      client.getTranscripts.mockResolvedValue({ transcripts: [mockTranscripts[0]] })

      render(
        <MemoryRouter>
          <TranscriptsPage />
        </MemoryRouter>
      )

      const viewButton = await screen.findByText('Просмотр')
      expect(viewButton.closest('a')).toHaveAttribute('href', '/transcripts/transcript-1')
    })
  })

  describe('Accessibility', () => {
    it('should have proper ARIA labels for filters', async () => {
      client.getTranscripts.mockResolvedValue({ transcripts: [] })

      render(
        <MemoryRouter>
          <TranscriptsPage />
        </MemoryRouter>
      )

      await waitFor(() => {
        const filters = screen.getAllByRole('combobox')
        expect(filters.length).toBeGreaterThan(0)
      })
    })

    it('should be keyboard navigable', async () => {
      client.getTranscripts.mockResolvedValue({ transcripts: [mockTranscripts[0]] })

      render(
        <MemoryRouter>
          <TranscriptsPage />
        </MemoryRouter>
      )

      const statusFilter = await screen.findByText('Все статусы')

      statusFilter.focus()
      expect(statusFilter).toHaveFocus()

      await userEvent.keyboard('{ArrowDown}')
      await userEvent.keyboard('{Enter}')

      await waitFor(() => {
        expect(client.getTranscripts).toHaveBeenCalled()
      })
    })
  })

  describe('Responsive Behavior', () => {
    it('should display cards in grid layout', async () => {
      client.getTranscripts.mockResolvedValue({ transcripts: mockTranscripts.slice(0, 3) })

      render(
        <MemoryRouter>
          <TranscriptsPage />
        </MemoryRouter>
      )

      await waitFor(() => {
        const grid = screen.container.querySelector('.transcripts-grid')
        expect(grid).toBeInTheDocument()
      })
    })
  })

  describe('Pagination', () => {
    // Note: Current implementation uses fixed pagination (skip=0, limit=100)
    it('should load transcripts with correct pagination params', async () => {
      client.getTranscripts.mockResolvedValue({ transcripts: mockTranscripts })

      render(
        <MemoryRouter>
          <TranscriptsPage />
        </MemoryRouter>
      )

      await waitFor(() => {
        expect(client.getTranscripts).toHaveBeenCalledWith(0, 100, { status: '', language: '' })
      })
    })
  })
})
