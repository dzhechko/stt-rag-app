import axios from 'axios'

const API_BASE_URL = import.meta.env.VITE_API_URL || '/api'

const client = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

export const uploadFile = async (file, language = null, onUploadProgress) => {
  const formData = new FormData()
  formData.append('file', file)
  if (language) {
    formData.append('language', language)
  }
  
  const response = await client.post('/transcripts/upload', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
    // Прогресс загрузки файла (используется на UploadPage)
    onUploadProgress,
  })
  return response.data
}

export const getTranscripts = async (skip = 0, limit = 100, filters = {}) => {
  // Remove empty string filters to avoid sending them as query params
  const cleanFilters = Object.fromEntries(
    Object.entries(filters).filter(([_, value]) => value !== '' && value != null)
  )
  const params = { skip, limit, ...cleanFilters }
  const response = await client.get('/transcripts', { params })
  return response.data
}

export const getTranscript = async (id) => {
  const response = await client.get(`/transcripts/${id}`)
  return response.data
}

export const deleteTranscript = async (id) => {
  await client.delete(`/transcripts/${id}`)
}

export const getJobs = async (transcriptId) => {
  const response = await client.get(`/transcripts/${transcriptId}/jobs`)
  return response.data
}

export const getTranscriptJobs = async (transcriptId) => {
  // Alias for getJobs for consistency
  return getJobs(transcriptId)
}

// Summary API functions
export const createSummary = async (transcriptId, summaryData) => {
  const response = await client.post('/summaries', {
    transcript_id: transcriptId,
    ...summaryData
  })
  return response.data
}

export const getSummaries = async (transcriptId) => {
  const response = await client.get(`/transcripts/${transcriptId}/summaries`)
  return response.data
}

export const getSummary = async (summaryId) => {
  const response = await client.get(`/summaries/${summaryId}`)
  return response.data
}

// RAG API functions
export const getRAGSessions = async () => {
  const response = await client.get('/rag/sessions')
  return response.data
}

export const createRAGSession = async (sessionData) => {
  const response = await client.post('/rag/sessions', sessionData)
  return response.data
}

export const deleteRAGSession = async (sessionId) => {
  await client.delete(`/rag/sessions/${sessionId}`)
}

export const getTranscriptIndexStatus = async (transcriptId) => {
  const response = await client.get(`/transcripts/${transcriptId}/index-status`)
  return response.data
}

export const reindexTranscript = async (transcriptId) => {
  const response = await client.post(`/transcripts/${transcriptId}/reindex`)
  return response.data
}

export const translateTranscript = async (transcriptId, targetLanguage = 'ru', model = null) => {
  const body = {
    target_language: targetLanguage
  }
  if (model) {
    body.model = model
  }
  const response = await client.post(`/transcripts/${transcriptId}/translate`, body)
  return response.data
}

export default client

