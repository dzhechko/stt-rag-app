import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import axios from 'axios'
import {
  uploadFile,
  getTranscripts,
  getTranscript,
  deleteTranscript,
  getJobs,
  getTranscriptJobs,
  createSummary,
  getSummaries,
  getSummary,
  getRAGSessions,
  createRAGSession,
  deleteRAGSession,
  getTranscriptIndexStatus,
  reindexTranscript,
  translateTranscript
} from '../../../src/api/client'
import client from '../../../src/api/client'

// Mock axios
vi.mock('axios', () => {
  const mockAxiosInstance = {
    post: vi.fn(),
    get: vi.fn(),
    delete: vi.fn(),
    defaults: {
      baseURL: '/api'
    }
  }

  return {
    create: vi.fn(() => mockAxiosInstance),
    default: mockAxiosInstance
  }
})

const mockClient = {
  post: vi.fn(),
  get: vi.fn(),
  delete: vi.fn()
}

// Mock the client instance
vi.mock('../../../src/api/client', async () => {
  const actual = await vi.importActual('../../../src/api/client')
  return {
    ...actual,
    default: mockClient
  }
})

describe('API Client', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockClient.post.mockClear()
    mockClient.get.mockClear()
    mockClient.delete.mockClear()
  })

  describe('uploadFile', () => {
    it('should upload file with language', async () => {
      const mockFile = new File(['content'], 'test.mp3', { type: 'audio/mp3' })
      const mockResponse = { data: { id: 'transcript-1' } }
      mockClient.post.mockResolvedValue(mockResponse)

      const onProgress = vi.fn()
      const result = await uploadFile(mockFile, 'ru', onProgress)

      expect(mockClient.post).toHaveBeenCalledWith(
        '/transcripts/upload',
        expect.any(FormData),
        expect.objectContaining({
          headers: {
            'Content-Type': 'multipart/form-data'
          },
          onUploadProgress: onProgress
        })
      )
      expect(result).toEqual({ id: 'transcript-1' })
    })

    it('should upload file without language', async () => {
      const mockFile = new File(['content'], 'test.mp3', { type: 'audio/mp3' })
      const mockResponse = { data: { id: 'transcript-1' } }
      mockClient.post.mockResolvedValue(mockResponse)

      const result = await uploadFile(mockFile, null)

      expect(mockClient.post).toHaveBeenCalled()
      expect(result).toEqual({ id: 'transcript-1' })
    })

    it('should handle upload progress', async () => {
      const mockFile = new File(['content'], 'test.mp3', { type: 'audio/mp3' })
      const mockResponse = { data: { id: 'transcript-1' } }
      mockClient.post.mockImplementation((url, data, config) => {
        if (config.onUploadProgress) {
          config.onUploadProgress({ loaded: 50, total: 100 })
        }
        return Promise.resolve(mockResponse)
      })

      const onProgress = vi.fn()
      await uploadFile(mockFile, 'ru', onProgress)

      expect(onProgress).toHaveBeenCalledWith({ loaded: 50, total: 100 })
    })

    it('should handle upload errors', async () => {
      const mockFile = new File(['content'], 'test.mp3', { type: 'audio/mp3' })
      const mockError = new Error('Upload failed')
      mockClient.post.mockRejectedValue(mockError)

      await expect(uploadFile(mockFile, 'ru')).rejects.toThrow('Upload failed')
    })
  })

  describe('getTranscripts', () => {
    it('should fetch transcripts with default parameters', async () => {
      const mockResponse = {
        data: {
          transcripts: [
            { id: '1', original_filename: 'test.mp3' }
          ]
        }
      }
      mockClient.get.mockResolvedValue(mockResponse)

      const result = await getTranscripts()

      expect(mockClient.get).toHaveBeenCalledWith('/transcripts', {
        params: { skip: 0, limit: 100 }
      })
      expect(result.transcripts).toHaveLength(1)
    })

    it('should fetch transcripts with custom pagination', async () => {
      const mockResponse = { data: { transcripts: [] } }
      mockClient.get.mockResolvedValue(mockResponse)

      await getTranscripts(10, 50)

      expect(mockClient.get).toHaveBeenCalledWith('/transcripts', {
        params: { skip: 10, limit: 50 }
      })
    })

    it('should fetch transcripts with filters', async () => {
      const mockResponse = { data: { transcripts: [] } }
      mockClient.get.mockResolvedValue(mockResponse)

      const filters = { status: 'completed', language: 'ru' }
      await getTranscripts(0, 100, filters)

      expect(mockClient.get).toHaveBeenCalledWith('/transcripts', {
        params: { skip: 0, limit: 100, status: 'completed', language: 'ru' }
      })
    })

    it('should remove empty string filters', async () => {
      const mockResponse = { data: { transcripts: [] } }
      mockClient.get.mockResolvedValue(mockResponse)

      const filters = { status: '', language: 'ru' }
      await getTranscripts(0, 100, filters)

      expect(mockClient.get).toHaveBeenCalledWith('/transcripts', {
        params: { skip: 0, limit: 100, language: 'ru' }
      })
    })

    it('should remove null filters', async () => {
      const mockResponse = { data: { transcripts: [] } }
      mockClient.get.mockResolvedValue(mockResponse)

      const filters = { status: null, language: 'ru' }
      await getTranscripts(0, 100, filters)

      expect(mockClient.get).toHaveBeenCalledWith('/transcripts', {
        params: { skip: 0, limit: 100, language: 'ru' }
      })
    })
  })

  describe('getTranscript', () => {
    it('should fetch single transcript by id', async () => {
      const mockResponse = {
        data: {
          id: 'transcript-1',
          original_filename: 'test.mp3'
        }
      }
      mockClient.get.mockResolvedValue(mockResponse)

      const result = await getTranscript('transcript-1')

      expect(mockClient.get).toHaveBeenCalledWith('/transcripts/transcript-1')
      expect(result).toEqual(mockResponse.data)
    })

    it('should handle transcript not found', async () => {
      const mockError = {
        response: { status: 404, data: { detail: 'Transcript not found' } }
      }
      mockClient.get.mockRejectedValue(mockError)

      await expect(getTranscript('nonexistent')).rejects.toEqual(mockError)
    })
  })

  describe('deleteTranscript', () => {
    it('should delete transcript by id', async () => {
      mockClient.delete.mockResolvedValue({})

      await deleteTranscript('transcript-1')

      expect(mockClient.delete).toHaveBeenCalledWith('/transcripts/transcript-1')
    })

    it('should handle delete errors', async () => {
      const mockError = new Error('Delete failed')
      mockClient.delete.mockRejectedValue(mockError)

      await expect(deleteTranscript('transcript-1')).rejects.toThrow('Delete failed')
    })
  })

  describe('getJobs', () => {
    it('should fetch jobs for transcript', async () => {
      const mockResponse = {
        data: [
          {
            id: 'job-1',
            job_type: 'transcription',
            status: 'completed'
          }
        ]
      }
      mockClient.get.mockResolvedValue(mockResponse)

      const result = await getJobs('transcript-1')

      expect(mockClient.get).toHaveBeenCalledWith('/transcripts/transcript-1/jobs')
      expect(result).toEqual(mockResponse.data)
    })
  })

  describe('getTranscriptJobs', () => {
    it('should be an alias for getJobs', async () => {
      const mockResponse = { data: [] }
      mockClient.get.mockResolvedValue(mockResponse)

      await getTranscriptJobs('transcript-1')

      expect(mockClient.get).toHaveBeenCalledWith('/transcripts/transcript-1/jobs')
    })
  })

  describe('createSummary', () => {
    it('should create summary for transcript', async () => {
      const mockResponse = {
        data: {
          id: 'summary-1',
          summary_text: 'Summary text'
        }
      }
      mockClient.post.mockResolvedValue(mockResponse)

      const summaryData = {
        template: 'meeting',
        model: 'GigaChat/GigaChat-2-Max'
      }
      const result = await createSummary('transcript-1', summaryData)

      expect(mockClient.post).toHaveBeenCalledWith('/summaries', {
        transcript_id: 'transcript-1',
        ...summaryData
      })
      expect(result).toEqual(mockResponse.data)
    })

    it('should handle summary creation errors', async () => {
      const mockError = new Error('Creation failed')
      mockClient.post.mockRejectedValue(mockError)

      await expect(createSummary('transcript-1', {})).rejects.toThrow('Creation failed')
    })
  })

  describe('getSummaries', () => {
    it('should fetch summaries for transcript', async () => {
      const mockResponse = {
        data: [
          {
            id: 'summary-1',
            summary_text: 'Summary 1'
          },
          {
            id: 'summary-2',
            summary_text: 'Summary 2'
          }
        ]
      }
      mockClient.get.mockResolvedValue(mockResponse)

      const result = await getSummaries('transcript-1')

      expect(mockClient.get).toHaveBeenCalledWith('/transcripts/transcript-1/summaries')
      expect(result).toEqual(mockResponse.data)
    })
  })

  describe('getSummary', () => {
    it('should fetch single summary by id', async () => {
      const mockResponse = {
        data: {
          id: 'summary-1',
          summary_text: 'Summary text'
        }
      }
      mockClient.get.mockResolvedValue(mockResponse)

      const result = await getSummary('summary-1')

      expect(mockClient.get).toHaveBeenCalledWith('/summaries/summary-1')
      expect(result).toEqual(mockResponse.data)
    })
  })

  describe('getRAGSessions', () => {
    it('should fetch all RAG sessions', async () => {
      const mockResponse = {
        data: [
          {
            id: 'session-1',
            session_name: 'Test Session'
          }
        ]
      }
      mockClient.get.mockResolvedValue(mockResponse)

      const result = await getRAGSessions()

      expect(mockClient.get).toHaveBeenCalledWith('/rag/sessions')
      expect(result).toEqual(mockResponse.data)
    })
  })

  describe('createRAGSession', () => {
    it('should create new RAG session', async () => {
      const mockResponse = {
        data: {
          id: 'session-1',
          session_name: 'New Session'
        }
      }
      mockClient.post.mockResolvedValue(mockResponse)

      const sessionData = {
        session_name: 'New Session',
        transcript_ids: ['transcript-1', 'transcript-2']
      }
      const result = await createRAGSession(sessionData)

      expect(mockClient.post).toHaveBeenCalledWith('/rag/sessions', sessionData)
      expect(result).toEqual(mockResponse.data)
    })
  })

  describe('deleteRAGSession', () => {
    it('should delete RAG session by id', async () => {
      mockClient.delete.mockResolvedValue({})

      await deleteRAGSession('session-1')

      expect(mockClient.delete).toHaveBeenCalledWith('/rag/sessions/session-1')
    })
  })

  describe('getTranscriptIndexStatus', () => {
    it('should fetch index status for transcript', async () => {
      const mockResponse = {
        data: {
          indexed: true,
          reason: null
        }
      }
      mockClient.get.mockResolvedValue(mockResponse)

      const result = await getTranscriptIndexStatus('transcript-1')

      expect(mockClient.get).toHaveBeenCalledWith('/transcripts/transcript-1/index-status')
      expect(result).toEqual(mockResponse.data)
    })

    it('should return not indexed status', async () => {
      const mockResponse = {
        data: {
          indexed: false,
          reason: 'Not yet indexed'
        }
      }
      mockClient.get.mockResolvedValue(mockResponse)

      const result = await getTranscriptIndexStatus('transcript-1')

      expect(result.indexed).toBe(false)
      expect(result.reason).toBe('Not yet indexed')
    })
  })

  describe('reindexTranscript', () => {
    it('should trigger reindexing for transcript', async () => {
      const mockResponse = {
        data: {
          message: 'Reindexing started'
        }
      }
      mockClient.post.mockResolvedValue(mockResponse)

      const result = await reindexTranscript('transcript-1')

      expect(mockClient.post).toHaveBeenCalledWith('/transcripts/transcript-1/reindex')
      expect(result).toEqual(mockResponse.data)
    })
  })

  describe('translateTranscript', () => {
    it('should translate transcript to target language', async () => {
      const mockResponse = {
        data: {
          message: 'Translation started'
        }
      }
      mockClient.post.mockResolvedValue(mockResponse)

      const result = await translateTranscript('transcript-1', 'ru')

      expect(mockClient.post).toHaveBeenCalledWith('/transcripts/transcript-1/translate', {
        target_language: 'ru'
      })
      expect(result).toEqual(mockResponse.data)
    })

    it('should translate with custom model', async () => {
      const mockResponse = { data: {} }
      mockClient.post.mockResolvedValue(mockResponse)

      await translateTranscript('transcript-1', 'ru', 'Qwen/Qwen3-235B')

      expect(mockClient.post).toHaveBeenCalledWith('/transcripts/transcript-1/translate', {
        target_language: 'ru',
        model: 'Qwen/Qwen3-235B'
      })
    })

    it('should handle already translated response', async () => {
      const mockResponse = {
        data: {
          already_translated: true,
          message: 'Already translated to Russian'
        }
      }
      mockClient.post.mockResolvedValue(mockResponse)

      const result = await translateTranscript('transcript-1', 'ru')

      expect(result.already_translated).toBe(true)
    })
  })

  describe('Error Handling', () => {
    it('should handle network errors', async () => {
      const networkError = new Error('Network Error')
      mockClient.get.mockRejectedValue(networkError)

      await expect(getTranscript('transcript-1')).rejects.toThrow('Network Error')
    })

    it('should handle HTTP error responses', async () => {
      const httpError = {
        response: {
          status: 500,
          data: { detail: 'Internal server error' }
        }
      }
      mockClient.get.mockRejectedValue(httpError)

      try {
        await getTranscript('transcript-1')
      } catch (error) {
        expect(error.response.status).toBe(500)
      }
    })

    it('should handle timeout errors', async () => {
      const timeoutError = new Error('Request timeout')
      mockClient.get.mockRejectedValue(timeoutError)

      await expect(getTranscript('transcript-1')).rejects.toThrow('Request timeout')
    })
  })

  describe('Request/Response Format Validation', () => {
    it('should send correct content type for JSON requests', async () => {
      mockClient.post.mockResolvedValue({ data: {} })

      await createSummary('transcript-1', { template: 'meeting' })

      expect(mockClient.post).toHaveBeenCalledWith(
        '/summaries',
        expect.any(Object),
        expect.not.objectContaining({
          headers: expect.objectContaining({
            'Content-Type': 'multipart/form-data'
          })
        })
      )
    })

    it('should send multipart/form-data for file uploads', async () => {
      const mockFile = new File(['content'], 'test.mp3', { type: 'audio/mp3' })
      mockClient.post.mockResolvedValue({ data: { id: '1' } })

      await uploadFile(mockFile, 'ru')

      expect(mockClient.post).toHaveBeenCalledWith(
        '/transcripts/upload',
        expect.any(FormData),
        expect.objectContaining({
          headers: {
            'Content-Type': 'multipart/form-data'
          }
        })
      )
    })

    it('should return response data correctly', async () => {
      const mockData = {
        id: 'transcript-1',
        original_filename: 'test.mp3'
      }
      mockClient.get.mockResolvedValue({ data: mockData })

      const result = await getTranscript('transcript-1')

      expect(result).toEqual(mockData)
    })
  })

  describe('Default Export', () => {
    it('should export axios client instance', () => {
      expect(client).toBeDefined()
      expect(client.get).toBeDefined()
      expect(client.post).toBeDefined()
      expect(client.delete).toBeDefined()
    })
  })
})
