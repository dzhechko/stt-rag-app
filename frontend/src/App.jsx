import { BrowserRouter as Router, Routes, Route, Link } from 'react-router-dom'
import { FileText } from 'lucide-react'
import HomePage from './pages/HomePage'
import UploadPage from './pages/UploadPage'
import TranscriptsPage from './pages/TranscriptsPage'
import TranscriptDetailPage from './pages/TranscriptDetailPage'
import TranscriptEditPage from './pages/TranscriptEditPage'
import RAGChatPage from './pages/RAGChatPage'
import './App.css'

function App() {
  return (
    <Router>
      <div className="app">
        <nav className="navbar">
          <div className="nav-container">
            <Link to="/" className="nav-logo">
              <FileText size={28} />
              <span>STT App</span>
            </Link>
            <div className="nav-links">
              <Link to="/" className="nav-link">Главная</Link>
              <Link to="/upload" className="nav-link">Загрузка</Link>
              <Link to="/transcripts" className="nav-link">Транскрипты</Link>
              <Link to="/rag" className="nav-link">RAG Чат</Link>
            </div>
          </div>
        </nav>
        
        <main className="main-content">
          <Routes>
            <Route path="/" element={<HomePage />} />
            <Route path="/upload" element={<UploadPage />} />
            <Route path="/transcripts" element={<TranscriptsPage />} />
            <Route path="/transcripts/:id" element={<TranscriptDetailPage />} />
            <Route path="/transcripts/:id/edit" element={<TranscriptEditPage />} />
            <Route path="/rag" element={<RAGChatPage />} />
            <Route path="/rag/sessions/:sessionId" element={<RAGChatPage />} />
          </Routes>
        </main>
      </div>
    </Router>
  )
}

export default App

