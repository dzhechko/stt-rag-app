import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { FileText, Clock, Globe, Trash2, Eye, ChevronDown, ChevronUp } from 'lucide-react'
import { getTranscripts, deleteTranscript } from '../api/client'
import './TranscriptsPage.css'

function TranscriptsPage() {
  const [transcripts, setTranscripts] = useState([])
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState({ status: '', language: '' })
  const [expandedTranscripts, setExpandedTranscripts] = useState(new Set())
  const [transcriptViewMode, setTranscriptViewMode] = useState({}) // { transcriptId: 'text' | 'json' | 'srt' }

  useEffect(() => {
    loadTranscripts()
  }, [filter])

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
    if (!window.confirm('Are you sure you want to delete this transcript?')) {
      return
    }
    
    try {
      await deleteTranscript(id)
      loadTranscripts()
    } catch (error) {
      console.error('Error deleting transcript:', error)
      alert('Error deleting transcript')
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
          : 'No JSON data available'
      case 'srt':
        return transcript.transcription_srt || 'No SRT data available'
      default:
        return transcript.transcription_text || 'No text available'
    }
  }

  if (loading) {
    return <div className="loading">Loading transcripts...</div>
  }

  return (
    <div className="transcripts-page">
      <div className="page-header">
        <h1>Transcripts</h1>
        <div className="filters">
          <select
            value={filter.status}
            onChange={(e) => setFilter({ ...filter, status: e.target.value })}
          >
            <option value="">All Statuses</option>
            <option value="pending">Pending</option>
            <option value="processing">Processing</option>
            <option value="completed">Completed</option>
            <option value="failed">Failed</option>
          </select>
          <select
            value={filter.language}
            onChange={(e) => setFilter({ ...filter, language: e.target.value })}
          >
            <option value="">All Languages</option>
            <option value="ru">Russian</option>
            <option value="en">English</option>
            <option value="de">German</option>
            <option value="fr">French</option>
            <option value="es">Spanish</option>
          </select>
        </div>
      </div>

      {transcripts.length === 0 ? (
        <div className="empty-state">
          <FileText size={64} />
          <p>No transcripts found</p>
          <Link to="/" className="btn-primary">Upload Files</Link>
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
                  <span>Size: {formatFileSize(transcript.file_size)}</span>
                </div>
              </div>

              <div className="card-status">
                <span
                  className="status-badge"
                  style={{ backgroundColor: getStatusColor(transcript.status) }}
                >
                  {transcript.status}
                </span>
              </div>

              {transcript.transcription_text && (
                <div className={`card-preview ${!expandedTranscripts.has(transcript.id) ? 'transcript-hidden' : ''}`}>
                  {!expandedTranscripts.has(transcript.id) ? (
                    <button
                      className="transcript-toggle"
                      onClick={() => toggleTranscript(transcript.id)}
                    >
                      <ChevronDown size={16} />
                      <span>Show transcript</span>
                    </button>
                  ) : (
                    <>
                      <div className="transcript-header">
                        <button
                          className="transcript-toggle transcript-hide-btn"
                          onClick={() => toggleTranscript(transcript.id)}
                        >
                          <ChevronUp size={16} />
                          <span>Hide transcript</span>
                        </button>
                      </div>
                      <div className="transcript-expanded">
                        <div className="transcript-view-tabs">
                          <button
                            className={transcriptViewMode[transcript.id] === 'text' || !transcriptViewMode[transcript.id] ? 'active' : ''}
                            onClick={() => setTranscriptViewMode({ ...transcriptViewMode, [transcript.id]: 'text' })}
                          >
                            Text
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
                  View
                </Link>
                <button
                  className="btn-action btn-danger"
                  onClick={() => handleDelete(transcript.id)}
                >
                  <Trash2 size={16} />
                  Delete
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

