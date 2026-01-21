import { useState, useEffect, useRef } from 'react'
import { useParams, Link, useNavigate } from 'react-router-dom'
import { ArrowLeft, Download, FileText, Clock, Globe, Edit, FileCheck, Plus, RefreshCw, CheckCircle, XCircle, Languages, ChevronDown, ChevronUp, Copy, Check } from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { getTranscript, getJobs, getSummaries, createSummary, getTranscriptIndexStatus, reindexTranscript, translateTranscript } from '../api/client'
import SummaryCreateModal from '../components/SummaryCreateModal'
import './TranscriptDetailPage.css'

function CopyButton({ text, label = "Копировать" }) {
  const [copied, setCopied] = useState(false)

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(text)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch (error) {
      console.error('Failed to copy:', error)
      alert('Failed to copy to clipboard')
    }
  }

  return (
    <button
      className="copy-button"
      onClick={handleCopy}
      title={copied ? "Copied!" : label}
    >
      {copied ? <Check size={16} /> : <Copy size={16} />}
      <span>{copied ? "Copied" : label}</span>
    </button>
  )
}

// Estimate translation time based on text length and model
function estimateTranslationTime(textLength, model) {
  // Base speeds in characters per second (conservative estimates)
  let minSpeed, maxSpeed
  
  switch (model) {
    case 'GigaChat/GigaChat-2-Max':
      // Slowest, highest quality
      minSpeed = 500
      maxSpeed = 800
      break
    case 'GigaChat/GigaChat-2':
      // Medium speed, good quality
      minSpeed = 1000
      maxSpeed = 1500
      break
    case 'Qwen/Qwen3-235B-A22B-Instruct-2507':
      // Fastest, recommended for large texts
      minSpeed = 2000
      maxSpeed = 3000
      break
    default:
      // Default to medium speed
      minSpeed = 1000
      maxSpeed = 1500
  }
  
  // Calculate time in seconds
  const minSeconds = Math.ceil(textLength / maxSpeed)
  const maxSeconds = Math.ceil(textLength / minSpeed)
  
  // Format as human-readable string
  const formatDuration = (seconds) => {
    if (seconds < 60) {
      return `${seconds} сек`
    } else if (seconds < 3600) {
      const mins = Math.floor(seconds / 60)
      const secs = seconds % 60
      if (secs === 0) {
        return `${mins} ${mins === 1 ? 'мин' : 'мин'}`
      }
      return `${mins} ${mins === 1 ? 'мин' : 'мин'} ${secs} сек`
    } else {
      const hours = Math.floor(seconds / 3600)
      const mins = Math.floor((seconds % 3600) / 60)
      if (mins === 0) {
        return `${hours} ${hours === 1 ? 'час' : 'часа'}`
      }
      return `${hours} ${hours === 1 ? 'час' : 'часа'} ${mins} ${mins === 1 ? 'мин' : 'мин'}`
    }
  }
  
  // If range is small, show single value
  if (maxSeconds - minSeconds <= 10) {
    const avgSeconds = Math.ceil((minSeconds + maxSeconds) / 2)
    return {
      minSeconds: avgSeconds,
      maxSeconds: avgSeconds,
      formatted: `~${formatDuration(avgSeconds)}`
    }
  }
  
  return {
    minSeconds,
    maxSeconds,
    formatted: `~${formatDuration(minSeconds)}–${formatDuration(maxSeconds)}`
  }
}

// Format duration in seconds to human-readable string
function formatDuration(seconds) {
  if (seconds < 60) {
    return `${Math.round(seconds)} сек`
  } else if (seconds < 3600) {
    const mins = Math.floor(seconds / 60)
    const secs = Math.round(seconds % 60)
    if (secs === 0) {
      return `${mins} ${mins === 1 ? 'мин' : 'мин'}`
    }
    return `${mins} ${mins === 1 ? 'мин' : 'мин'} ${secs} сек`
  } else {
    const hours = Math.floor(seconds / 3600)
    const mins = Math.floor((seconds % 3600) / 60)
    if (mins === 0) {
      return `${hours} ${hours === 1 ? 'час' : 'часа'}`
    }
    return `${hours} ${hours === 1 ? 'час' : 'часа'} ${mins} ${mins === 1 ? 'мин' : 'мин'}`
  }
}

