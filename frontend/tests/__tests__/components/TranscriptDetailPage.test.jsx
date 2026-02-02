import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import TranscriptDetailPage from '../../../src/pages/TranscriptDetailPage'
import * as client from '../../../src/api/client'

// Mock the API client
vi.mock('../../../src/api/client', () => ({
  getTranscript: vi.fn(),
  getJobs: vi.fn(),
  getSummaries: vi.fn(),
  createSummary: vi.fn(),
  getTranscriptIndexStatus: vi.fn(),
  reindexTranscript: vi.fn(),
  translateTranscript: vi.fn()
}))

// Mock SummaryCreateModal
vi.mock('../../../src/components/SummaryCreateModal', () => ({
  default: ({ isOpen, onClose, onSubmit }) => {
    if (!isOpen) return null
    return (
      <div data-testid="summary-modal">
        <button onClick={() => onSubmit({ template: 'meeting' })}>Submit Summary</button>
        <button onClick={onClose}>Close Modal</button>
      </div>
    )
  }
}))

const mockNavigate = vi.fn()
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom')
  return {
    ...actual,
    useNavigate: () => mockNavigate,
    useParams: () => ({ id: 'test-transcript-1' })
  }
})

const mockTranscript = {
  id: 'test-transcript-1',
  original_filename: 'meeting.mp3',
  status: 'completed',
  language: 'en',
  file_size: 1024000,
  created_at: '2024-01-15T10:30:00',
  transcription_text: 'This is the meeting transcript text.',
  transcription_json: { segments: [{ start: 0, end: 1, text: 'Test segment' }] },
  transcription_srt: '1\n00:00:00,000 --> 00:00:01,000\nTest segment',
  extra_metadata: {}
}

const mockJobs = [
  {
    id: 'job-1',
    job_type: 'transcription',
    status: 'completed',
    progress: 1.0,
    created_at: '2024-01-15T10:30:00',
    updated_at: '2024-01-15T10:35:00'
  }
]

const mockSummaries = [
  {
    id: 'summary-1',
    transcript_id: 'test-transcript-1',
    summary_text: 'Meeting summary with key points.',
    model_used: 'GigaChat/GigaChat-2-Max',
    summary_template: 'meeting',
    created_at: '2024-01-15T10:40:00'
  }
]

