import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, fireEvent, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import UploadPage from '../../../src/pages/UploadPage'
import * as client from '../../../src/api/client'

// Mock the API client
vi.mock('../../../src/api/client', () => ({
  uploadFile: vi.fn(),
  getTranscriptJobs: vi.fn()
}))

// Mock react-router-dom
const mockNavigate = vi.fn()
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom')
  return {
    ...actual,
    useNavigate: () => mockNavigate
  }
})

describe('UploadPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.runOnlyPendingTimers()
    vi.useRealTimers()
  })

  describe('Rendering', () => {
    it('should render the upload page with title and drop zone', () => {
      render(
        <MemoryRouter>
          <UploadPage />
        </MemoryRouter>
      )

      expect(screen.getByText('Загрузка аудио файлов')).toBeInTheDocument()
      expect(screen.getByText(/Перетащите аудио файлы сюда или нажмите для выбора/)).toBeInTheDocument()
    })

    it('should display supported formats', () => {
      render(
        <MemoryRouter>
          <UploadPage />
        </MemoryRouter>
      )

      expect(screen.getByText('Поддерживаемые форматы:')).toBeInTheDocument()
      expect(screen.getByText('MP3')).toBeInTheDocument()
      expect(screen.getByText('WAV')).toBeInTheDocument()
      expect(screen.getByText('WEBM')).toBeInTheDocument()
    })

    it('should render language selector', () => {
      render(
        <MemoryRouter>
          <UploadPage />
        </MemoryRouter>
      )

      expect(screen.getByText('Язык:')).toBeInTheDocument()
      expect(screen.getByText('Русский (рекомендуется)')).toBeInTheDocument()
      expect(screen.getByText('English')).toBeInTheDocument()
      expect(screen.getByText('Автоопределение (может переводить на английский!)')).toBeInTheDocument()
    })
  })

  describe('File Drag and Drop', () => {
    it('should accept valid audio files on drop', async () => {
      const file = new File(['audio content'], 'test.mp3', { type: 'audio/mp3' })
      render(
        <MemoryRouter>
          <UploadPage />
        </MemoryRouter>
      )

      const dropZone = screen.getByText(/Перетащите аудио файлы/).closest('.drop-zone')

      fireEvent.drop(dropZone, {
        dataTransfer: {
          files: [file]
        }
      })

      await waitFor(() => {
        expect(screen.getByText('test.mp3')).toBeInTheDocument()
        expect(screen.getByText(/Выбранные файлы \(1\)/)).toBeInTheDocument()
      })
    })

    it('should accept multiple files on drop', async () => {
      const file1 = new File(['audio content'], 'test1.mp3', { type: 'audio/mp3' })
      const file2 = new File(['audio content'], 'test2.wav', { type: 'audio/wav' })
      render(
        <MemoryRouter>
          <UploadPage />
        </MemoryRouter>
      )

      const dropZone = screen.getByText(/Перетащите аудио файлы/).closest('.drop-zone')

      fireEvent.drop(dropZone, {
        dataTransfer: {
          files: [file1, file2]
        }
      })

      await waitFor(() => {
        expect(screen.getByText('test1.mp3')).toBeInTheDocument()
        expect(screen.getByText('test2.wav')).toBeInTheDocument()
        expect(screen.getByText(/Выбранные файлы \(2\)/)).toBeInTheDocument()
      })
    })

    it('should reject non-audio files', async () => {
      const file = new File(['document content'], 'test.pdf', { type: 'application/pdf' })
      render(
        <MemoryRouter>
          <UploadPage />
        </MemoryRouter>
      )

      const dropZone = screen.getByText(/Перетащите аудио файлы/).closest('.drop-zone')

      fireEvent.drop(dropZone, {
        dataTransfer: {
          files: [file]
        }
      })

      await waitFor(() => {
        expect(screen.queryByText('test.pdf')).not.toBeInTheDocument()
        expect(screen.queryByText(/Выбранные файлы/)).not.toBeInTheDocument()
      })
    })

    it('should handle drag over events', () => {
      render(
        <MemoryRouter>
          <UploadPage />
        </MemoryRouter>
      )

      const dropZone = screen.getByText(/Перетащите аудио файлы/).closest('.drop-zone')

      const preventDefault = vi.fn()
      fireEvent.dragOver(dropZone, { preventDefault })

      expect(preventDefault).toHaveBeenCalled()
    })

    it('should handle drag enter events', () => {
      render(
        <MemoryRouter>
          <UploadPage />
        </MemoryRouter>
      )

      const dropZone = screen.getByText(/Перетащите аудио файлы/).closest('.drop-zone')

      const preventDefault = vi.fn()
      fireEvent.dragEnter(dropZone, { preventDefault })

      expect(preventDefault).toHaveBeenCalled()
    })
  })

  describe('File Selection Dialog', () => {
    it('should open file selector when clicking drop zone', async () => {
      render(
        <MemoryRouter>
          <UploadPage />
        </MemoryRouter>
      )

      const fileInput = document.querySelector('input[type="file"]')
      expect(fileInput).toBeInTheDocument()
      expect(fileInput).toHaveAttribute('multiple')
      expect(fileInput).toHaveAttribute('accept', 'audio/*,video/*')
    })

    it('should handle file selection via input', async () => {
      const file = new File(['audio content'], 'test.mp3', { type: 'audio/mp3' })
      render(
        <MemoryRouter>
          <UploadPage />
        </MemoryRouter>
      )

      const fileInput = document.querySelector('input[type="file"]')

      await userEvent.upload(fileInput, file)

      await waitFor(() => {
        expect(screen.getByText('test.mp3')).toBeInTheDocument()
      })
    })
  })

  describe('Upload Progress', () => {
    it('should show upload progress while uploading', async () => {
      const file = new File(['audio content'], 'test.mp3', { type: 'audio/mp3' })
      const mockUploadProgress = vi.fn()

      client.uploadFile.mockImplementation((file, language, onProgress) => {
        onProgress({ loaded: 50, total: 100 })
        onProgress({ loaded: 100, total: 100 })
        return Promise.resolve({ id: 'transcript-1' })
      })

      render(
        <MemoryRouter>
          <UploadPage />
        </MemoryRouter>
      )

      const fileInput = document.querySelector('input[type="file"]')
      await userEvent.upload(fileInput, file)

      const uploadButton = await screen.findByText(/Загрузить 1 файл/)
      fireEvent.click(uploadButton)

      await waitFor(() => {
        expect(screen.getByText(/Загрузка:/)).toBeInTheDocument()
      })
    })

    it('should show transcription progress after upload', async () => {
      const file = new File(['audio content'], 'test.mp3', { type: 'audio/mp3' })

      client.uploadFile.mockResolvedValue({ id: 'transcript-1' })
      client.getTranscriptJobs.mockResolvedValue([
        {
          job_type: 'transcription',
          status: 'processing',
          progress: 0.5
        }
      ])

      render(
        <MemoryRouter>
          <UploadPage />
        </MemoryRouter>
      )

      const fileInput = document.querySelector('input[type="file"]')
      await userEvent.upload(fileInput, file)

      const uploadButton = await screen.findByText(/Загрузить 1 файл/)
      fireEvent.click(uploadButton)

      await waitFor(() => {
        expect(screen.getByText(/Транскрибация:/)).toBeInTheDocument()
      }, { timeout: 3000 })
    })

    it('should show completed status when transcription finishes', async () => {
      const file = new File(['audio content'], 'test.mp3', { type: 'audio/mp3' })

      client.uploadFile.mockResolvedValue({ id: 'transcript-1' })
      client.getTranscriptJobs.mockResolvedValue([
        {
          job_type: 'transcription',
          status: 'completed',
          progress: 1.0
        }
      ])

      render(
        <MemoryRouter>
          <UploadPage />
        </MemoryRouter>
      )

      const fileInput = document.querySelector('input[type="file"]')
      await userEvent.upload(fileInput, file)

      const uploadButton = await screen.findByText(/Загрузить 1 файл/)
      fireEvent.click(uploadButton)

      await waitFor(() => {
        expect(screen.getByText(/Транскрибировано/)).toBeInTheDocument()
      }, { timeout: 3000 })
    })
  })

  describe('Polling for Transcription Status', () => {
    it('should poll for transcription status', async () => {
      const file = new File(['audio content'], 'test.mp3', { type: 'audio/mp3' })

      client.uploadFile.mockResolvedValue({ id: 'transcript-1' })
      client.getTranscriptJobs
        .mockResolvedValueOnce([
          { job_type: 'transcription', status: 'queued', progress: 0 }
        ])
        .mockResolvedValueOnce([
          { job_type: 'transcription', status: 'processing', progress: 0.5 }
        ])
        .mockResolvedValueOnce([
          { job_type: 'transcription', status: 'completed', progress: 1.0 }
        ])

      render(
        <MemoryRouter>
          <UploadPage />
        </MemoryRouter>
      )

      const fileInput = document.querySelector('input[type="file"]')
      await userEvent.upload(fileInput, file)

      const uploadButton = await screen.findByText(/Загрузить 1 файл/)
      fireEvent.click(uploadButton)

      await waitFor(() => {
        expect(client.getTranscriptJobs).toHaveBeenCalled()
      }, { timeout: 3000 })
    })
  })

  describe('Error States', () => {
    it('should display upload error', async () => {
      const file = new File(['audio content'], 'test.mp3', { type: 'audio/mp3' })

      client.uploadFile.mockRejectedValue({
        response: { data: { detail: 'Upload failed' } }
      })

      render(
        <MemoryRouter>
          <UploadPage />
        </MemoryRouter>
      )

      const fileInput = document.querySelector('input[type="file"]')
      await userEvent.upload(fileInput, file)

      const uploadButton = await screen.findByText(/Загрузить 1 файл/)
      fireEvent.click(uploadButton)

      await waitFor(() => {
        expect(screen.getByText(/Upload failed/)).toBeInTheDocument()
      })
    })

    it('should display transcription error', async () => {
      const file = new File(['audio content'], 'test.mp3', { type: 'audio/mp3' })

      client.uploadFile.mockResolvedValue({ id: 'transcript-1' })
      client.getTranscriptJobs.mockResolvedValue([
        {
          job_type: 'transcription',
          status: 'failed',
          error_message: 'Transcription failed'
        }
      ])

      render(
        <MemoryRouter>
          <UploadPage />
        </MemoryRouter>
      )

      const fileInput = document.querySelector('input[type="file"]')
      await userEvent.upload(fileInput, file)

      const uploadButton = await screen.findByText(/Загрузить 1 файл/)
      fireEvent.click(uploadButton)

      await waitFor(() => {
        expect(screen.getByText(/Transcription failed/)).toBeInTheDocument()
      }, { timeout: 3000 })
    })
  })

  describe('Language Selection', () => {
    it('should change selected language', async () => {
      render(
        <MemoryRouter>
          <UploadPage />
        </MemoryRouter>
      )

      const select = screen.getByLabelText('Язык:')
      expect(select).toHaveValue('ru')

      fireEvent.change(select, { target: { value: 'en' } })
      expect(select).toHaveValue('en')
    })

    it('should display language hint', () => {
      render(
        <MemoryRouter>
          <UploadPage />
        </MemoryRouter>
      )

      expect(screen.getByText(/Важно: при "Автоопределении" Whisper может переводить на английский/)).toBeInTheDocument()
    })
  })

  describe('File Format Validation', () => {
    const supportedFormats = [
      { filename: 'test.mp3', type: 'audio/mp3', valid: true },
      { filename: 'test.mp4', type: 'video/mp4', valid: true },
      { filename: 'test.mpeg', type: 'video/mpeg', valid: true },
      { filename: 'test.mpga', type: 'audio/mpeg', valid: true },
      { filename: 'test.m4a', type: 'audio/x-m4a', valid: true },
      { filename: 'test.wav', type: 'audio/wav', valid: true },
      { filename: 'test.webm', type: 'audio/webm', valid: true },
      { filename: 'test.pdf', type: 'application/pdf', valid: false },
      { filename: 'test.doc', type: 'application/msword', valid: false },
      { filename: 'test.txt', type: 'text/plain', valid: false }
    ]

    supportedFormats.forEach(({ filename, type, valid }) => {
      it(`${valid ? 'accepts' : 'rejects'} ${filename}`, async () => {
        const file = new File(['content'], filename, { type })
        render(
          <MemoryRouter>
            <UploadPage />
          </MemoryRouter>
        )

        const fileInput = document.querySelector('input[type="file"]')
        await userEvent.upload(fileInput, file)

        if (valid) {
          await waitFor(() => {
            expect(screen.getByText(filename)).toBeInTheDocument()
          })
        } else {
          await waitFor(() => {
            expect(screen.queryByText(filename)).not.toBeInTheDocument()
          })
        }
      })
    })
  })

  describe('File Removal', () => {
    it('should remove file when clicking remove button', async () => {
      const file = new File(['audio content'], 'test.mp3', { type: 'audio/mp3' })
      render(
        <MemoryRouter>
          <UploadPage />
        </MemoryRouter>
      )

      const fileInput = document.querySelector('input[type="file"]')
      await userEvent.upload(fileInput, file)

      await waitFor(() => {
        expect(screen.getByText('test.mp3')).toBeInTheDocument()
      })

      const removeButton = screen.getByRole('button', { name: '' }).querySelector('.btn-remove') || screen.getByRole('button')
      fireEvent.click(removeButton)

      await waitFor(() => {
        expect(screen.queryByText('test.mp3')).not.toBeInTheDocument()
      })
    })

    it('should not show remove button for files being processed', async () => {
      const file = new File(['audio content'], 'test.mp3', { type: 'audio/mp3' })

      client.uploadFile.mockImplementation((file, language, onProgress) => {
        return new Promise((resolve) => {
          onProgress({ loaded: 50, total: 100 })
          setTimeout(() => resolve({ id: 'transcript-1' }), 100)
        })
      })

      render(
        <MemoryRouter>
          <UploadPage />
        </MemoryRouter>
      )

      const fileInput = document.querySelector('input[type="file"]')
      await userEvent.upload(fileInput, file)

      const uploadButton = await screen.findByText(/Загрузить 1 файл/)
      fireEvent.click(uploadButton)

      await waitFor(() => {
        expect(screen.queryByText(/Загрузка\.\.\./)).toBeInTheDocument()
        const removeButtons = screen.container.querySelectorAll('.btn-remove')
        expect(removeButtons.length).toBe(0)
      })
    })
  })

  describe('Upload Button', () => {
    it('should be disabled when no files are selected', () => {
      render(
        <MemoryRouter>
          <UploadPage />
        </MemoryRouter>
      )

      const uploadButton = screen.queryByText(/Загрузить/)
      expect(uploadButton).not.toBeInTheDocument()
    })

    it('should show correct text for single file', async () => {
      const file = new File(['audio content'], 'test.mp3', { type: 'audio/mp3' })
      render(
        <MemoryRouter>
          <UploadPage />
        </MemoryRouter>
      )

      const fileInput = document.querySelector('input[type="file"]')
      await userEvent.upload(fileInput, file)

      await waitFor(() => {
        expect(screen.getByText('Загрузить 1 файл')).toBeInTheDocument()
      })
    })

    it('should show correct text for multiple files', async () => {
      const file1 = new File(['audio content'], 'test1.mp3', { type: 'audio/mp3' })
      const file2 = new File(['audio content'], 'test2.mp3', { type: 'audio/mp3' })
      render(
        <MemoryRouter>
          <UploadPage />
        </MemoryRouter>
      )

      const fileInput = document.querySelector('input[type="file"]')
      await userEvent.upload(fileInput, file1)
      await userEvent.upload(fileInput, file2)

      await waitFor(() => {
        expect(screen.getByText('Загрузить 2 файла')).toBeInTheDocument()
      })
    })

    it('should be disabled while uploading', async () => {
      const file = new File(['audio content'], 'test.mp3', { type: 'audio/mp3' })

      client.uploadFile.mockImplementation(() => new Promise(resolve => setTimeout(() => resolve({ id: 'test' }), 1000)))

      render(
        <MemoryRouter>
          <UploadPage />
        </MemoryRouter>
      )

      const fileInput = document.querySelector('input[type="file"]')
      await userEvent.upload(fileInput, file)

      const uploadButton = await screen.findByText(/Загрузить 1 файл/)
      fireEvent.click(uploadButton)

      await waitFor(() => {
        expect(uploadButton).toBeDisabled()
      })
    })
  })

  describe('Accessibility', () => {
    it('should have proper ARIA labels', () => {
      render(
        <MemoryRouter>
          <UploadPage />
        </MemoryRouter>
      )

      const fileInput = document.querySelector('input[type="file"]')
      expect(fileInput).toBeInTheDocument()

      const languageSelect = screen.getByLabelText('Язык:')
      expect(languageSelect).toBeInTheDocument()
    })

    it('should be keyboard navigable', async () => {
      render(
        <MemoryRouter>
          <UploadPage />
        </MemoryRouter>
      )

      const languageSelect = screen.getByLabelText('Язык:')
      languageSelect.focus()
      expect(languageSelect).toHaveFocus()

      await userEvent.keyboard('{ArrowDown}')
      await userEvent.keyboard('{Enter}')

      expect(languageSelect).toHaveValue('en')
    })
  })

  describe('Redirect on Completion', () => {
    it('should redirect to transcripts page when all files complete', async () => {
      const file = new File(['audio content'], 'test.mp3', { type: 'audio/mp3' })

      client.uploadFile.mockResolvedValue({ id: 'transcript-1' })
      client.getTranscriptJobs.mockResolvedValue([
        {
          job_type: 'transcription',
          status: 'completed',
          progress: 1.0
        }
      ])

      render(
        <MemoryRouter>
          <UploadPage />
        </MemoryRouter>
      )

      const fileInput = document.querySelector('input[type="file"]')
      await userEvent.upload(fileInput, file)

      const uploadButton = await screen.findByText(/Загрузить 1 файл/)
      fireEvent.click(uploadButton)

      await waitFor(() => {
        expect(mockNavigate).toHaveBeenCalledWith('/transcripts')
      }, { timeout: 5000 })
    })
  })
})
