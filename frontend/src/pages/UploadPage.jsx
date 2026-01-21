import { useState, useCallback, useEffect, useRef, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import { Upload, File, X, CheckCircle, AlertCircle } from 'lucide-react'
import { uploadFile, getTranscriptJobs } from '../api/client'
import './UploadPage.css'

function UploadPage() {
  const [files, setFiles] = useState([])
  const [language, setLanguage] = useState('ru')
  const [uploading, setUploading] = useState(false)
  const [fileProgress, setFileProgress] = useState({}) // { transcriptId: progress }
  const [jobStatuses, setJobStatuses] = useState({}) // { transcriptId: 'queued' | 'processing' | 'completed' | 'failed' }
  const navigate = useNavigate()
  const intervalsRef = useRef({})
  const pollingAttemptsRef = useRef({}) // { transcriptId: count } - track polling attempts for missing jobs

  const handleDrop = useCallback((e) => {
    e.preventDefault()
    const droppedFiles = Array.from(e.dataTransfer.files)
    handleFiles(droppedFiles)
  }, [])

  const handleFileSelect = (e) => {
    const selectedFiles = Array.from(e.target.files)
    handleFiles(selectedFiles)
  }

  const handleFiles = (newFiles) => {
    const audioFiles = newFiles.filter(file => {
      const ext = file.name.toLowerCase().split('.').pop()
      return ['mp3', 'mp4', 'mpeg', 'mpga', 'm4a', 'wav', 'webm'].includes(ext)
    })
    
    setFiles(prev => [...prev, ...audioFiles.map(file => ({
      file,
      id: Date.now() + Math.random(),
      status: 'pending',
      transcriptId: null,
      error: null,
      uploadProgress: 0,
    }))])
  }

  const removeFile = (id) => {
    setFiles(prev => prev.filter(f => f.id !== id))
  }

  // Calculate progress for a file item - ensures recalculation when fileProgress changes
  const calculateFileProgress = useCallback((fileItem) => {
    const uploadProgress = fileItem.uploadProgress ?? 0
    const transcriptionProgress = fileItem.transcriptId 
      ? (fileProgress[fileItem.transcriptId] ?? 0)
      : 0
    // If transcriptId exists, upload is complete, so use: 0.4 + 0.6 * transcriptionProgress
    const combined = fileItem.transcriptId
      ? 0.4 + 0.6 * transcriptionProgress
      : uploadProgress
    
    return { uploadProgress, transcriptionProgress, combined }
  }, [fileProgress])

  const pollTranscriptionProgress = async (transcriptId) => {
    console.log(`[Polling] Poll for: ${transcriptId}`)
    try {
      const jobs = await getTranscriptJobs(transcriptId)
      const transcriptionJob = jobs.find(j => j.job_type === 'transcription')
      
      if (transcriptionJob) {
        // Reset polling attempts counter when job is found
        pollingAttemptsRef.current[transcriptId] = 0
        
        const progress = transcriptionJob.progress ?? 0
        const status = transcriptionJob.status
        
        // ВАЖНО: Всегда обновляем прогресс и статус для отображения динамики
        console.log(`[Progress] ${transcriptId.slice(0,8)}: ${Math.round(progress * 100)}% (${status})`)
        
        // Update job status
        setJobStatuses(prev => ({ ...prev, [transcriptId]: status }))
        
        setFileProgress(prev => {
          // Только обновляем если прогресс изменился
          if (prev[transcriptId] !== progress) {
            console.log(`[Progress Update] ${Math.round((prev[transcriptId] || 0) * 100)}% -> ${Math.round(progress * 100)}%`)
            return { ...prev, [transcriptId]: progress }
          }
          return prev
        })
        
        // Update file status based on job status
        if (status === 'processing' || status === 'queued') {
          // Keep status as 'processing' while transcription is in progress
          setFiles(prev => prev.map(f => 
            f.transcriptId === transcriptId 
              ? { ...f, status: 'processing' }
              : f
          ))
        } else if (status === 'completed') {
          // Transcription completed
          console.log(`[Polling] Transcription completed for ${transcriptId}`)
          setFiles(prev => {
            const updated = prev.map(f => 
              f.transcriptId === transcriptId 
                ? { ...f, status: 'transcribed' }
                : f
            )
            // Check if all files are processed (transcribed, error, or pending)
            const allProcessed = updated.every(f => 
              f.status === 'transcribed' || f.status === 'error' || f.status === 'pending'
            )
            const hasTranscribed = updated.some(f => f.status === 'transcribed')
            
            // Redirect to transcripts page after all files are processed
            if (allProcessed && hasTranscribed) {
              console.log(`[Polling] All files processed, redirecting to /transcripts in 2 seconds`)
              setTimeout(() => {
                navigate('/transcripts')
              }, 2000)
            }
            
            return updated
          })
        } else if (status === 'failed') {
          // Transcription failed
          console.log(`[Polling] Transcription failed for ${transcriptId}:`, transcriptionJob.error_message)
          setFiles(prev => prev.map(f => 
            f.transcriptId === transcriptId 
              ? { ...f, status: 'error', error: transcriptionJob.error_message || 'Ошибка транскрибации' }
              : f
          ))
        }
        
        // Return true if we should stop polling (completed or failed)
        const shouldStop = status === 'completed' || status === 'failed'
        if (shouldStop) console.log(`[Polling] Stopping for ${transcriptId.slice(0,8)} - ${status}`)
        return shouldStop
      } else {
        console.log(`[Polling] No transcriptionJob found for ${transcriptId}, jobs:`, jobs)
        // Increment polling attempts counter
        pollingAttemptsRef.current[transcriptId] = (pollingAttemptsRef.current[transcriptId] || 0) + 1
        const attempts = pollingAttemptsRef.current[transcriptId]
        console.log(`[Polling] Polling attempts for ${transcriptId}: ${attempts}`)
        
        // Continue polling if job not found yet (it might be created soon)
        // Stop after 60 attempts (60 seconds) if job never appears
        if (attempts > 60) {
          console.warn(`[Polling] Stopping polling for ${transcriptId} after 60 attempts - job never appeared`)
          return true // Stop polling
        }
      }
    } catch (error) {
      console.error(`[Polling] Error polling progress for ${transcriptId}:`, error)
    }
    return false
  }

  // Start polling for a specific transcriptId
  const startPollingForTranscript = useCallback((transcriptId) => {
    // Не создавать дублирующие интервалы
    if (intervalsRef.current[transcriptId]) {
      console.log(`[Polling] Already polling: ${transcriptId.slice(0,8)}`)
      return
    }
    
    console.log(`[Polling] Starting for: ${transcriptId.slice(0,8)}`)
    intervalsRef.current[transcriptId] = true // Mark as starting
    
    // First poll immediately
    pollTranscriptionProgress(transcriptId).then(shouldStop => {
      if (shouldStop) {
        console.log(`[Polling] Job done on first poll: ${transcriptId.slice(0,8)}`)
        delete intervalsRef.current[transcriptId]
        return
      }
      
      // Start polling interval
      const interval = setInterval(async () => {
        const stop = await pollTranscriptionProgress(transcriptId)
        if (stop) {
          console.log(`[Polling] Stopping interval: ${transcriptId.slice(0,8)}`)
          clearInterval(interval)
          delete intervalsRef.current[transcriptId]
        }
      }, 1000)
      
      intervalsRef.current[transcriptId] = interval
    })
  }, [])

  // Watch for files that need polling - DON'T clear intervals on files change!
  useEffect(() => {
    files.forEach(fileItem => {
      if (fileItem.transcriptId && 
          (fileItem.status === 'uploading' || fileItem.status === 'processing')) {
        startPollingForTranscript(fileItem.transcriptId)
      }
    })
    // NO cleanup here - intervals manage themselves
  }, [files, startPollingForTranscript])

  // Cleanup ONLY on unmount
  useEffect(() => {
    return () => {
      console.log('[Polling] Unmount - clearing all intervals')
      Object.entries(intervalsRef.current).forEach(([id, interval]) => {
        if (typeof interval !== 'boolean') clearInterval(interval)
      })
      intervalsRef.current = {}
    }
  }, [])

  const uploadFiles = async () => {
    if (files.length === 0) return
    
    setUploading(true)
    
    for (let i = 0; i < files.length; i++) {
      const fileItem = files[i]
      if (fileItem.status === 'pending') {
        try {
          // Update status to uploading
          setFiles(prev => prev.map((f, idx) => 
            idx === i ? { ...f, status: 'uploading' } : f
          ))
          
          const result = await uploadFile(
            fileItem.file,
            language || null,
            (progressEvent) => {
              const total = progressEvent.total || progressEvent.loaded
              const progress = total ? progressEvent.loaded / total : 0
              setFiles(prev =>
                prev.map((f, idx) =>
                  idx === i ? { ...f, uploadProgress: progress } : f
                )
              )
            }
          )
          
          // Ensure uploadProgress is 1.0 after upload completes, then update status to processing
          setFiles(prev => prev.map((f, idx) => 
            idx === i ? { ...f, uploadProgress: 1.0, status: 'processing', transcriptId: result.id } : f
          ))
          
          // Initialize transcription progress immediately
          setFileProgress(prev => ({ ...prev, [result.id]: 0.0 }))
          
          // useEffect will handle polling automatically when files state updates
          // No need to start polling here - useEffect will catch the state change
          // Redirect will happen when transcription completes (in pollTranscriptionProgress)
        } catch (error) {
          setFiles(prev => prev.map((f, idx) => 
            idx === i ? { ...f, status: 'error', error: error.response?.data?.detail || error.message } : f
          ))
        }
      }
    }
    
    setUploading(false)
  }

  return (
    <div className="upload-page">
      <h1>Загрузка аудио файлов</h1>
      
      <div className="upload-section">
        <div
          className="drop-zone"
          onDrop={handleDrop}
          onDragOver={(e) => e.preventDefault()}
          onDragEnter={(e) => e.preventDefault()}
        >
          <Upload size={48} />
          <p>Перетащите аудио файлы сюда или нажмите для выбора</p>
          <input
            type="file"
            multiple
            accept="audio/*,video/*"
            onChange={handleFileSelect}
            className="file-input"
          />
        </div>
        
        <div className="supported-formats">
          <p className="formats-label">Поддерживаемые форматы:</p>
          <div className="formats-list">
            <span className="format-tag">MP3</span>
            <span className="format-tag">MP4</span>
            <span className="format-tag">MPEG</span>
            <span className="format-tag">MPGA</span>
            <span className="format-tag">M4A</span>
            <span className="format-tag">WAV</span>
            <span className="format-tag">WEBM</span>
          </div>
        </div>

        <div className="language-selector">
          <label htmlFor="language">Язык:</label>
          <select
            id="language"
            value={language}
            onChange={(e) => setLanguage(e.target.value)}
          >
            <option value="ru">Русский (рекомендуется)</option>
            <option value="en">English</option>
            <option value="">Автоопределение (может переводить на английский!)</option>
            <option value="de">German</option>
            <option value="fr">French</option>
            <option value="es">Spanish</option>
          </select>
          <small className="language-hint">
            Важно: при "Автоопределении" Whisper может переводить на английский вместо транскрибирования
          </small>
        </div>

        {files.length > 0 && (
          <div className="files-list">
            <h3>Выбранные файлы ({files.length})</h3>
            {files.map(fileItem => (
              <div key={fileItem.id} className="file-item">
                <File size={20} />
                <span className="file-name">{fileItem.file.name}</span>
                <span className="file-size">
                  {(fileItem.file.size / 1024 / 1024).toFixed(2)} MB
                </span>
                {fileItem.status === 'pending' && (
                  <button
                    className="btn-remove"
                    onClick={() => removeFile(fileItem.id)}
                  >
                    <X size={16} />
                  </button>
                )}
                {fileItem.status === 'uploading' && !fileItem.transcriptId && (
                  <span className="status uploading">Загрузка...</span>
                )}
                {(fileItem.status === 'uploading' || fileItem.status === 'processing') && (() => {
                  const progressData = calculateFileProgress(fileItem)
                  // Определяем фазу по нескольким признакам для надёжности:
                  const isUploadComplete = fileItem.uploadProgress >= 1.0 || fileItem.status === 'processing'
                  const hasTranscriptId = fileItem.transcriptId !== null
                  const isTranscribing = isUploadComplete || hasTranscriptId
                  const currentPhase = isTranscribing ? 'transcription' : 'upload'
                  
                  // Получаем статус задачи с backend
                  const jobStatus = hasTranscriptId ? jobStatuses[fileItem.transcriptId] : null
                  const isQueued = jobStatus === 'queued'
                  
                  // Рассчитываем прогресс транскрибации
                  const transcriptionProgress = hasTranscriptId && fileProgress[fileItem.transcriptId] !== undefined
                    ? fileProgress[fileItem.transcriptId]
                    : 0
                  const transcriptionPercent = Math.round(transcriptionProgress * 100)
                  
                  // Общий прогресс: 40% загрузка + 60% транскрибация
                  const combinedProgress = isTranscribing
                    ? 0.4 + 0.6 * transcriptionProgress
                    : progressData.uploadProgress * 0.4
                  
                  return (
                    <div className="file-progress-phases" key={`${fileItem.id}-${currentPhase}-${jobStatus}`}>
                      {/* Индикатор текущей фазы */}
                      <div className="phase-indicator">
                        <span className={`phase ${currentPhase === 'upload' ? 'active' : 'completed'}`}>
                          1. Загрузка {isUploadComplete && '✓'}
                        </span>
                        <span className="phase-arrow">→</span>
                        <span className={`phase ${currentPhase === 'transcription' ? 'active' : ''}`}>
                          2. Транскрибация {isTranscribing && (isQueued ? '(ожидание)' : `${transcriptionPercent}%`)}
                        </span>
                      </div>
                      
                      {/* Прогресс-бар */}
                      <div className="progress-container">
                        <div className={`progress-bar ${isQueued ? 'indeterminate' : ''}`}>
                          <div
                            className={`progress-fill ${isQueued ? 'indeterminate' : ''}`}
                            style={{ width: isQueued ? '100%' : `${Math.round(combinedProgress * 100)}%` }}
                          />
                        </div>
                        <span className="progress-text">
                          {isTranscribing
                            ? (isQueued 
                                ? 'Ожидание начала...' 
                                : `Транскрибация: ${transcriptionPercent}% (общий: ${Math.round(combinedProgress * 100)}%)`)
                            : `Загрузка: ${Math.round(progressData.uploadProgress * 100)}%`}
                        </span>
                      </div>
                    </div>
                  )
                })()}
                {fileItem.status === 'completed' && fileItem.transcriptId && fileProgress[fileItem.transcriptId] !== undefined && fileProgress[fileItem.transcriptId] >= 1.0 && (
                  <span className="status completed">
                    <CheckCircle size={16} /> Завершено
                  </span>
                )}
                {fileItem.status === 'transcribed' && (
                  <span className="status completed">
                    <CheckCircle size={16} /> Транскрибировано
                  </span>
                )}
                {fileItem.status === 'error' && (
                  <span className="status error">
                    <AlertCircle size={16} /> {fileItem.error}
                  </span>
                )}
              </div>
            ))}
          </div>
        )}

        {files.length > 0 && (
          <button
            className="btn-upload"
            onClick={uploadFiles}
            disabled={uploading}
          >
            {uploading ? 'Загрузка...' : `Загрузить ${files.length} ${files.length === 1 ? 'файл' : files.length < 5 ? 'файла' : 'файлов'}`}
          </button>
        )}
      </div>
    </div>
  )
}

export default UploadPage

