import { useState, useEffect, useRef } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { ArrowLeft, Send, MessageSquare, History, X, Plus, ChevronDown, ChevronUp, FileText, ThumbsUp, ThumbsDown, Settings } from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { getTranscripts, getRAGSessions, createRAGSession, deleteRAGSession } from '../api/client'
import client from '../api/client'
import './RAGChatPage.css'

function ChunksDisplay({ chunks }) {
  const [expanded, setExpanded] = useState(false)
  
  if (!chunks || chunks.length === 0) return null
  
  return (
    <div className="chunks-display">
      <button 
        className="chunks-toggle"
        onClick={() => setExpanded(!expanded)}
      >
        <FileText size={14} />
        <span>{chunks.length} source{chunks.length > 1 ? 's' : ''} used</span>
        {expanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
      </button>
      {expanded && (
        <div className="chunks-list">
          {chunks.map((chunk, idx) => (
            <div key={idx} className="chunk-item">
              <div className="chunk-header">
                <span className="chunk-index">Source {idx + 1}</span>
                {chunk.score && (
                  <span className="chunk-score">Relevance: {(chunk.score * 100).toFixed(1)}%</span>
                )}
                {chunk.transcript_id && (
                  <span className="chunk-transcript-id">Transcript: {chunk.transcript_id.substring(0, 8)}...</span>
                )}
              </div>
              <div className="chunk-text">{chunk.chunk_text || chunk.text || 'No text available'}</div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

function FeedbackButtons({ messageId }) {
  const [feedback, setFeedback] = useState(null)
  const [submitting, setSubmitting] = useState(false)

  // Skip feedback for temporary IDs (non-session queries without saved message)
  if (!messageId || messageId.startsWith('temp-')) {
    return null
  }

  const handleFeedback = async (type) => {
    if (submitting || feedback === type) return
    
    setSubmitting(true)
    try {
      await client.post(`/rag/messages/${messageId}/feedback`, {
        feedback_type: type,
        comment: null
      })
      setFeedback(type)
    } catch (error) {
      console.error('Error submitting feedback:', error)
      alert('Failed to submit feedback')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="feedback-buttons">
      <button
        className={`feedback-btn ${feedback === 'positive' ? 'active' : ''}`}
        onClick={() => handleFeedback('positive')}
        disabled={submitting}
        title="This answer was helpful"
      >
        <ThumbsUp size={16} />
        <span>Helpful</span>
      </button>
      <button
        className={`feedback-btn ${feedback === 'negative' ? 'active' : ''}`}
        onClick={() => handleFeedback('negative')}
        disabled={submitting}
        title="This answer was not helpful"
      >
        <ThumbsDown size={16} />
        <span>Not helpful</span>
      </button>
    </div>
  )
}

function RAGChatPage() {
  const { sessionId: urlSessionId } = useParams()
  const navigate = useNavigate()
  const [question, setQuestion] = useState('')
  const [messages, setMessages] = useState([])
  const [loading, setLoading] = useState(false)
  const [transcripts, setTranscripts] = useState([])
  const [selectedTranscripts, setSelectedTranscripts] = useState([])
  const [useSession, setUseSession] = useState(false)
  const [currentSessionId, setCurrentSessionId] = useState(urlSessionId || null)
  const [sessions, setSessions] = useState([])
  const [showSessionSelector, setShowSessionSelector] = useState(false)
  const [sessionName, setSessionName] = useState('')
  const [showSettings, setShowSettings] = useState(false)
  const [ragSettings, setRagSettings] = useState({
    top_k: 5,
    model: 'GigaChat/GigaChat-2-Max',
    temperature: 0.3,
    use_reranking: true,
    use_query_expansion: true,
    use_multi_hop: false,
    use_hybrid_search: false,
    use_advanced_grading: false,
    reranker_model: 'ms-marco-MiniLM-L-6-v2'
  })
  const messagesEndRef = useRef(null)

  useEffect(() => {
    loadTranscripts()
    loadSessions()
    if (urlSessionId) {
      setCurrentSessionId(urlSessionId)
      setUseSession(true)
      loadSessionMessages(urlSessionId)
    }
  }, [urlSessionId])
  
  useEffect(() => {
    if (currentSessionId && useSession) {
      loadSessionMessages(currentSessionId)
    } else if (!useSession) {
      setMessages([])
      setCurrentSessionId(null)
    }
  }, [currentSessionId, useSession])

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const loadTranscripts = async () => {
    try {
      const data = await getTranscripts(0, 100, { status: 'completed' })
      console.log('Loaded transcripts:', data)
      if (data && data.transcripts) {
        setTranscripts(data.transcripts)
        console.log(`Successfully loaded ${data.transcripts.length} transcripts`)
      } else {
        console.warn('No transcripts in response:', data)
        setTranscripts([])
      }
    } catch (error) {
      console.error('Error loading transcripts:', error)
      console.error('Error details:', error.response?.data || error.message)
      setTranscripts([])
    }
  }

  const loadSessions = async () => {
    try {
      const data = await getRAGSessions()
      setSessions(data)
    } catch (error) {
      console.error('Error loading sessions:', error)
    }
  }

  const loadSessionMessages = async (sid) => {
    if (!sid) return
    try {
      const response = await client.get(`/rag/sessions/${sid}/messages`)
      const loadedMessages = []
      response.data.forEach(msg => {
        loadedMessages.push({
          type: 'question',
          content: msg.question
        })
        loadedMessages.push({
          type: 'answer',
          content: msg.answer,
          question: msg.question,
          qualityScore: msg.quality_score
        })
      })
      setMessages(loadedMessages)
    } catch (error) {
      console.error('Error loading session messages:', error)
    }
  }

  const handleCreateSession = async () => {
    if (!sessionName.trim()) return
    try {
      const newSession = await createRAGSession({
        session_name: sessionName.trim(),
        transcript_ids: selectedTranscripts.length > 0 ? selectedTranscripts : null
      })
      setCurrentSessionId(newSession.id)
      setUseSession(true)
      setSessionName('')
      setShowSessionSelector(false)
      await loadSessions()
      navigate(`/rag/chat/${newSession.id}`)
    } catch (error) {
      console.error('Error creating session:', error)
    }
  }

  const handleSelectSession = (sid) => {
    setCurrentSessionId(sid)
    setUseSession(true)
    setShowSessionSelector(false)
    navigate(`/rag/chat/${sid}`)
  }

  const handleDeleteSession = async (sid, e) => {
    e.stopPropagation()
    if (window.confirm('Delete this session?')) {
      try {
        await deleteRAGSession(sid)
        if (currentSessionId === sid) {
          setCurrentSessionId(null)
          setUseSession(false)
          setMessages([])
          navigate('/rag/chat')
        }
        await loadSessions()
      } catch (error) {
        console.error('Error deleting session:', error)
      }
    }
  }

  const handleClearHistory = () => {
    if (window.confirm('Clear current session history?')) {
      setMessages([])
      setCurrentSessionId(null)
      setUseSession(false)
      navigate('/rag/chat')
    }
  }

  const handleAsk = async () => {
    if (!question.trim()) return

    const userQuestion = question
    setQuestion('')
    setLoading(true)

    // Add user question to messages
    const userMessage = { type: 'question', content: userQuestion }
    setMessages(prev => [...prev, userMessage])

    try {
      let response
      const requestData = {
        question: userQuestion,
        transcript_ids: selectedTranscripts.length > 0 ? selectedTranscripts : null,
        top_k: ragSettings.top_k,
        model: ragSettings.model,
        temperature: ragSettings.temperature
      }
      
      if (useSession && currentSessionId) {
        response = await client.post(`/rag/sessions/${currentSessionId}/ask`, requestData)
      } else {
        response = await client.post('/rag/ask', requestData)
      }
      
             const answerMessage = {
               type: 'answer',
               content: response.data.answer,
               question: userQuestion,
               qualityScore: response.data.quality_score,
               qualityMetrics: response.data.quality_metrics || null,
               retrievedChunks: response.data.retrieved_chunks || [],
               sources: response.data.sources || [],
               messageId: response.data.message_id || null
             }
      setMessages(prev => [...prev, answerMessage])
    } catch (error) {
      console.error('Error asking question:', error)
      let errorText = error.response?.data?.detail || error.message || 'Unknown error'
      
      // Improve error messages for connection errors
      if (error.response?.status === 503 || errorText.toLowerCase().includes('connection')) {
        errorText = 'Ошибка подключения к API. Пожалуйста, проверьте:\n' +
          '1. Доступность Evolution API\n' +
          '2. Настройки API ключа и URL\n' +
          '3. Сетевое подключение\n\n' +
          `Детали: ${errorText}`
      }
      
      const errorMessage = {
        type: 'error',
        content: errorText
      }
      setMessages(prev => [...prev, errorMessage])
    } finally {
      setLoading(false)
    }
  }

  const toggleTranscript = (id) => {
    setSelectedTranscripts(prev =>
      prev.includes(id)
        ? prev.filter(tid => tid !== id)
        : [...prev, id]
    )
  }

  return (
    <div className="rag-chat-page">
      <div className="chat-header">
        <button className="btn-back" onClick={() => navigate('/transcripts')}>
          <ArrowLeft size={20} />
          Back
        </button>
        <h1>RAG Chat</h1>
        <div className="header-controls">
          <button
            className="btn-settings"
            onClick={() => setShowSettings(true)}
            title="RAG Settings"
          >
            <Settings size={18} />
            Settings
          </button>
        </div>
        <div className="session-controls">
          <label className="session-toggle">
            <input
              type="checkbox"
              checked={useSession}
              onChange={(e) => {
                setUseSession(e.target.checked)
                if (!e.target.checked) {
                  setCurrentSessionId(null)
                  setMessages([])
                  navigate('/rag/chat')
                }
              }}
            />
            <History size={16} />
            <span>Use History</span>
          </label>
          {useSession && (
            <>
              <button
                className="btn-session-select"
                onClick={() => setShowSessionSelector(!showSessionSelector)}
              >
                {currentSessionId ? 'Change Session' : 'Select Session'}
              </button>
              {currentSessionId && (
                <button
                  className="btn-clear-history"
                  onClick={handleClearHistory}
                >
                  Clear History
                </button>
              )}
            </>
          )}
        </div>
      </div>

      {showSessionSelector && (
        <div className="session-selector-modal">
          <div className="session-selector-content">
            <div className="session-selector-header">
              <h3>Manage Sessions</h3>
              <button onClick={() => setShowSessionSelector(false)}>
                <X size={20} />
              </button>
            </div>
            <div className="session-create">
              <input
                type="text"
                placeholder="New session name..."
                value={sessionName}
                onChange={(e) => setSessionName(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && handleCreateSession()}
              />
              <button onClick={handleCreateSession}>
                <Plus size={16} />
                Create
              </button>
            </div>
            <div className="sessions-list">
              {sessions.length > 0 ? (
                sessions.map(session => (
                  <div
                    key={session.id}
                    className={`session-item ${currentSessionId === session.id ? 'active' : ''}`}
                    onClick={() => handleSelectSession(session.id)}
                  >
                    <div className="session-info">
                      <span className="session-name">
                        {session.session_name || `Session ${session.id.slice(0, 8)}`}
                      </span>
                      <span className="session-date">
                        {new Date(session.created_at).toLocaleDateString()}
                      </span>
                    </div>
                    <button
                      className="btn-delete-session"
                      onClick={(e) => handleDeleteSession(session.id, e)}
                    >
                      <X size={16} />
                    </button>
                  </div>
                ))
              ) : (
                <p className="no-sessions">No sessions yet. Create one to start.</p>
              )}
            </div>
          </div>
        </div>
      )}

      <div className="chat-container">
        <div className="transcripts-sidebar">
          <h3>Select Transcripts</h3>
          <div className="transcripts-list">
            {transcripts.length === 0 ? (
              <p className="info-text" style={{ padding: '1rem', textAlign: 'center', color: '#7f8c8d' }}>
                No transcripts found. Upload some files first!
              </p>
            ) : (
              transcripts
                .sort((a, b) => new Date(b.created_at) - new Date(a.created_at))
                .map(transcript => {
                  const date = new Date(transcript.created_at)
                  const now = new Date()
                  const diffMs = now - date
                  const diffHours = Math.floor(diffMs / (1000 * 60 * 60))
                  const diffDays = Math.floor(diffHours / 24)
                  
                  let timeAgo = ''
                  if (diffDays > 0) {
                    timeAgo = `${diffDays} day${diffDays > 1 ? 's' : ''} ago`
                  } else if (diffHours > 0) {
                    timeAgo = `${diffHours} hour${diffHours > 1 ? 's' : ''} ago`
                  } else {
                    const diffMins = Math.floor(diffMs / (1000 * 60))
                    timeAgo = diffMins > 0 ? `${diffMins} min${diffMins > 1 ? 's' : ''} ago` : 'Just now'
                  }
                  
                  return (
                    <label key={transcript.id} className="transcript-checkbox">
                      <input
                        type="checkbox"
                        checked={selectedTranscripts.includes(transcript.id)}
                        onChange={() => toggleTranscript(transcript.id)}
                      />
                      <div className="transcript-info">
                        <span className="transcript-name">{transcript.original_filename}</span>
                        <span className="transcript-time">{timeAgo}</span>
                      </div>
                    </label>
                  )
                })
            )}
          </div>
          {selectedTranscripts.length === 0 && (
            <p className="info-text">No transcripts selected - searching all</p>
          )}
        </div>

        <div className="chat-main">
          <div className="messages-container">
            {messages.length === 0 ? (
              <div className="empty-chat">
                <MessageSquare size={48} />
                <p>Ask a question about your transcripts</p>
              </div>
            ) : (
              messages.map((msg, idx) => (
                <div key={idx} className={`message ${msg.type}`}>
                  {msg.type === 'question' && (
                    <div className="message-content">
                      <strong>You:</strong> {msg.content}
                    </div>
                  )}
                      {msg.type === 'answer' && (
                        <div className="message-content">
                          <strong>Assistant:</strong>
                          <div className="markdown-content">
                            <ReactMarkdown remarkPlugins={[remarkGfm]}>
                              {msg.content}
                            </ReactMarkdown>
                          </div>
                          {msg.qualityScore && (
                            <span className="quality-score">
                              Quality: {msg.qualityScore.toFixed(1)}/5.0
                            </span>
                          )}
                          {msg.qualityMetrics && (
                            <div className="quality-metrics">
                              <span>Groundedness: {(msg.qualityMetrics.groundedness * 100).toFixed(0)}%</span>
                              <span>Completeness: {(msg.qualityMetrics.completeness * 100).toFixed(0)}%</span>
                              <span>Relevance: {(msg.qualityMetrics.relevance * 100).toFixed(0)}%</span>
                            </div>
                          )}
                          {msg.retrievedChunks && msg.retrievedChunks.length > 0 && (
                            <ChunksDisplay chunks={msg.retrievedChunks} />
                          )}
                          <FeedbackButtons messageId={msg.messageId} />
                        </div>
                      )}
                  {msg.type === 'error' && (
                    <div className="message-content error">
                      {msg.content}
                    </div>
                  )}
                </div>
              ))
            )}
            {loading && (
              <div className="message loading">
                <div className="message-content">Thinking...</div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          <div className="input-container">
            <input
              type="text"
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              onKeyPress={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault()
                  handleAsk()
                }
              }}
              placeholder="Ask a question..."
              disabled={loading}
            />
            <button onClick={handleAsk} disabled={loading || !question.trim()}>
              <Send size={20} />
            </button>
          </div>
        </div>
      </div>

      {showSettings && (
        <div className="settings-modal-overlay" onClick={() => setShowSettings(false)}>
          <div className="settings-modal" onClick={(e) => e.stopPropagation()}>
            <div className="settings-header">
              <h3>RAG Settings</h3>
              <button onClick={() => setShowSettings(false)}>
                <X size={20} />
              </button>
            </div>
            <div className="settings-content">
              <div className="setting-item">
                <label htmlFor="top_k">
                  Number of chunks (top_k):
                  <span className="setting-hint">More chunks = more context, but may include noise</span>
                </label>
                <input
                  id="top_k"
                  type="number"
                  min="1"
                  max="20"
                  value={ragSettings.top_k}
                  onChange={(e) => setRagSettings({...ragSettings, top_k: parseInt(e.target.value) || 5})}
                />
              </div>
              <div className="setting-item">
                <label htmlFor="model">
                  Model for answer generation:
                </label>
                <select
                  id="model"
                  value={ragSettings.model}
                  onChange={(e) => setRagSettings({...ragSettings, model: e.target.value})}
                >
                  <option value="GigaChat/GigaChat-2-Max">GigaChat-2-Max (Default, best for Russian)</option>
                  <option value="Qwen/Qwen3-235B-A22B-Instruct-2507">Qwen3-235B (Best quality, slower)</option>
                  <option value="Qwen/Qwen3-Next-80B-A3B-Instruct">Qwen3-Next-80B (Balanced)</option>
                </select>
              </div>
              <div className="setting-item">
                <label htmlFor="temperature">
                  Temperature: {ragSettings.temperature}
                  <span className="setting-hint">Lower = more factual, Higher = more creative</span>
                </label>
                <input
                  id="temperature"
                  type="range"
                  min="0"
                  max="1"
                  step="0.1"
                  value={ragSettings.temperature}
                  onChange={(e) => setRagSettings({...ragSettings, temperature: parseFloat(e.target.value)})}
                />
                <div className="temperature-labels">
                  <span>0.0 (Factual)</span>
                  <span>1.0 (Creative)</span>
                </div>
              </div>
              <div className="setting-item">
                <label>
                  <input
                    type="checkbox"
                    checked={ragSettings.use_query_expansion}
                    onChange={(e) => setRagSettings({...ragSettings, use_query_expansion: e.target.checked})}
                  />
                  <span>Enable Query Expansion</span>
                </label>
                <span className="setting-hint">
                  Automatically reformulates question and generates hypothetical answer for better search
                </span>
              </div>
              <div className="setting-item">
                <label>
                  <input
                    type="checkbox"
                    checked={ragSettings.use_multi_hop}
                    onChange={(e) => setRagSettings({...ragSettings, use_multi_hop: e.target.checked})}
                  />
                  <span>Enable Multi-hop Reasoning</span>
                </label>
                <span className="setting-hint">
                  Breaks complex questions into sub-queries for deeper search (overrides Query Expansion)
                </span>
              </div>
              <div className="setting-item">
                <label>
                  <input
                    type="checkbox"
                    checked={ragSettings.use_hybrid_search}
                    onChange={(e) => setRagSettings({...ragSettings, use_hybrid_search: e.target.checked})}
                  />
                  <span>Enable Hybrid Search</span>
                </label>
                <span className="setting-hint">
                  Combines vector (semantic) and BM25 (keyword) search for better coverage
                </span>
              </div>
              <div className="setting-item">
                <label>
                  <input
                    type="checkbox"
                    checked={ragSettings.use_reranking}
                    onChange={(e) => setRagSettings({...ragSettings, use_reranking: e.target.checked})}
                  />
                  <span>Enable Reranking</span>
                </label>
                <span className="setting-hint">
                  Reorders retrieved chunks by relevance using specialized model for better accuracy
                </span>
              </div>
              <div className="setting-item">
                <label htmlFor="reranker_model">
                  Reranker Model:
                </label>
                <select
                  id="reranker_model"
                  value={ragSettings.reranker_model}
                  onChange={(e) => setRagSettings({...ragSettings, reranker_model: e.target.value})}
                >
                  <option value="ms-marco-MiniLM-L-6-v2">ms-marco-MiniLM-L-6-v2 (Fast, lightweight)</option>
                  <option value="bge-reranker-v2-m3">bge-reranker-v2-m3 (Better quality, slower)</option>
                  <option value="llm">LLM-based (Fallback)</option>
                </select>
              </div>
              <div className="setting-item">
                <label>
                  <input
                    type="checkbox"
                    checked={ragSettings.use_advanced_grading}
                    onChange={(e) => setRagSettings({...ragSettings, use_advanced_grading: e.target.checked})}
                  />
                  <span>Enable Advanced Quality Grading</span>
                </label>
                <span className="setting-hint">
                  Evaluates groundedness, completeness, and relevance of answers
                </span>
              </div>
              <div className="settings-info">
                <h4>Advanced RAG Algorithm Description</h4>
                <div className="algorithm-description">
                  <p><strong>Current Implementation:</strong></p>
                  <ol>
                    <li><strong>Multi-hop Reasoning</strong> (if enabled):
                      <ul>
                        <li>Automatically breaks complex questions into 2-4 sub-queries</li>
                        <li>Performs iterative search for each sub-question</li>
                        <li>Combines and deduplicates results for comprehensive coverage</li>
                      </ul>
                    </li>
                    <li><strong>Query Expansion</strong> (if enabled, when multi-hop is off):
                      <ul>
                        <li>Generates 2-3 alternative question formulations</li>
                        <li>Creates a hypothetical answer to improve search queries</li>
                        <li>Uses multiple queries to find more relevant chunks</li>
                      </ul>
                    </li>
                    <li><strong>Hybrid Search</strong> (if enabled):
                      <ul>
                        <li>Combines vector (semantic) search with BM25 (keyword) search</li>
                        <li>Weighted combination: 70% vector, 30% BM25 by default</li>
                        <li>Better coverage of both semantic and exact term matches</li>
                      </ul>
                    </li>
                    <li><strong>Vector Search</strong>:
                      <ul>
                        <li>Uses local embeddings model (all-MiniLM-L6-v2, dimension 384)</li>
                        <li>Cosine similarity for semantic search</li>
                        <li>Searches across selected transcripts or all indexed transcripts</li>
                      </ul>
                    </li>
                    <li><strong>Specialized Reranking</strong> (if enabled):
                      <ul>
                        <li>Uses cross-encoder model (ms-marco-MiniLM-L-6-v2 or bge-reranker-v2-m3)</li>
                        <li>Evaluates query-chunk pairs for better relevance scoring</li>
                        <li>Combines reranker score (70%) with original score (30%)</li>
                        <li>Fallback to LLM-based reranking if model unavailable</li>
                      </ul>
                    </li>
                    <li><strong>Answer Generation</strong>:
                      <ul>
                        <li>Uses selected LLM model (GigaChat-2-Max by default)</li>
                        <li>Generates answer based on retrieved context</li>
                        <li>Evaluates answer quality automatically</li>
                      </ul>
                    </li>
                    <li><strong>Advanced Quality Grading</strong> (if enabled):
                      <ul>
                        <li><strong>Groundedness</strong>: Checks if facts in answer are supported by retrieved chunks</li>
                        <li><strong>Completeness</strong>: Evaluates if answer covers all aspects of the question</li>
                        <li><strong>Relevance</strong>: Measures how relevant the answer is to the question</li>
                        <li>Returns detailed metrics (0.0-1.0 for each, overall score 0.0-5.0)</li>
                      </ul>
                    </li>
                  </ol>
                </div>
              </div>
            </div>
            <div className="settings-footer">
              <button onClick={() => setShowSettings(false)}>Close</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default RAGChatPage

