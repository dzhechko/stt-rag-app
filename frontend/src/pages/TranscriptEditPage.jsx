import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { Save, ArrowLeft, X } from 'lucide-react'
import { getTranscript } from '../api/client'
import client from '../api/client'
import './TranscriptEditPage.css'

function TranscriptEditPage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [transcript, setTranscript] = useState(null)
  const [editedText, setEditedText] = useState('')
  const [tags, setTags] = useState([])
  const [tagInput, setTagInput] = useState('')
  const [category, setCategory] = useState('')
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    loadTranscript()
  }, [id])

  const loadTranscript = async () => {
    try {
      const data = await getTranscript(id)
      setTranscript(data)
      setEditedText(data.transcription_text || '')
      setTags(data.tags || [])
      setCategory(data.category || '')
    } catch (error) {
      console.error('Error loading transcript:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleAddTag = () => {
    if (tagInput.trim() && !tags.includes(tagInput.trim())) {
      setTags([...tags, tagInput.trim()])
      setTagInput('')
    }
  }

  const handleRemoveTag = (tagToRemove) => {
    setTags(tags.filter(tag => tag !== tagToRemove))
  }

  const handleSave = async () => {
    setSaving(true)
    try {
      await client.put(`/transcripts/${id}`, {
        transcription_text: editedText,
        tags: tags,
        category: category || null
      })
      navigate(`/transcripts/${id}`)
    } catch (error) {
      console.error('Error saving transcript:', error)
      alert('Error saving transcript')
    } finally {
      setSaving(false)
    }
  }

  if (loading) {
    return <div className="loading">Loading transcript...</div>
  }

  if (!transcript) {
    return (
      <div className="error-state">
        <p>Transcript not found</p>
      </div>
    )
  }

  return (
    <div className="edit-page">
      <div className="edit-header">
        <button className="btn-back" onClick={() => navigate(`/transcripts/${id}`)}>
          <ArrowLeft size={20} />
          Cancel
        </button>
        <h1>Edit Transcript</h1>
        <button
          className="btn-save"
          onClick={handleSave}
          disabled={saving}
        >
          <Save size={20} />
          {saving ? 'Saving...' : 'Save'}
        </button>
      </div>

      <div className="edit-content">
        <div className="edit-section">
          <label>Transcription Text</label>
          <textarea
            className="text-editor"
            value={editedText}
            onChange={(e) => setEditedText(e.target.value)}
            placeholder="Enter transcription text..."
          />
        </div>

        <div className="edit-section">
          <label>Tags</label>
          <div className="tags-input">
            <input
              type="text"
              value={tagInput}
              onChange={(e) => setTagInput(e.target.value)}
              onKeyPress={(e) => {
                if (e.key === 'Enter') {
                  e.preventDefault()
                  handleAddTag()
                }
              }}
              placeholder="Add a tag and press Enter"
            />
            <button onClick={handleAddTag}>Add</button>
          </div>
          <div className="tags-list">
            {tags.map(tag => (
              <span key={tag} className="tag">
                {tag}
                <button onClick={() => handleRemoveTag(tag)}>
                  <X size={14} />
                </button>
              </span>
            ))}
          </div>
        </div>

        <div className="edit-section">
          <label>Category</label>
          <input
            type="text"
            value={category}
            onChange={(e) => setCategory(e.target.value)}
            placeholder="Enter category"
          />
        </div>
      </div>
    </div>
  )
}

export default TranscriptEditPage

