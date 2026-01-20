import { useState } from 'react'
import { X } from 'lucide-react'
import './SummaryCreateModal.css'

function SummaryCreateModal({ isOpen, onClose, onSubmit, transcriptId }) {
  const [template, setTemplate] = useState('meeting')
  const [model, setModel] = useState('GigaChat/GigaChat-2-Max')
  const [customPrompt, setCustomPrompt] = useState('')
  const [fieldsConfig, setFieldsConfig] = useState({
    participants: true,
    decisions: true,
    deadlines: false,
    topics: true
  })
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError(null)
    setLoading(true)

    try {
      const summaryData = {
        template: template || null,
        model: model || null,
        custom_prompt: customPrompt || null,
        fields_config: fieldsConfig
      }

      await onSubmit(summaryData)
      onClose()
      // Reset form
      setTemplate('meeting')
      setModel('GigaChat/GigaChat-2-Max')
      setCustomPrompt('')
      setFieldsConfig({
        participants: true,
        decisions: true,
        deadlines: false,
        topics: true
      })
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Failed to create summary')
    } finally {
      setLoading(false)
    }
  }

  const toggleField = (field) => {
    setFieldsConfig(prev => ({
      ...prev,
      [field]: !prev[field]
    }))
  }

  if (!isOpen) return null

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>Create Summary</h2>
          <button className="modal-close" onClick={onClose}>
            <X size={20} />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="summary-form">
          <div className="form-group">
            <label htmlFor="template">Template</label>
            <select
              id="template"
              value={template}
              onChange={(e) => setTemplate(e.target.value)}
            >
              <option value="">None (use default)</option>
              <option value="meeting">Meeting</option>
              <option value="interview">Interview</option>
              <option value="lecture">Lecture</option>
              <option value="podcast">Podcast</option>
            </select>
          </div>

          <div className="form-group">
            <label htmlFor="model">Model</label>
            <select
              id="model"
              value={model}
              onChange={(e) => setModel(e.target.value)}
            >
              <option value="GigaChat/GigaChat-2-Max">GigaChat-2-Max (Recommended)</option>
              <option value="Qwen/Qwen3-235B-A22B-Instruct-2507">Qwen3-235B</option>
              <option value="Qwen/Qwen3-Next-80B-A3B-Instruct">Qwen3-Next-80B</option>
            </select>
          </div>

          <div className="form-group">
            <label htmlFor="customPrompt">Custom Prompt (optional)</label>
            <textarea
              id="customPrompt"
              value={customPrompt}
              onChange={(e) => setCustomPrompt(e.target.value)}
              placeholder="Enter custom prompt to override template..."
              rows={4}
            />
            <small>If provided, this will override the template</small>
          </div>

          <div className="form-group">
            <label>Fields to Include</label>
            <div className="fields-checkboxes">
              <label className="checkbox-label">
                <input
                  type="checkbox"
                  checked={fieldsConfig.participants}
                  onChange={() => toggleField('participants')}
                />
                Participants
              </label>
              <label className="checkbox-label">
                <input
                  type="checkbox"
                  checked={fieldsConfig.decisions}
                  onChange={() => toggleField('decisions')}
                />
                Decisions
              </label>
              <label className="checkbox-label">
                <input
                  type="checkbox"
                  checked={fieldsConfig.deadlines}
                  onChange={() => toggleField('deadlines')}
                />
                Deadlines
              </label>
              <label className="checkbox-label">
                <input
                  type="checkbox"
                  checked={fieldsConfig.topics}
                  onChange={() => toggleField('topics')}
                />
                Topics
              </label>
            </div>
          </div>

          {error && (
            <div className="form-error">{error}</div>
          )}

          <div className="form-actions">
            <button type="button" onClick={onClose} disabled={loading}>
              Cancel
            </button>
            <button type="submit" disabled={loading}>
              {loading ? 'Creating...' : 'Create Summary'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

export default SummaryCreateModal
