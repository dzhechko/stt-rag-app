import { useState, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { Upload, File, X, CheckCircle, AlertCircle } from 'lucide-react'
import { uploadFile } from '../api/client'
import './UploadPage.css'

function UploadPage() {
  const [files, setFiles] = useState([])
  const [language, setLanguage] = useState('')
  const [uploading, setUploading] = useState(false)
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

  const uploadFiles = async () => {
    if (files.length === 0) return
    
    setUploading(true)
    
    for (const fileItem of files) {
      if (fileItem.status === 'pending') {
        try {
          fileItem.status = 'uploading'
          setFiles([...files])
          
          const result = await uploadFile(fileItem.file, language || null)
          fileItem.status = 'completed'
          fileItem.transcriptId = result.id
          setFiles([...files])
          
          // Navigate to transcripts page after first successful upload
          if (files.indexOf(fileItem) === 0) {
            setTimeout(() => {
              navigate('/transcripts')
            }, 1000)
          }
        } catch (error) {
          fileItem.status = 'error'
          fileItem.error = error.response?.data?.detail || error.message
          setFiles([...files])
        }
      }
    }
    
    setUploading(false)
  }

  return (
    <div className="upload-page">
      <h1>Upload Audio Files</h1>
      
      <div className="upload-section">
        <div
          className="drop-zone"
          onDrop={handleDrop}
          onDragOver={(e) => e.preventDefault()}
          onDragEnter={(e) => e.preventDefault()}
        >
          <Upload size={48} />
          <p>Drag and drop audio files here, or click to select</p>
          <input
            type="file"
            multiple
            accept="audio/*,video/*"
            onChange={handleFileSelect}
            className="file-input"
          />
        </div>

        <div className="language-selector">
          <label htmlFor="language">Language:</label>
          <select
            id="language"
            value={language}
            onChange={(e) => setLanguage(e.target.value)}
          >
            <option value="">Auto-detect (may be less accurate)</option>
            <option value="ru">Russian (Русский) - Recommended for Russian meetings</option>
            <option value="en">English</option>
            <option value="de">German</option>
            <option value="fr">French</option>
            <option value="es">Spanish</option>
          </select>
          <small className="language-hint">
            Для русских встреч рекомендуется выбрать "Russian" для более точной транскрипции
          </small>
        </div>

        {files.length > 0 && (
          <div className="files-list">
            <h3>Selected Files ({files.length})</h3>
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
                {fileItem.status === 'uploading' && (
                  <span className="status uploading">Uploading...</span>
                )}
                {fileItem.status === 'completed' && (
                  <span className="status completed">
                    <CheckCircle size={16} /> Completed
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
            {uploading ? 'Uploading...' : `Upload ${files.length} File(s)`}
          </button>
        )}
      </div>
    </div>
  )
}

export default UploadPage

