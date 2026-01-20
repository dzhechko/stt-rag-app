import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { FileText, Clock, Globe, Trash2, Eye, ChevronDown, ChevronUp } from 'lucide-react'
import { getTranscripts, deleteTranscript, getTranscriptJobs } from '../api/client'
import './TranscriptsPage.css'

function TranscriptsPage() {
  const [transcripts, setTranscripts] = useState([])
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState({ status: '', language: '' })
  const [expandedTranscripts, setExpandedTranscripts] = useState(new Set())
  const [transcriptViewMode, setTranscriptViewMode] = useState({}) // { transcriptId: 'text' | 'json' | 'srt' }
  const [transcriptProgress, setTranscriptProgress] = useState({}) // { transcriptId: progress }

  useEffect(() => {
    loadTranscripts()
  }, [filter])

  // Poll progress for transcripts in processing/pending status
  useEffect(() => {
    const processingTranscripts = transcripts.filter(
      t => t.status === 'processing' || t.status === 'pending'
    )

    if (processingTranscripts.length === 0) return

    const pollProgress = async () => {
      for (const transcript of processingTranscripts) {
        try {
          const jobs = await getTranscriptJobs(transcript.id)
          const transcriptionJob = jobs.find(j => j.job_type === 'transcription')
          if (transcriptionJob && transcriptionJob.progress !== undefined) {
            setTranscriptProgress(prev => ({
              ...prev,
              [transcript.id]: transcriptionJob.progress
            }))
          }
        } catch (error) {
          console.error(`Error polling progress for transcript ${transcript.id}:`, error)
        }
      }
    }

    // Poll immediately (for fast transcriptions)
    pollProgress()

    // Then poll every 2 seconds
    const interval = setInterval(pollProgress, 2000)

    return () => clearInterval(interval)
  }, [transcripts])

  const loadTranscripts = async () => {
    setLoading(true)
    try {
      const data = await getTranscripts(0, 100, filter)
      console.log('Loaded transcripts data:', data)
      console.log('Transcripts count:', data?.transcripts?.length || 0)
      setTranscripts(data.transcripts || [])
    } catch (error) {
      console.error('Error loading transcripts:', error)
      setTranscripts([])
    } finally {
      setLoading(false)
    }
  }

  const handleDelete = async (id) => {
    if (!window.confirm('Вы уверены, что хотите удалить этот транскрипт?')) {
      return
    }
    
    try {
      await deleteTranscript(id)
      loadTranscripts()
    } catch (error) {
      console.error('Error deleting transcript:', error)
      alert('Ошибка при удалении транскрипта')
    }
  }

  const getStatusColor = (status) => {
    switch (status) {
      case 'completed': return '#27ae60'
      case 'processing': return '#3498db'
      case 'pending': return '#f39c12'
      case 'failed': return '#e74c3c'
      default: return '#95a5a6'
    }
  }

  const formatDate = (dateString) => {
    return new Date(dateString).toLocaleString()
  }

  const formatFileSize = (bytes) => {
    if (bytes < 1024) return bytes + ' B'
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(2) + ' KB'
    return (bytes / 1024 / 1024).toFixed(2) + ' MB'
  }

  const toggleTranscript = (id) => {
    setExpandedTranscripts(prev => {
      const newSet = new Set(prev)
      if (newSet.has(id)) {
        newSet.delete(id)
      } else {
        newSet.add(id)
      }
      return newSet
    })
  }

  const getTranscriptContent = (transcript) => {
    const viewMode = transcriptViewMode[transcript.id] || 'text'
    switch (viewMode) {
      case 'json':
        return transcript.transcription_json 
          ? JSON.stringify(transcript.transcription_json, null, 2)
          : 'Данные JSON недоступны'
      case 'srt':
        return transcript.transcription_srt || 'Данные SRT недоступны'
      default:
        return transcript.transcription_text || 'Текст недоступен'
    }
  }

  if (loading) {
    return <div className="loading">Загрузка транскриптов...</div>
  }

  return (
    <div className="transcripts-page">
      <div className="page-header">
        <h1>Транскрипты</h1>
        <div className="filters">
          <select
            value={filter.status}
            onChange={(e) => setFilter({ ...filter, status: e.target.value })}
          >
            <option value="">Все статусы</option>
            <option value="pending">Ожидание</option>
            <option value="processing">Обработка</option>
            <option value="completed">Завершено</option>
            <option value="failed">Ошибка</option>
          </select>
          <select
            value={filter.language}
            onChange={(e) => setFilter({ ...filter, language: e.target.value })}
          >
            <option value="">Все языки</option>
            <option value="ru">Русский</option>
            <option value="en">Английский</option>
            <option value="de">Немецкий</option>
            <option value="fr">Французский</option>
            <option value="es">Испанский</option>
          </select>
        </div>
      </div>

      {transcripts.length === 0 ? (
        <div className="empty-state">
          <FileText size={64} />
          <p>Транскрипты не найдены</p>
          <Link to="/upload" className="btn-primary">Загрузить файлы</Link>
        </div>
      ) : (
        <div className="transcripts-grid">
          {transcripts.map(transcript => (
            <div key={transcript.id} className="transcript-card">
              <div className="card-header">
                <FileText size={24} />
                <h3>{transcript.original_filename}</h3>
              </div>
              
              <div className="card-info">
                <div className="info-item">
                  <Clock size={16} />
                  <span>{formatDate(transcript.created_at)}</span>
                </div>
                {transcript.language && (
                  <div className="info-item">
                    <Globe size={16} />
                    <span>{transcript.language.toUpperCase()}</span>
                  </div>
                )}
                <div className="info-item">
                  <span>Размер: {formatFileSize(transcript.file_size)}</span>
                </div>
              </div>

              <div className="card-status">
                <span
                  className="status-badge"
                  style={{ backgroundColor: getStatusColor(transcript.status) }}
                >
                  {transcript.status}
                </span>
                {(transcript.status === 'processing' || transcript.status === 'pending') && 
                 transcriptProgress[transcript.id] !== undefined && (
                  <div className="progress-container">
                    <div className="progress-bar">
                      <div 
                        className="progress-fill"
                        style={{ width: `${(transcriptProgress[transcript.id] || 0) * 100}%` }}
                      />
                    </div>
                    <span className="progress-text">
                      {Math.round((transcriptProgress[transcript.id] || 0) * 100)}%
                    </span>
                  </div>
                )}
              </div>

              {transcript.transcription_text && (
                <div className={`card-preview ${!expandedTranscripts.has(transcript.id) ? 'transcript-hidden' : ''}`}>
                  {!expandedTranscripts.has(transcript.id) ? (
                    <button
                      className="transcript-toggle"
                      onClick={() => toggleTranscript(transcript.id)}
                    >
                      <ChevronDown size={16} />
                      <span>Показать транскрипт</span>
                    </button>
                  ) : (
                    <>
                      <div className="transcript-header">
                        <button
                          className="transcript-toggle transcript-hide-btn"
                          onClick={() => toggleTranscript(transcript.id)}
                        >
                          <ChevronUp size={16} />
                          <span>Скрыть транскрипт</span>
                        </button>
                      </div>
                      <div className="transcript-expanded">
                        <div className="transcript-view-tabs">
                          <button
                            className={transcriptViewMode[transcript.id] === 'text' || !transcriptViewMode[transcript.id] ? 'active' : ''}
                            onClick={() => setTranscriptViewMode({ ...transcriptViewMode, [transcript.id]: 'text' })}
                          >
                            Текст
                          </button>
                          {transcript.transcription_json && (
                            <button
                              className={transcriptViewMode[transcript.id] === 'json' ? 'active' : ''}
                              onClick={() => setTranscriptViewMode({ ...transcriptViewMode, [transcript.id]: 'json' })}
                            >
                              JSON
                            </button>
                          )}
                          {transcript.transcription_srt && (
                            <button
                              className={transcriptViewMode[transcript.id] === 'srt' ? 'active' : ''}
                              onClick={() => setTranscriptViewMode({ ...transcriptViewMode, [transcript.id]: 'srt' })}
                            >
                              SRT
                            </button>
                          )}
                        </div>
                        <div className="transcript-content">
                          <pre>{getTranscriptContent(transcript)}</pre>
                        </div>
                      </div>
                    </>
                  )}
                </div>
              )}

              <div className="card-actions">
                <Link
                  to={`/transcripts/${transcript.id}`}
                  className="btn-action"
                >
                  <Eye size={16} />
                  Просмотр
                </Link>
                <button
                  className="btn-action btn-danger"
                  onClick={() => handleDelete(transcript.id)}
                >
                  <Trash2 size={16} />
                  Удалить
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

export default TranscriptsPage

