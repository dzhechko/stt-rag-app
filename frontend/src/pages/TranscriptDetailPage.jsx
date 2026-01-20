import { useState, useEffect } from 'react'
import { useParams, Link, useNavigate } from 'react-router-dom'
import { ArrowLeft, Download, FileText, Clock, Globe, Edit, FileCheck, Plus, RefreshCw, CheckCircle, XCircle, Languages, ChevronDown, ChevronUp } from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { getTranscript, getJobs, getSummaries, createSummary, getTranscriptIndexStatus, reindexTranscript, translateTranscript } from '../api/client'
import SummaryCreateModal from '../components/SummaryCreateModal'
import './TranscriptDetailPage.css'

function TranscriptDetailPage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [transcript, setTranscript] = useState(null)
  const [jobs, setJobs] = useState([])
  const [summaries, setSummaries] = useState([])
  const [loading, setLoading] = useState(true)
  const [activeTab, setActiveTab] = useState('text')
  const [showSummaryModal, setShowSummaryModal] = useState(false)
  const [loadingSummaries, setLoadingSummaries] = useState(false)
  const [indexStatus, setIndexStatus] = useState(null)
  const [reindexing, setReindexing] = useState(false)
  const [viewLanguage, setViewLanguage] = useState('current') // 'current', 'original', 'ru'
  const [translating, setTranslating] = useState(false)
  const [expandedSummaries, setExpandedSummaries] = useState(new Set())

  useEffect(() => {
    loadTranscript()
    loadJobs()
    if (transcript?.status === 'completed') {
      loadSummaries()
      loadIndexStatus()
    }
    const interval = setInterval(() => {
      if (transcript?.status === 'processing' || transcript?.status === 'pending') {
        loadTranscript()
        loadJobs()
      } else if (transcript?.status === 'completed') {
        loadSummaries()
        loadIndexStatus()
      }
    }, 2000)
    return () => clearInterval(interval)
  }, [id, transcript?.status])

  const loadTranscript = async () => {
    try {
      const data = await getTranscript(id)
      setTranscript(data)
    } catch (error) {
      console.error('Error loading transcript:', error)
    } finally {
      setLoading(false)
    }
  }

  const loadJobs = async () => {
    try {
      const data = await getJobs(id)
      setJobs(data)
    } catch (error) {
      console.error('Error loading jobs:', error)
    }
  }

  const loadSummaries = async () => {
    if (!id) return
    setLoadingSummaries(true)
    try {
      const data = await getSummaries(id)
      setSummaries(data)
    } catch (error) {
      console.error('Error loading summaries:', error)
    } finally {
      setLoadingSummaries(false)
    }
  }

  const handleCreateSummary = async (summaryData) => {
    try {
      await createSummary(id, summaryData)
      await loadSummaries()
      await loadJobs() // Refresh jobs to show summarization job
    } catch (error) {
      console.error('Error creating summary:', error)
      throw error
    }
  }

  const loadIndexStatus = async () => {
    if (!id || transcript?.status !== 'completed') return
    try {
      const status = await getTranscriptIndexStatus(id)
      setIndexStatus(status)
    } catch (error) {
      console.error('Error loading index status:', error)
      setIndexStatus({ indexed: false, reason: 'Error checking status' })
    }
  }

  const handleReindex = async () => {
    if (!id || reindexing) return
    setReindexing(true)
    try {
      const result = await reindexTranscript(id)
      if (result.chunks_indexed === 0) {
        if (result.error === 'embeddings_not_available') {
          alert(`RAG indexing is not available: ${result.reason || result.message}\n\nEvolution Cloud.ru does not support embeddings API endpoint. RAG features are disabled.`)
        } else {
          alert(`Reindexed but got 0 chunks. ${result.message || 'RAG indexing may not be available.'}`)
        }
      } else {
        alert(`Successfully reindexed transcript. ${result.chunks_indexed} chunks indexed.`)
      }
      await loadIndexStatus()
    } catch (error) {
      console.error('Error reindexing transcript:', error)
      alert(`Error reindexing transcript: ${error.response?.data?.detail || error.message}`)
    } finally {
      setReindexing(false)
    }
  }

  const handleTranslate = async (targetLanguage = 'ru') => {
    if (!id || translating) return
    setTranslating(true)
    try {
      const result = await translateTranscript(id, targetLanguage)
      if (result.already_translated) {
        alert(result.message)
      } else {
        alert(result.message)
        await loadTranscript() // Reload to get updated text
      }
    } catch (error) {
      console.error('Error translating transcript:', error)
      alert(`Error translating transcript: ${error.response?.data?.detail || error.message}`)
    } finally {
      setTranslating(false)
    }
  }

  const getDisplayText = () => {
    if (!transcript) return ''
    
    if (viewLanguage === 'original' && transcript.extra_metadata?.original_english_text) {
      return transcript.extra_metadata.original_english_text
    }
    
    return transcript.transcription_text || ''
  }

  const isTranslated = transcript?.extra_metadata?.translated === true
  const hasOriginalEnglish = transcript?.extra_metadata?.original_english_text

  const formatDate = (dateString) => {
    return new Date(dateString).toLocaleString()
  }

  const formatFileSize = (bytes) => {
    if (bytes < 1024) return bytes + ' B'
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(2) + ' KB'
    return (bytes / 1024 / 1024).toFixed(2) + ' MB'
  }

  const downloadText = () => {
    if (!transcript?.transcription_text) return
    const blob = new Blob([transcript.transcription_text], { type: 'text/plain' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${transcript.original_filename}.txt`
    a.click()
    URL.revokeObjectURL(url)
  }

  const downloadJSON = () => {
    if (!transcript?.transcription_json) return
    const blob = new Blob([JSON.stringify(transcript.transcription_json, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${transcript.original_filename}.json`
    a.click()
    URL.revokeObjectURL(url)
  }

  const downloadSRT = () => {
    if (!transcript?.transcription_srt) return
    const blob = new Blob([transcript.transcription_srt], { type: 'text/srt' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${transcript.original_filename}.srt`
    a.click()
    URL.revokeObjectURL(url)
  }

  if (loading) {
    return <div className="loading">Loading transcript...</div>
  }

  if (!transcript) {
    return (
      <div className="error-state">
        <p>Transcript not found</p>
        <Link to="/transcripts">Back to Transcripts</Link>
      </div>
    )
  }

  return (
    <div className="transcript-detail-page">
      <div className="detail-header">
        <button className="btn-back" onClick={() => navigate('/transcripts')}>
          <ArrowLeft size={20} />
          Back
        </button>
        <h1>{transcript.original_filename}</h1>
      </div>

      <div className="detail-info">
        <div className="info-card">
          <Clock size={20} />
          <div>
            <label>Created</label>
            <span>{formatDate(transcript.created_at)}</span>
          </div>
        </div>
        {transcript.language && (
          <div className="info-card">
            <Globe size={20} />
            <div>
              <label>Language</label>
              <span>{transcript.language.toUpperCase()}</span>
            </div>
          </div>
        )}
        <div className="info-card">
          <FileText size={20} />
          <div>
            <label>File Size</label>
            <span>{formatFileSize(transcript.file_size)}</span>
          </div>
        </div>
        <div className="info-card">
          <div>
            <label>Status</label>
            <span className={`status-${transcript.status}`}>{transcript.status}</span>
          </div>
        </div>
      </div>

      {transcript.status === 'completed' && (
        <div className="rag-index-section">
          <div className="rag-index-header">
            <h3>RAG Indexing</h3>
            {indexStatus && (
              <div className={`index-status ${indexStatus.indexed ? 'indexed' : 'not-indexed'}`}>
                {indexStatus.indexed ? (
                  <>
                    <CheckCircle size={16} />
                    <span>Indexed</span>
                  </>
                ) : (
                  <>
                    <XCircle size={16} />
                    <span>Not Indexed</span>
                  </>
                )}
              </div>
            )}
          </div>
          {indexStatus && !indexStatus.indexed && (
            <div className="rag-index-actions">
              <p className="index-reason">{indexStatus.reason || 'Transcript is not indexed in RAG system'}</p>
              <button
                className="btn-reindex"
                onClick={handleReindex}
                disabled={reindexing}
              >
                <RefreshCw size={16} className={reindexing ? 'spinning' : ''} />
                {reindexing ? 'Reindexing...' : 'Reindex for RAG'}
              </button>
            </div>
          )}
          {indexStatus && indexStatus.indexed && (
            <div className="rag-index-actions">
              <button
                className="btn-reindex"
                onClick={handleReindex}
                disabled={reindexing}
              >
                <RefreshCw size={16} className={reindexing ? 'spinning' : ''} />
                {reindexing ? 'Reindexing...' : 'Reindex Again'}
              </button>
            </div>
          )}
        </div>
      )}

      {transcript.status === 'completed' && transcript.transcription_text && (
        <div className="translation-section">
          <div className="translation-header">
            <h3><Languages size={20} />Translation</h3>
            {isTranslated && (
              <span className="translation-badge">
                <CheckCircle size={14} />
                Translated
              </span>
            )}
          </div>
          
          <div className="language-switcher">
            <label>View language:</label>
            <div className="language-buttons">
              <button
                className={viewLanguage === 'current' ? 'active' : ''}
                onClick={() => setViewLanguage('current')}
              >
                Current ({transcript.language?.toUpperCase() || 'AUTO'})
              </button>
              {hasOriginalEnglish && (
                <button
                  className={viewLanguage === 'original' ? 'active' : ''}
                  onClick={() => setViewLanguage('original')}
                >
                  Original (EN)
                </button>
              )}
              {isTranslated && (
                <button
                  className={viewLanguage === 'ru' ? 'active' : ''}
                  onClick={() => setViewLanguage('ru')}
                >
                  Russian (RU)
                </button>
              )}
            </div>
          </div>

          {!isTranslated && transcript.language?.toLowerCase() !== 'ru' && (
            <div className="translation-actions">
              <p className="translation-hint">
                {transcript.language?.toLowerCase() === 'en' 
                  ? "This transcript is in English. Would you like to translate it to Russian?"
                  : "Would you like to translate this transcript to Russian?"}
              </p>
              <button
                className="btn-translate"
                onClick={() => handleTranslate('ru')}
                disabled={translating}
              >
                <Languages size={16} />
                {translating ? 'Translating...' : 'Translate to Russian'}
              </button>
            </div>
          )}
        </div>
      )}

      {jobs.length > 0 && (
        <div className="jobs-section">
          <h2>Processing Jobs</h2>
          {jobs.map(job => (
            <div key={job.id} className="job-item">
              <div className="job-info">
                <span className="job-type">{job.job_type}</span>
                <span className={`job-status job-status-${job.status}`}>{job.status}</span>
                {job.progress > 0 && (
                  <div className="progress-bar">
                    <div
                      className="progress-fill"
                      style={{ width: `${job.progress * 100}%` }}
                    />
                  </div>
                )}
              </div>
              {job.error_message && (
                <div className="job-error">{job.error_message}</div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Summaries Section */}
      {transcript.status === 'completed' && (
        <div className="summaries-section">
          <div className="summaries-header">
            <h2>
              <FileCheck size={20} />
              Summaries
            </h2>
            <button
              className="btn-create-summary"
              onClick={() => setShowSummaryModal(true)}
            >
              <Plus size={16} />
              Create Summary
            </button>
          </div>
          {loadingSummaries ? (
            <div className="loading">Loading summaries...</div>
          ) : summaries.length > 0 ? (
            <div className="summaries-list">
              {summaries.map((summary) => {
                const isExpanded = expandedSummaries.has(summary.id)
                const previewLength = 200
                const shouldShowToggle = summary.summary_text && summary.summary_text.length > previewLength
                const displayText = isExpanded || !shouldShowToggle 
                  ? summary.summary_text 
                  : summary.summary_text.substring(0, previewLength) + '...'
                
                return (
                  <div key={summary.id} className="summary-item">
                    <div className="summary-header">
                      <span className="summary-model">{summary.model_used}</span>
                      <span className="summary-date">
                        {formatDate(summary.created_at)}
                      </span>
                    </div>
                    {summary.summary_template && (
                      <span className="summary-template">
                        Template: {summary.summary_template}
                      </span>
                    )}
                    {shouldShowToggle && (
                      <button
                        className="summary-toggle"
                        onClick={() => {
                          setExpandedSummaries(prev => {
                            const newSet = new Set(prev)
                            if (newSet.has(summary.id)) {
                              newSet.delete(summary.id)
                            } else {
                              newSet.add(summary.id)
                            }
                            return newSet
                          })
                        }}
                      >
                        {isExpanded ? (
                          <>
                            <ChevronUp size={16} />
                            <span>Show less</span>
                          </>
                        ) : (
                          <>
                            <ChevronDown size={16} />
                            <span>Show more</span>
                          </>
                        )}
                      </button>
                    )}
                    <div className="summary-text">
                      <ReactMarkdown remarkPlugins={[remarkGfm]}>
                        {displayText}
                      </ReactMarkdown>
                    </div>
                  </div>
                )
              })}
            </div>
          ) : (
            <div className="empty-summaries">
              <p>No summaries yet. Create one to get started.</p>
            </div>
          )}
        </div>
      )}

      {transcript.status === 'completed' && transcript.transcription_text && (
        <div className="transcript-content">
          <div className="content-tabs">
            <button
              className={activeTab === 'text' ? 'active' : ''}
              onClick={() => setActiveTab('text')}
            >
              Text
            </button>
            {summaries.length > 0 && (
              <button
                className={activeTab === 'summary' ? 'active' : ''}
                onClick={() => setActiveTab('summary')}
              >
                Summary
              </button>
            )}
            {transcript.transcription_json && (
              <button
                className={activeTab === 'json' ? 'active' : ''}
                onClick={() => setActiveTab('json')}
              >
                JSON
              </button>
            )}
            {transcript.transcription_srt && (
              <button
                className={activeTab === 'srt' ? 'active' : ''}
                onClick={() => setActiveTab('srt')}
              >
                SRT
              </button>
            )}
          </div>

          <div className="content-actions">
            <Link
              to={`/transcripts/${transcript.id}/edit`}
              className="btn-download"
            >
              <Edit size={16} />
              Edit
            </Link>
            {transcript.transcription_text && (
              <button className="btn-download" onClick={downloadText}>
                <Download size={16} />
                Download Text
              </button>
            )}
            {transcript.transcription_json && (
              <button className="btn-download" onClick={downloadJSON}>
                <Download size={16} />
                Download JSON
              </button>
            )}
            {transcript.transcription_srt && (
              <button className="btn-download" onClick={downloadSRT}>
                <Download size={16} />
                Download SRT
              </button>
            )}
          </div>

          <div className="content-display">
            {activeTab === 'text' && (
              <pre className="text-content">{getDisplayText()}</pre>
            )}
            {activeTab === 'summary' && summaries.length > 0 && (
              <div className="summary-content">
                {summaries.map((summary) => {
                  const isExpanded = expandedSummaries.has(summary.id)
                  const previewLength = 200
                  const shouldShowToggle = summary.summary_text && summary.summary_text.length > previewLength
                  const displayText = isExpanded || !shouldShowToggle 
                    ? summary.summary_text 
                    : summary.summary_text.substring(0, previewLength) + '...'
                  
                  return (
                    <div key={summary.id} className="summary-display-item">
                      <div className="summary-meta">
                        <span className="summary-model">{summary.model_used}</span>
                        {summary.summary_template && (
                          <span className="summary-template">
                            Template: {summary.summary_template}
                          </span>
                        )}
                        <span className="summary-date">
                          {formatDate(summary.created_at)}
                        </span>
                        {shouldShowToggle && (
                          <button
                            className="summary-toggle"
                            onClick={() => {
                              setExpandedSummaries(prev => {
                                const newSet = new Set(prev)
                                if (newSet.has(summary.id)) {
                                  newSet.delete(summary.id)
                                } else {
                                  newSet.add(summary.id)
                                }
                                return newSet
                              })
                            }}
                          >
                            {isExpanded ? (
                              <>
                                <ChevronUp size={16} />
                                <span>Show less</span>
                              </>
                            ) : (
                              <>
                                <ChevronDown size={16} />
                                <span>Show more</span>
                              </>
                            )}
                          </button>
                        )}
                      </div>
                      <div className="summary-text-display">
                        <ReactMarkdown remarkPlugins={[remarkGfm]}>
                          {displayText}
                        </ReactMarkdown>
                      </div>
                    </div>
                  )
                })}
              </div>
            )}
            {activeTab === 'json' && transcript.transcription_json && (
              <pre className="json-content">
                {JSON.stringify(transcript.transcription_json, null, 2)}
              </pre>
            )}
            {activeTab === 'srt' && transcript.transcription_srt && (
              <pre className="srt-content">{transcript.transcription_srt}</pre>
            )}
          </div>
        </div>
      )}

      <SummaryCreateModal
        isOpen={showSummaryModal}
        onClose={() => setShowSummaryModal(false)}
        onSubmit={handleCreateSummary}
        transcriptId={id}
      />

      {transcript.status === 'failed' && (
        <div className="error-state">
          <p>Transcription failed. Please try uploading again.</p>
        </div>
      )}
    </div>
  )
}

export default TranscriptDetailPage