// Calculate job duration from created_at and updated_at
function calculateJobDuration(job) {
  if (job.status !== 'completed' || !job.created_at || !job.updated_at) return null
  const start = new Date(job.created_at)
  const end = new Date(job.updated_at)
  const durationSeconds = Math.round((end - start) / 1000)
  return durationSeconds > 0 ? durationSeconds : null
}

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
  const [translationModel, setTranslationModel] = useState('GigaChat/GigaChat-2-Max') // Модель для перевода
  const [translationStartTime, setTranslationStartTime] = useState(null) // Timestamp when translation started
  const [currentTime, setCurrentTime] = useState(Date.now()) // Current time for updating elapsed time display
  const [visibleSummaries, setVisibleSummaries] = useState(new Set()) // ID видимых summaries
  const [expandedSummaries, setExpandedSummaries] = useState(new Set()) // ID развернутых summaries (preview/full)

  useEffect(() => {
    loadTranscript()
    loadJobs()
    if (transcript?.status === 'completed') {
      loadSummaries()
      loadIndexStatus()
    }
  }, [id])

  // Effect to update elapsed time every second during translation
  useEffect(() => {
    if (!translationStartTime || !translating) {
      setCurrentTime(Date.now())
      return
    }
    
    // Update current time every second to trigger re-render and update elapsed time display
    const interval = setInterval(() => {
      setCurrentTime(Date.now())
    }, 1000)
    
    return () => clearInterval(interval)
  }, [translationStartTime, translating])

  // Separate effect for polling during active operations
  useEffect(() => {
    // Опрос нужен для pending/processing статусов транскрипта, а также для активных jobs (translation, indexing)
    const interval = setInterval(async () => {
      if (transcript?.status === 'processing' || transcript?.status === 'pending') {
        loadTranscript()
        loadJobs()
      } else if (transcript?.status === 'completed') {
        // Always poll jobs to check for active translation or indexing jobs
        const jobsData = await loadJobs()
        
        // Check indexing job status - look for ANY indexing job, not just active ones
        const indexingJobData = jobsData?.find(j => j.job_type === 'indexing')
        if (indexingJobData) {
          console.log('[Polling] Indexing job status:', indexingJobData.status, 'progress:', indexingJobData.progress)
          if (indexingJobData.status === 'completed') {
            // Indexing completed - reload index status to show "Проиндексирован"
            console.log('[Polling] Indexing completed! Reloading index status...')
            await loadIndexStatus()
          } else if (indexingJobData.status === 'failed') {
            // Indexing failed - show error and reload status
            console.log('[Polling] Indexing failed!')
            await loadIndexStatus()
            if (indexingJobData.error_message) {
              alert(`Ошибка при индексации: ${indexingJobData.error_message}`)
            }
          } else if (indexingJobData.status === 'processing' || indexingJobData.status === 'queued') {
            // Indexing in progress - reload status to update progress display
            loadIndexStatus()
          }
        }
        
        // Check translation job status - look for ANY translation job, not just active ones
        const translationJob = jobsData?.find(j => j.job_type === 'translation')
        if (translationJob) {
          console.log('[Polling] Translation job status:', translationJob.status, 'progress:', translationJob.progress)
          if (translationJob.status === 'completed') {
            // Translation completed - reload transcript and stop translating state
            console.log('[Polling] Translation completed! Reloading transcript...')
            setTranslating(false)
            setTranslationStartTime(null) // Reset start time
            
            // Reload transcript immediately and again after a delay to ensure data is fresh
            await loadTranscript()
            console.log('[Polling] First reload done, scheduling second reload...')
            setTimeout(async () => {
              await loadTranscript()
              console.log('[Polling] Second reload done - checking extra_metadata:', transcript?.extra_metadata)
            }, 500)
          } else if (translationJob.status === 'failed') {
            // Translation failed - show error and stop translating state
            setTranslating(false)
            setTranslationStartTime(null) // Reset start time
            if (translationJob.error_message) {
              alert(`Ошибка при переводе: ${translationJob.error_message}`)
            }
          } else if (translationJob.status === 'processing' || translationJob.status === 'queued') {
            // Translation in progress - keep translating state true and keep polling
            // This ensures the progress bar stays visible
          }
          // If status is 'processing' or 'queued', keep polling
        } else if (translating) {
          // No translation job found but we're in translating state - wait a bit more
          // Maybe job hasn't been created yet (can take a moment)
          // Don't reset translating state immediately - give it time
        }
      }
    }, 1000) // Poll every 1 second for better responsiveness
    return () => clearInterval(interval)
  }, [id, transcript?.status, translating])

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
      return data
    } catch (error) {
      console.error('Error loading jobs:', error)
      return []
    }
  }

  const loadSummaries = async () => {
    if (!id) return
    setLoadingSummaries(true)
    try {
      const data = await getSummaries(id)
      setSummaries(data)
      // По умолчанию все summaries видимы
      if (data && data.length > 0) {
        setVisibleSummaries(new Set(data.map(s => s.id)))
      }
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
      setIndexStatus({ indexed: false, reason: 'Ошибка при проверке статуса' })
    }
  }

  const handleReindex = async () => {
    if (!id || reindexing) return
    setReindexing(true)
    try {
      // Start reindexing (this will create a job on backend)
      const result = await reindexTranscript(id)
      
      // Immediately load jobs to see the indexing job
      await loadJobs()
      
      // Don't show alert immediately - let user see progress bar
      // Indexing is happening in background, we'll poll for progress
      // The result will be checked when job completes
    } catch (error) {
      console.error('Error reindexing transcript:', error)
      alert(`Ошибка при переиндексации транскрипта: ${error.response?.data?.detail || error.message}`)
    } finally {
      setReindexing(false)
    }
  }

  const handleTranslate = async (targetLanguage = 'ru') => {
    if (!id || translating) return
    setTranslating(true)
    // Record start time for ETA calculation
    setTranslationStartTime(Date.now())
    try {
      // Start translation (this will create a job on backend and return immediately)
      const result = await translateTranscript(id, targetLanguage, translationModel)
      
      if (result.already_translated) {
        alert(result.message)
        setTranslating(false)
        setTranslationStartTime(null)
        return
      }
      
      // Immediately load jobs to see the translation job - do this multiple times to ensure we get it
      await loadJobs()
      // Wait a bit and load again to catch the job
      setTimeout(async () => {
        await loadJobs()
      }, 500)
      
      // Don't show alert - let user see progress bar
      // Translation is happening in background, we'll poll for progress
      // Keep translating state true until job completes (handled in useEffect)
    } catch (error) {
      console.error('Error translating transcript:', error)
      alert(`Ошибка при переводе транскрипта: ${error.response?.data?.detail || error.message}`)
      setTranslating(false)
      setTranslationStartTime(null)
    }
  }

  const getDisplayText = () => {
    if (!transcript) return ''
    
    if (viewLanguage === 'original' && transcript.extra_metadata?.original_english_text) {
      return transcript.extra_metadata.original_english_text
    }
    
    return transcript.transcription_text || ''
  }

  const getDisplayJSON = () => {
    if (!transcript?.transcription_json) {
      console.log('[getDisplayJSON] No transcription_json available')
      return null
    }
    
    const isTranslated = transcript.extra_metadata?.translated === true
    const translatedJSON = transcript.extra_metadata?.translated_transcription_json
    
    // Debug logging to help verify which JSON is used
    console.log('[getDisplayJSON] Debug info:', {
      isTranslated,
      hasTranslatedJSON: Boolean(translatedJSON),
      translatedJSONType: translatedJSON ? typeof translatedJSON : 'none',
      translatedJSONKeys: translatedJSON ? Object.keys(translatedJSON).slice(0, 5) : 'none',
      viewLanguage,
      transcriptLanguage: transcript.language,
      extraMetadataKeys: transcript.extra_metadata ? Object.keys(transcript.extra_metadata) : 'none',
    })
    
    if (isTranslated && translatedJSON) {
      // Явно запрошен оригинал — показываем английский JSON
      if (viewLanguage === 'original') {
        return transcript.transcription_json
      }
      
      // Явно запрошен русский — показываем переведенный JSON
      if (viewLanguage === 'ru') {
        return translatedJSON
      }
      
      // Текущий язык:
      // - если язык транскрипта сейчас ru, считаем, что основной вид — русский JSON
      // - иначе оставляем оригинальный JSON
      if (viewLanguage === 'current') {
        if (transcript.language?.toLowerCase() === 'ru') {
          return translatedJSON
        }
        return transcript.transcription_json
      }
    }
    
    // По умолчанию — оригинальный JSON (английский или тот, который пришел с backend)
    return transcript.transcription_json
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

  const getJobTypeLabel = (jobType) => {
    const labels = {
      'transcription': 'Транскрибация',
      'translation': 'Перевод на русский',
      'indexing': 'Индексация RAG',
      'summarization': 'Создание протокола встречи'
    }
    return labels[jobType] || jobType
  }

  // Get active translation job - find ACTIVE translation job only (processing or queued)
  const activeTranslationJob = jobs.find(j => j.job_type === 'translation' && (j.status === 'processing' || j.status === 'queued'))
  // Also find any translation job for showing errors
  const anyTranslationJob = jobs.find(j => j.job_type === 'translation')
  
  // Get active indexing job
  const indexingJob = jobs.find(j => j.job_type === 'indexing' && (j.status === 'processing' || j.status === 'queued'))

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
    const jsonToDownload = getDisplayJSON()
    if (!jsonToDownload) return
    const blob = new Blob([JSON.stringify(jsonToDownload, null, 2)], { type: 'application/json' })
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
    return <div className="loading">Загрузка транскрипта...</div>
  }

  if (!transcript) {
    return (
      <div className="error-state">
        <p>Транскрипт не найден</p>
        <Link to="/transcripts">Вернуться к транскриптам</Link>
      </div>
    )
  }

  return (
    <div className="transcript-detail-page">
      <div className="detail-header">
        <button className="btn-back" onClick={() => navigate('/transcripts')}>
          <ArrowLeft size={20} />
          Назад
        </button>
        <h1>{transcript.original_filename}</h1>
      </div>

      <div className="detail-info">
        <div className="info-card">
          <Clock size={20} />
          <div>
            <label>Создан</label>
            <span>{formatDate(transcript.created_at)}</span>
          </div>
        </div>
        {transcript.language && (
          <div className="info-card">
            <Globe size={20} />
            <div>
              <label>Язык</label>
              <span>{transcript.language.toUpperCase()}</span>
            </div>
          </div>
        )}
        <div className="info-card">
          <FileText size={20} />
          <div>
            <label>Размер файла</label>
            <span>{formatFileSize(transcript.file_size)}</span>
          </div>
        </div>
        <div className="info-card">
          <div>
            <label>Статус</label>
            <span className={`status-${transcript.status}`}>{transcript.status}</span>
          </div>
        </div>
      </div>

      {transcript.status === 'completed' && (
        <div className="rag-index-section">
          <div className="rag-index-header">
            <h3>Индексация RAG</h3>
            {indexStatus && (
              <div className={`index-status ${indexStatus.indexed ? 'indexed' : 'not-indexed'}`}>
                {indexStatus.indexed ? (
                  <>
                    <CheckCircle size={16} />
                    <span>Проиндексирован</span>
                  </>
                ) : (
                  <>
                    <XCircle size={16} />
                    <span>Не проиндексирован</span>
                  </>
                )}
              </div>
            )}
          </div>
          {indexingJob && (indexingJob.status === 'processing' || indexingJob.status === 'queued') && (
            <div className="indexing-progress">
              <div className="progress-container">
                <div className="progress-bar">
                  <div
                    className="progress-fill"
                    style={{ width: `${(indexingJob.progress || 0) * 100}%` }}
                  />
                </div>
                <span className="progress-text">
                  Индексация в процессе... {Math.round((indexingJob.progress || 0) * 100)}%
                </span>
              </div>
            </div>
          )}
          {!indexingJob && (
            <div className="rag-index-actions">
              {indexStatus && !indexStatus.indexed && (
                <p className="index-reason">{indexStatus.reason || 'Транскрипт не проиндексирован в системе RAG'}</p>
              )}
              <button
                className="btn-reindex"
                onClick={handleReindex}
                disabled={reindexing}
              >
                <RefreshCw size={16} className={reindexing ? 'spinning' : ''} />
                {reindexing ? 'Индексация...' : (indexStatus && indexStatus.indexed ? 'Переиндексировать снова' : 'Индексировать для RAG')}
              </button>
            </div>
          )}
        </div>
      )}

      {transcript.status === 'completed' && transcript.transcription_text && (
        <div className="translation-section">
          <div className="translation-header">
            <h3><Languages size={20} />Перевод</h3>
            {isTranslated && (
              <span className="translation-badge">
                <CheckCircle size={14} />
                Переведено
                {transcript.extra_metadata?.translation_duration_seconds && (
                  <span className="translation-time">
                    за {formatDuration(transcript.extra_metadata.translation_duration_seconds)}
                  </span>
                )}
              </span>
            )}
          </div>
          
          <div className="language-switcher">
            <label>Язык просмотра:</label>
            <div className="language-buttons">
              <button
                className={viewLanguage === 'current' ? 'active' : ''}
                onClick={() => setViewLanguage('current')}
              >
                Текущий ({transcript.language?.toUpperCase() || 'АВТО'})
              </button>
              {hasOriginalEnglish && (
                <button
                  className={viewLanguage === 'original' ? 'active' : ''}
                  onClick={() => setViewLanguage('original')}
                >
                  Оригинал (EN)
                </button>
              )}
              {isTranslated && (
                <button
                  className={viewLanguage === 'ru' ? 'active' : ''}
                  onClick={() => setViewLanguage('ru')}
                >
                  Русский (RU)
                </button>
              )}
            </div>
          </div>

          {(activeTranslationJob || translating) && (() => {
            const progress = activeTranslationJob?.progress ?? 0
            const hasDeterminateProgress = progress > 0 && progress < 1
            
            // Calculate elapsed time and ETA
            let elapsedSeconds = 0
            let remainingSeconds = null
            let initialEstimate = null
            
            if (translationStartTime) {
              elapsedSeconds = (currentTime - translationStartTime) / 1000
              if (hasDeterminateProgress && progress >= 0.05) {
                // Calculate ETA based on actual progress
                const estimatedTotalSeconds = elapsedSeconds / progress
                remainingSeconds = Math.max(0, estimatedTotalSeconds - elapsedSeconds)
              } else if (transcript?.transcription_text) {
                // Use initial estimate based on model when we don't have meaningful progress
                const textLength = transcript.transcription_text.length
                const estimate = estimateTranslationTime(textLength, translationModel)
                initialEstimate = estimate
                // Subtract elapsed time from initial estimate
                remainingSeconds = Math.max(0, estimate.maxSeconds - elapsedSeconds)
              }
            }
            
            return (
              <div className="translation-progress">
                <div className="progress-container">
                  {hasDeterminateProgress ? (
                    <>
                      <div className="progress-bar">
                        <div
                          className="progress-fill"
                          style={{ width: `${Math.round(progress * 100)}%` }}
                        />
                      </div>
                      <div className="progress-info">
                        <span className="progress-text">
                          Перевод в процессе... {Math.round(progress * 100)}%
                        </span>
                        {translationStartTime && (
                          <div className="progress-time-info">
                            <span>Прошло: {formatDuration(elapsedSeconds)}</span>
                            {remainingSeconds !== null && (
                              <span>Осталось: ~{formatDuration(remainingSeconds)}</span>
                            )}
                          </div>
                        )}
                      </div>
                    </>
                  ) : (
                    <>
                      <div className="progress-bar indeterminate">
                        <div className="progress-fill" />
                      </div>
                      <div className="progress-info">
                        <span className="progress-text">
                          Перевод в процессе...
                        </span>
                        {translationStartTime && (
                          <div className="progress-time-info">
                            <span>Прошло: {formatDuration(elapsedSeconds)}</span>
                            {initialEstimate && remainingSeconds !== null && remainingSeconds > 0 && (
                              <span>Осталось: ~{formatDuration(remainingSeconds)} (прогноз)</span>
                            )}
                          </div>
                        )}
                      </div>
                    </>
                  )}
                </div>
              </div>
            )
          })()}
          {anyTranslationJob && anyTranslationJob.status === 'failed' && (
            <div className="translation-error">
              <p className="error-message">
                Ошибка при переводе: {anyTranslationJob.error_message || 'Неизвестная ошибка'}
              </p>
            </div>
          )}
          {!isTranslated && transcript.language?.toLowerCase() !== 'ru' && !activeTranslationJob && !translating && (() => {
            // Calculate estimated translation time
            const textLength = transcript.transcription_text?.length || 0
            const timeEstimate = estimateTranslationTime(textLength, translationModel)
            
            return (
              <div className="translation-actions">
                <p className="translation-hint">
                  {transcript.language?.toLowerCase() === 'en' 
                    ? "Этот транскрипт на английском языке. Хотите перевести его на русский?"
                    : "Хотите перевести этот транскрипт на русский?"}
                </p>
                <div className="translation-model-selector">
                  <label htmlFor="translation-model">Модель для перевода:</label>
                  <select
                    id="translation-model"
                    value={translationModel}
                    onChange={(e) => setTranslationModel(e.target.value)}
                    className="model-select"
                  >
                    <option value="GigaChat/GigaChat-2-Max">GigaChat-2-Max — Медленный, высокое качество</option>
                    <option value="GigaChat/GigaChat-2">GigaChat-2 — Быстрее, хорошее качество</option>
                    <option value="Qwen/Qwen3-235B-A22B-Instruct-2507">Qwen3 — Быстрый, рекомендуется для больших текстов</option>
                  </select>
                </div>
                {textLength > 0 && (
                  <div className="translation-time-estimate">
                    <Clock size={14} />
                    <span>Примерное время перевода для выбранной модели: <strong>{timeEstimate.formatted}</strong></span>
                  </div>
                )}
                <button
                  className="btn-translate"
                  onClick={() => handleTranslate('ru')}
                  disabled={translating}
                >
                  <Languages size={16} />
                  {translating ? 'Перевод...' : 'Перевести на русский'}
                </button>
              </div>
            )
          })()}
        </div>
      )}

      {jobs.length > 0 && (
        <div className="jobs-section">
          <h2>Задачи обработки</h2>
          {jobs.map(job => {
            const duration = calculateJobDuration(job)
            return (
              <div key={job.id} className="job-item">
                <div className="job-info">
                  <span className="job-type">{getJobTypeLabel(job.job_type)}</span>
                  <span className={`job-status job-status-${job.status}`}>{job.status}</span>
                  {job.status === 'completed' && duration !== null && (
                    <span className="job-duration">
                      {formatDuration(duration)}
                    </span>
                  )}
                  {job.progress > 0 && job.status !== 'completed' && (
                    <div className="progress-container">
                      <div className="progress-bar">
                        <div
                          className="progress-fill"
                          style={{ width: `${job.progress * 100}%` }}
                        />
                      </div>
                      <span className="progress-text">
                        {Math.round(job.progress * 100)}%
                      </span>
                    </div>
                  )}
                </div>
                {job.error_message && (
                  <div className="job-error">{job.error_message}</div>
                )}
              </div>
            )
          })}
        </div>
      )}

      {/* Summaries Section */}
      {transcript.status === 'completed' && (
        <div className="summaries-section">
          <div className="summaries-header">
            <h2>
              <FileCheck size={20} />
              Протоколы встреч
            </h2>
            <button
              className="btn-create-summary"
              onClick={() => setShowSummaryModal(true)}
            >
              <Plus size={16} />
              Создать протокол
            </button>
          </div>
          {loadingSummaries ? (
            <div className="loading">Загрузка протоколов встреч...</div>
          ) : summaries.length > 0 ? (
            <div className="summaries-list">
              {summaries.map((summary) => {
                const isVisible = visibleSummaries.has(summary.id)
                const isExpanded = expandedSummaries.has(summary.id)
                const previewLength = 200
                const shouldShowToggle = summary.summary_text && summary.summary_text.length > previewLength
                const displayText = isExpanded || !shouldShowToggle 
                  ? summary.summary_text 
                  : summary.summary_text.substring(0, previewLength) + '...'
                
                // Если summary скрыт, показываем только кнопку для показа
                if (!isVisible) {
                  return (
                    <div key={summary.id} className="summary-item summary-hidden">
                      <div className="summary-header">
                        <span className="summary-model">{summary.model_used}</span>
                        <span className="summary-date">
                          {formatDate(summary.created_at)}
                        </span>
                      </div>
                      <button
                        className="summary-toggle"
                        onClick={() => {
                          setVisibleSummaries(prev => {
                            const newSet = new Set(prev)
                            newSet.add(summary.id)
                            return newSet
                          })
                        }}
                      >
                        <ChevronDown size={16} />
                        <span>Показать протокол</span>
                      </button>
                    </div>
                  )
                }
                
                // Если summary видим, показываем полный контент
                return (
                  <div key={summary.id} className="summary-item">
                    <div className="summary-header">
                      <span className="summary-model">{summary.model_used}</span>
                      <span className="summary-date">
                        {formatDate(summary.created_at)}
                      </span>
                      <div className="summary-actions">
                        <CopyButton text={summary.summary_text} label="Копировать протокол" />
                        <button
                          className="summary-toggle summary-hide-btn"
                          onClick={() => {
                            setVisibleSummaries(prev => {
                              const newSet = new Set(prev)
                              newSet.delete(summary.id)
                              return newSet
                            })
                          }}
                          title="Скрыть протокол"
                        >
                          <ChevronUp size={16} />
                          <span>Hide</span>
                        </button>
                      </div>
                    </div>
                    {summary.summary_template && (
                      <span className="summary-template">
                        Шаблон: {summary.summary_template}
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
                            <span>Показать меньше</span>
                          </>
                        ) : (
                          <>
                            <ChevronDown size={16} />
                            <span>Показать больше</span>
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
              <p>Протоколы встреч пока отсутствуют. Создайте первый, чтобы начать.</p>
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
              Текст
            </button>
            {summaries.length > 0 && (
              <button
                className={activeTab === 'summary' ? 'active' : ''}
                onClick={() => setActiveTab('summary')}
              >
                Протокол
              </button>
            )}
            {(transcript.transcription_json || transcript.extra_metadata?.translated_transcription_json) && (
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
              Редактировать
            </Link>
            {transcript.transcription_text && (
              <button className="btn-download" onClick={downloadText}>
                <Download size={16} />
                Скачать текст
              </button>
            )}
            {(transcript.transcription_json || transcript.extra_metadata?.translated_transcription_json) && (
              <button className="btn-download" onClick={downloadJSON}>
                <Download size={16} />
                Скачать JSON
              </button>
            )}
            {transcript.transcription_srt && (
              <button className="btn-download" onClick={downloadSRT}>
                <Download size={16} />
                Скачать SRT
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
                  const isVisible = visibleSummaries.has(summary.id)
                  const isExpanded = expandedSummaries.has(summary.id)
                  const previewLength = 200
                  const shouldShowToggle = summary.summary_text && summary.summary_text.length > previewLength
                  const displayText = isExpanded || !shouldShowToggle 
                    ? summary.summary_text 
                    : summary.summary_text.substring(0, previewLength) + '...'
                  
                  // Если summary скрыт, показываем только кнопку для показа
                  if (!isVisible) {
                    return (
                      <div key={summary.id} className="summary-display-item summary-hidden">
                        <div className="summary-meta">
                          <span className="summary-model">{summary.model_used}</span>
                          <span className="summary-date">
                            {formatDate(summary.created_at)}
                          </span>
                        </div>
                        <button
                          className="summary-toggle"
                          onClick={() => {
                            setVisibleSummaries(prev => {
                              const newSet = new Set(prev)
                              newSet.add(summary.id)
                              return newSet
                            })
                          }}
                        >
                          <ChevronDown size={16} />
                          <span>Показать протокол</span>
                        </button>
                      </div>
                    )
                  }
                  
                  // Если summary видим, показываем полный контент
                  return (
                    <div key={summary.id} className="summary-display-item">
                      <div className="summary-meta">
                        <span className="summary-model">{summary.model_used}</span>
                        {summary.summary_template && (
                          <span className="summary-template">
                            Шаблон: {summary.summary_template}
                          </span>
                        )}
                        <span className="summary-date">
                          {formatDate(summary.created_at)}
                        </span>
                        <div className="summary-actions">
                          <CopyButton text={summary.summary_text} label="Копировать протокол" />
                          <button
                            className="summary-toggle summary-hide-btn"
                            onClick={() => {
                              setVisibleSummaries(prev => {
                                const newSet = new Set(prev)
                                newSet.delete(summary.id)
                                return newSet
                              })
                            }}
                            title="Скрыть протокол"
                          >
                            <ChevronUp size={16} />
                            <span>Hide</span>
                          </button>
                        </div>
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
                                <span>Показать меньше</span>
                              </>
                            ) : (
                              <>
                                <ChevronDown size={16} />
                                <span>Показать больше</span>
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
            {activeTab === 'json' && (() => {
              const displayJSON = getDisplayJSON()
              return displayJSON ? (
                <pre className="json-content">
                  {JSON.stringify(displayJSON, null, 2)}
                </pre>
              ) : null
            })()}
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
          <p>Транскрибация не удалась. Пожалуйста, попробуйте загрузить снова.</p>
        </div>
      )}
    </div>
  )
}

export default TranscriptDetailPage

