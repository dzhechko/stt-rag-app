import { useState, useCallback, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { Upload, File, X, CheckCircle, AlertCircle } from 'lucide-react'
import { uploadFile, getTranscriptJobs } from '../api/client'
import './UploadPage.css'

function UploadPage() {
  const [files, setFiles] = useState([])
  const [language, setLanguage] = useState('')
  const [uploading, setUploading] = useState(false)
  const [fileProgress, setFileProgress] = useState({}) // { transcriptId: progress }
  const navigate = useNavigate()

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
      error: null
    }))])
  }

  const removeFile = (id) => {
    setFiles(prev => prev.filter(f => f.id !== id))
  }

  const pollTranscriptionProgress = async (transcriptId) => {
    try {
      const jobs = await getTranscriptJobs(transcriptId)
      const transcriptionJob = jobs.find(j => j.job_type === 'transcription')
      if (transcriptionJob) {
        // Always update progress if job exists
        if (transcriptionJob.progress !== undefined) {
          setFileProgress(prev => ({
            ...prev,
            [transcriptId]: transcriptionJob.progress
          }))
        }
        
        // Update file status based on job status
        if (transcriptionJob.status === 'processing' || transcriptionJob.status === 'queued') {
          // Keep status as 'processing' while transcription is in progress
          setFiles(prev => prev.map(f => 
            f.transcriptId === transcriptId 
              ? { ...f, status: 'processing' }
              : f
          ))
        } else if (transcriptionJob.status === 'completed') {
          // Transcription completed
          setFiles(prev => prev.map(f => 
            f.transcriptId === transcriptId 
              ? { ...f, status: 'transcribed' }
              : f
          ))
        } else if (transcriptionJob.status === 'failed') {
          // Transcription failed
          setFiles(prev => prev.map(f => 
            f.transcriptId === transcriptId 
              ? { ...f, status: 'error', error: transcriptionJob.error_message || 'Ошибка транскрибации' }
              : f
          ))
        }
        
        // Return true if we should stop polling (completed or failed)
        return transcriptionJob.status === 'completed' || transcriptionJob.status === 'failed'
      }
    } catch (error) {
      console.error('Error polling progress:', error)
    }
    return false
  }

  // Poll progress for files that are being transcribed
  useEffect(() => {
    const intervals = {}
    
    files.forEach(fileItem => {
      // Poll for files that have transcriptId and are in uploading/processing/completed status
      if (fileItem.transcriptId && (fileItem.status === 'uploading' || fileItem.status === 'processing' || fileItem.status === 'completed')) {
        // First poll immediately (for fast transcriptions)
        pollTranscriptionProgress(fileItem.transcriptId).then(shouldStop => {
          if (shouldStop) {
            // If already completed/failed, don't start interval
            return
          }
          
          // Then start polling for this file
          const interval = setInterval(async () => {
            const stop = await pollTranscriptionProgress(fileItem.transcriptId)
            if (stop) {
              clearInterval(interval)
              delete intervals[fileItem.transcriptId]
            }
          }, 1000) // Poll every 1 second for better responsiveness
          intervals[fileItem.transcriptId] = interval
        })
      }
    })

    return () => {
      Object.values(intervals).forEach(interval => clearInterval(interval))
    }
  }, [files])

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
          
          const result = await uploadFile(fileItem.file, language || null)
          
          // Update status to processing and set transcriptId
          setFiles(prev => prev.map((f, idx) => 
            idx === i ? { ...f, status: 'processing', transcriptId: result.id } : f
          ))
          
          // Initialize progress immediately
          setFileProgress(prev => ({ ...prev, [result.id]: 0.0 }))
          
          // Start polling immediately for this file (don't wait)
          setTimeout(() => {
            pollTranscriptionProgress(result.id)
          }, 100)
          
          // Navigate to transcripts page after first successful upload
          if (i === 0) {
            setTimeout(() => {
              navigate('/transcripts')
            }, 1000)
          }
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
            <option value="">Автоопределение (может быть менее точным)</option>
            <option value="ru">Русский - Рекомендуется для встреч на русском языке</option>
            <option value="en">English</option>
            <option value="de">German</option>
            <option value="fr">French</option>
            <option value="es">Spanish</option>
          </select>
          <small className="language-hint">
            Для русских встреч рекомендуется выбрать "Russian" для более точной транскрибации
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
                {fileItem.transcriptId && (fileItem.status === 'uploading' || fileItem.status === 'processing' || (fileItem.status === 'completed' && fileProgress[fileItem.transcriptId] !== undefined && fileProgress[fileItem.transcriptId] < 1.0)) && (
                  <div className="transcription-status">
                    <div className="progress-container">
                      <div className="progress-bar">
                        <div 
                          className="progress-fill"
                          style={{ width: `${(fileProgress[fileItem.transcriptId] || 0) * 100}%` }}
                        />
                      </div>
                      <span className="progress-text">
                        Транскрибация... {Math.round((fileProgress[fileItem.transcriptId] || 0) * 100)}%
                      </span>
                    </div>
                  </div>
                )}
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