describe('TranscriptDetailPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.useFakeTimers()
    client.getTranscript.mockResolvedValue(mockTranscript)
    client.getJobs.mockResolvedValue(mockJobs)
    client.getSummaries.mockResolvedValue(mockSummaries)
    client.getTranscriptIndexStatus.mockResolvedValue({ indexed: true })
    client.translateTranscript.mockResolvedValue({ message: 'Translation started' })
    client.reindexTranscript.mockResolvedValue({ message: 'Reindexing started' })
  })

  afterEach(() => {
    vi.runOnlyPendingTimers()
    vi.useRealTimers()
  })

  const renderComponent = () => {
    return render(
      <MemoryRouter initialEntries={['/transcripts/test-transcript-1']}>
        <Routes>
          <Route path="/transcripts/:id" element={<TranscriptDetailPage />} />
        </Routes>
      </MemoryRouter>
    )
  }

  describe('Rendering', () => {
    it('should render loading state initially', () => {
      client.getTranscript.mockImplementation(() => new Promise(() => {}))

      renderComponent()

      expect(screen.getByText('Загрузка транскрипта...')).toBeInTheDocument()
    })

    it('should render transcript details when loaded', async () => {
      renderComponent()

      await waitFor(() => {
        expect(screen.getByText('meeting.mp3')).toBeInTheDocument()
        expect(screen.getByText('EN')).toBeInTheDocument()
        expect(screen.getByText(/1\.00 MB/)).toBeInTheDocument()
      })
    })

    it('should render error state when transcript not found', async () => {
      client.getTranscript.mockResolvedValue(null)

      renderComponent()

      await waitFor(() => {
        expect(screen.getByText('Транскрипт не найден')).toBeInTheDocument()
      })
    })

    it('should display transcript metadata', async () => {
      renderComponent()

      await waitFor(() => {
        expect(screen.getByText('Создан')).toBeInTheDocument()
        expect(screen.getByText('Язык')).toBeInTheDocument()
        expect(screen.getByText('Размер файла')).toBeInTheDocument()
        expect(screen.getByText('Статус')).toBeInTheDocument()
      })
    })
  })

  describe('Transcript Display', () => {
    it('should display transcription text in text tab', async () => {
      renderComponent()

      await waitFor(() => {
        expect(screen.getByText('This is the meeting transcript text.')).toBeInTheDocument()
      })
    })

    it('should switch between tabs', async () => {
      renderComponent()

      await waitFor(() => {
        expect(screen.getByText('Текст')).toHaveClass('active')
      })

      const jsonButton = screen.getByText('JSON')
      fireEvent.click(jsonButton)

      await waitFor(() => {
        expect(jsonButton).toHaveClass('active')
        expect(screen.getByText('{')).toBeInTheDocument()
      })

      const srtButton = screen.getByText('SRT')
      fireEvent.click(srtButton)

      await waitFor(() => {
        expect(srtButton).toHaveClass('active')
        expect(screen.getByText(/00:00:00/)).toBeInTheDocument()
      })
    })

    it('should show summary tab when summaries exist', async () => {
      renderComponent()

      await waitFor(() => {
        expect(screen.getByText('Протокол')).toBeInTheDocument()
      })

      const summaryButton = screen.getByText('Протокол')
      fireEvent.click(summaryButton)

      await waitFor(() => {
        expect(screen.getByText('Meeting summary with key points.')).toBeInTheDocument()
      })
    })
  })

  describe('Text Editing', () => {
    it('should have link to edit page', async () => {
      renderComponent()

      await waitFor(() => {
        const editLink = screen.getByText('Редактировать')
        expect(editLink.closest('a')).toHaveAttribute('href', '/transcripts/test-transcript-1/edit')
      })
    })
  })

  describe('Summary Display', () => {
    it('should display summaries section', async () => {
      renderComponent()

      await waitFor(() => {
        expect(screen.getByText('Протоколы встреч')).toBeInTheDocument()
      })
    })

    it('should display summary content', async () => {
      renderComponent()

      await waitFor(() => {
        expect(screen.getByText('Meeting summary with key points.')).toBeInTheDocument()
      })
    })

    it('should show create summary modal when button clicked', async () => {
      renderComponent()

      await waitFor(() => {
        expect(screen.getByText('Создать протокол')).toBeInTheDocument()
      })

      const createButton = screen.getByText('Создать протокол')
      fireEvent.click(createButton)

      await waitFor(() => {
        expect(screen.getByTestId('summary-modal')).toBeInTheDocument()
      })
    })

    it('should submit summary creation', async () => {
      client.createSummary.mockResolvedValue({})

      renderComponent()

      await waitFor(() => {
        const createButton = screen.getByText('Создать протокол')
        fireEvent.click(createButton)
      })

      await waitFor(() => {
        const submitButton = screen.getByText('Submit Summary')
        fireEvent.click(submitButton)
      })

      await waitFor(() => {
        expect(client.createSummary).toHaveBeenCalledWith('test-transcript-1', {
          template: 'meeting'
        })
      })
    })

    it('should toggle summary visibility', async () => {
      renderComponent()

      await waitFor(() => {
        expect(screen.getByText('Meeting summary with key points.')).toBeInTheDocument()
      })

      const hideButton = screen.getAllByText('Hide')[0]
      fireEvent.click(hideButton)

      await waitFor(() => {
        expect(screen.queryByText('Meeting summary with key points.')).not.toBeInTheDocument()
        expect(screen.getByText('Показать протокол')).toBeInTheDocument()
      })
    })

    it('should expand long summaries', async () => {
      const longSummary = {
        ...mockSummaries[0],
        summary_text: 'A'.repeat(300) // Longer than preview length of 200
      }
      client.getSummaries.mockResolvedValue([longSummary])

      renderComponent()

      await waitFor(() => {
        expect(screen.getByText('Показать больше')).toBeInTheDocument()
      })

      const expandButton = screen.getByText('Показать больше')
      fireEvent.click(expandButton)

      await waitFor(() => {
        expect(screen.getByText('Показать меньше')).toBeInTheDocument()
      })
    })
  })

  describe('Translation', () => {
    it('should display translation section', async () => {
      renderComponent()

      await waitFor(() => {
        expect(screen.getByText('Перевод')).toBeInTheDocument()
      })
    })

    it('should show translation button for non-Russian transcripts', async () => {
      renderComponent()

      await waitFor(() => {
        expect(screen.getByText('Перевести на русский')).toBeInTheDocument()
      })
    })

    it('should trigger translation when button clicked', async () => {
      renderComponent()

      await waitFor(() => {
        const translateButton = screen.getByText('Перевести на русский')
        fireEvent.click(translateButton)
      })

      await waitFor(() => {
        expect(client.translateTranscript).toHaveBeenCalledWith(
          'test-transcript-1',
          'ru',
          'GigaChat/GigaChat-2-Max'
        )
      })
    })

    it('should show translation progress', async () => {
      client.translateTranscript.mockResolvedValue({ already_translated: false })
      client.getJobs.mockResolvedValue([
        {
          job_type: 'translation',
          status: 'processing',
          progress: 0.5
        }
      ])

      renderComponent()

      const translateButton = await screen.findByText('Перевести на русский')
      fireEvent.click(translateButton)

      await waitFor(() => {
        expect(screen.getByText(/Перевод в процессе\.\.\./)).toBeInTheDocument()
      }, { timeout: 3000 })
    })

    it('should display language switcher when translated', async () => {
      const translatedTranscript = {
        ...mockTranscript,
        extra_metadata: {
          translated: true,
          translated_transcription_json: { segments: [{ start: 0, end: 1, text: 'Переведенный текст' }] }
        }
      }
      client.getTranscript.mockResolvedValue(translatedTranscript)

      renderComponent()

      await waitFor(() => {
        expect(screen.getByText('Русский (RU)')).toBeInTheDocument()
      })
    })

    it('should allow selecting translation model', async () => {
      renderComponent()

      await waitFor(() => {
        const modelSelect = screen.getByLabelText('Модель для перевода:')
        expect(modelSelect).toBeInTheDocument()
      })

      const modelSelect = screen.getByLabelText('Модель для перевода:')
      fireEvent.change(modelSelect, { target: { value: 'Qwen/Qwen3-235B-A22B-Instruct-2507' } })

      await waitFor(() => {
        expect(modelSelect).toHaveValue('Qwen/Qwen3-235B-A22B-Instruct-2507')
      })
    })
  })

  describe('RAG Indexing', () => {
    it('should display RAG indexing section', async () => {
      renderComponent()

      await waitFor(() => {
        expect(screen.getByText('Индексация RAG')).toBeInTheDocument()
      })
    })

    it('should show indexed status when transcript is indexed', async () => {
      renderComponent()

      await waitFor(() => {
        expect(screen.getByText('Проиндексирован')).toBeInTheDocument()
      })
    })

    it('should show not indexed status when transcript is not indexed', async () => {
      client.getTranscriptIndexStatus.mockResolvedValue({
        indexed: false,
        reason: 'Not yet indexed'
      })

      renderComponent()

      await waitFor(() => {
        expect(screen.getByText('Не проиндексирован')).toBeInTheDocument()
      })
    })

    it('should trigger reindexing when button clicked', async () => {
      renderComponent()

      await waitFor(() => {
        const reindexButton = screen.getByText('Индексировать для RAG')
        fireEvent.click(reindexButton)
      })

      await waitFor(() => {
        expect(client.reindexTranscript).toHaveBeenCalledWith('test-transcript-1')
      })
    })

    it('should show reindexing progress', async () => {
      client.getJobs.mockResolvedValue([
        {
          job_type: 'indexing',
          status: 'processing',
          progress: 0.7
        }
      ])

      renderComponent()

      await waitFor(() => {
        expect(screen.getByText(/Индексация в процессе\.\.\. 70%/)).toBeInTheDocument()
      })
    })
  })

  describe('Download Actions', () => {
    it('should download text', async () => {
      const mockBlob = new Blob(['test'], { type: 'text/plain' })
      global.URL.createObjectURL = vi.fn(() => 'mock-url')
      global.URL.revokeObjectURL = vi.fn()

      const createElementSpy = vi.spyOn(document, 'createElement')
      const linkMock = {
        href: '',
        download: '',
        click: vi.fn(),
        style: {}
      }
      createElementSpy.mockReturnValue(linkMock)

      renderComponent()

      const downloadButton = await screen.findByText('Скачать текст')
      fireEvent.click(downloadButton)

      await waitFor(() => {
        expect(linkMock.click).toHaveBeenCalled()
      })
    })

    it('should download JSON', async () => {
      const linkMock = {
        href: '',
        download: '',
        click: vi.fn(),
        style: {}
      }
      vi.spyOn(document, 'createElement').mockReturnValue(linkMock)
      global.URL.createObjectURL = vi.fn(() => 'mock-url')

      renderComponent()

      const downloadButton = await screen.findByText('Скачать JSON')
      fireEvent.click(downloadButton)

      await waitFor(() => {
        expect(linkMock.click).toHaveBeenCalled()
      })
    })

    it('should download SRT', async () => {
      const linkMock = {
        href: '',
        download: '',
        click: vi.fn(),
        style: {}
      }
      vi.spyOn(document, 'createElement').mockReturnValue(linkMock)
      global.URL.createObjectURL = vi.fn(() => 'mock-url')

      renderComponent()

      const downloadButton = await screen.findByText('Скачать SRT')
      fireEvent.click(downloadButton)

      await waitFor(() => {
        expect(linkMock.click).toHaveBeenCalled()
      })
    })
  })

  describe('Jobs Display', () => {
    it('should display jobs section when jobs exist', async () => {
      renderComponent()

      await waitFor(() => {
        expect(screen.getByText('Задачи обработки')).toBeInTheDocument()
      })
    })

    it('should display job type labels', async () => {
      renderComponent()

      await waitFor(() => {
        expect(screen.getByText('Транскрибация')).toBeInTheDocument()
      })
    })

    it('should display job status', async () => {
      renderComponent()

      await waitFor(() => {
        expect(screen.getByText('completed')).toBeInTheDocument()
      })
    })

    it('should display job duration for completed jobs', async () => {
      renderComponent()

      await waitFor(() => {
        expect(screen.getByText(/5 мин/)).toBeInTheDocument()
      })
    })
  })

  describe('Copy Button', () => {
    it('should copy text to clipboard', async () => {
      renderComponent()

      await waitFor(() => {
        const copyButton = screen.getByText('Копировать')
        fireEvent.click(copyButton)
      })

      await waitFor(() => {
        expect(navigator.clipboard.writeText).toHaveBeenCalled()
      })
    })

    it('should show copied state temporarily', async () => {
      renderComponent()

      await waitFor(() => {
        const copyButton = screen.getByText('Копировать')
        fireEvent.click(copyButton)
      })

      await waitFor(() => {
        expect(screen.getByText('Скопировано')).toBeInTheDocument()
      })

      vi.advanceTimersByTime(2500)

      await waitFor(() => {
        expect(screen.queryByText('Скопировано')).not.toBeInTheDocument()
      })
    })
  })

  describe('Navigation', () => {
    it('should navigate back to transcripts when back button clicked', async () => {
      renderComponent()

      const backButton = await screen.findByText('Назад')
      fireEvent.click(backButton)

      expect(mockNavigate).toHaveBeenCalledWith('/transcripts')
    })
  })

  describe('Polling', () => {
    it('should poll for job updates during processing', async () => {
      const processingTranscript = { ...mockTranscript, status: 'processing' }
      client.getTranscript.mockResolvedValue(processingTranscript)

      renderComponent()

      await waitFor(() => {
        expect(client.getJobs).toHaveBeenCalled()
      })

      vi.advanceTimersByTime(1000)

      await waitFor(() => {
        expect(client.getJobs).toHaveBeenCalledTimes(2)
      })
    })
  })

  describe('Error Handling', () => {
    it('should display error state for failed transcription', async () => {
      const failedTranscript = { ...mockTranscript, status: 'failed' }
      client.getTranscript.mockResolvedValue(failedTranscript)

      renderComponent()

      await waitFor(() => {
        expect(screen.getByText(/Транскрибация не удалась/)).toBeInTheDocument()
      })
    })

    it('should show translation error', async () => {
      client.getJobs.mockResolvedValue([
        {
          job_type: 'translation',
          status: 'failed',
          error_message: 'Translation failed'
        }
      ])

      renderComponent()

      await waitFor(() => {
        expect(screen.getByText(/Translation failed/)).toBeInTheDocument()
      })
    })
  })

  describe('Accessibility', () => {
    it('should have proper heading hierarchy', async () => {
      renderComponent()

      await waitFor(() => {
        const h1 = screen.getByRole('heading', { level: 1 })
        expect(h1).toHaveTextContent('meeting.mp3')
      })
    })

    it('should be keyboard navigable', async () => {
      renderComponent()

      await waitFor(() => {
        const textTab = screen.getByText('Текст')
        textTab.focus()
        expect(textTab).toHaveFocus()
      })
    })
  })

  describe('Loading States', () => {
    it('should show loading state for summaries', async () => {
      client.getSummaries.mockImplementation(() => new Promise(() => {}))

      renderComponent()

      await waitFor(() => {
        expect(screen.getByText('Загрузка протоколов встреч...')).toBeInTheDocument()
      })
    })
  })
})
