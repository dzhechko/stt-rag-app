import { Link } from 'react-router-dom'
import { FileText, MessageSquare, Database, ArrowRight } from 'lucide-react'
import './HomePage.css'

function HomePage() {
  return (
    <div className="home-page">
      {/* Hero Section */}
      <div className="hero-section">
        <div className="hero-badge">
          <span>АНАЛИЗ СИСТЕМЫ ЗАВЕРШЕН</span>
        </div>
        <h1 className="hero-title">
          <span className="hero-title-main">STT</span> APP: ТРАНСКРИПЦИЯ И RAG
        </h1>
        <p className="hero-description">
          Полнофункциональная платформа для транскрипции аудио и работы с Retrieval-Augmented Generation. 
          Исследуйте возможности транскрипции, управления документами и интеллектуального поиска в интерактивной среде.
        </p>
        <div className="hero-buttons">
          <Link to="/transcripts" className="btn-hero btn-hero-primary">
            <span>ИССЛЕДОВАТЬ ИНТЕРФЕЙС</span>
            <ArrowRight size={20} />
          </Link>
          <Link to="/rag" className="btn-hero btn-hero-secondary">
            <span>RAG ЧАТ</span>
          </Link>
        </div>
      </div>

      {/* Key Features Section */}
      <div className="features-section">
        <h2 className="features-title">КЛЮЧЕВЫЕ ВОЗМОЖНОСТИ</h2>
        <div className="features-grid">
          <div className="feature-card">
            <div className="feature-icon">
              <FileText size={32} />
            </div>
            <h3 className="feature-title">ТРАНСКРИПЦИЯ АУДИО</h3>
            <p className="feature-subtitle">Высокоточное преобразование речи в текст</p>
            <p className="feature-description">
              Загружайте аудиофайлы различных форматов и получайте точные транскрипции с поддержкой 
              множества языков и автоматической обработкой.
            </p>
          </div>

          <div className="feature-card">
            <div className="feature-icon">
              <MessageSquare size={32} />
            </div>
            <h3 className="feature-title">RAG ЧАТ</h3>
            <p className="feature-subtitle">Интеллектуальный поиск по документам</p>
            <p className="feature-description">
              Задавайте вопросы на основе транскрипций с использованием Retrieval-Augmented Generation. 
              Получайте точные ответы с указанием источников.
            </p>
          </div>

          <div className="feature-card">
            <div className="feature-icon">
              <Database size={32} />
            </div>
            <h3 className="feature-title">УПРАВЛЕНИЕ ДАННЫМИ</h3>
            <p className="feature-subtitle">Централизованное хранение и обработка</p>
            <p className="feature-description">
              Управляйте транскрипциями, создавайте суммаризации, индексируйте документы для поиска 
              и отслеживайте историю обработки.
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}

export default HomePage

