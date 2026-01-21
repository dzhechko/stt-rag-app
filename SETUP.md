# STT App - Setup Instructions

## Быстрый старт

### 1. Предварительные требования

- Docker и Docker Compose установлены
- API ключи от Evolution Cloud.ru

### 2. Настройка

1. Скопируйте файл `.env.example` в `.env`:
```bash
cp .env.example .env
```

2. Отредактируйте `.env` и добавьте ваши API ключи:
```env
EVOLUTION_API_KEY=sk-your-actual-api-key
EVOLUTION_BASE_URL=https://foundation-models.api.cloud.ru/v1
```

### 3. Запуск

```bash
docker-compose up -d
```

Это запустит:
- PostgreSQL (порт 5432)
- Backend API (порт 8000)
- Frontend (порт 5173)
- Qdrant (порт 6333)

### 4. Доступ к приложению

- **Frontend**: http://localhost:5173
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **Metrics (Prometheus)**: http://localhost:8000/metrics
- **Qdrant Dashboard**: http://localhost:6333/dashboard

## Использование

### Загрузка и транскрибация

1. Откройте http://localhost:5173
2. Перейдите на страницу "Upload"
3. Перетащите или выберите аудио/видео файл
4. Опционально выберите язык
5. Нажмите "Upload"
6. Дождитесь завершения обработки

### Просмотр транскриптов

1. Перейдите на страницу "Transcripts"
2. Просмотрите список всех транскриптов
3. Откройте транскрипт для детального просмотра
4. Скачайте результаты в различных форматах (TXT, JSON, SRT)

### Редактирование транскриптов

1. Откройте транскрипт
2. Нажмите "Edit"
3. Внесите изменения в текст
4. Добавьте теги и категорию
5. Сохраните изменения

### Саммаризация

1. После завершения транскрибации используйте API для создания саммари:
```bash
curl -X POST http://localhost:8000/api/summaries \
  -H "Content-Type: application/json" \
  -d '{
    "transcript_id": "your-transcript-id",
    "template": "meeting",
    "fields_config": {
      "participants": true,
      "decisions": true,
      "deadlines": true
    }
  }'
```

### RAG Chat

1. Перейдите на страницу "RAG Chat"
2. Выберите транскрипты для поиска (или оставьте пустым для поиска по всем)
3. Задайте вопрос
4. Получите ответ на основе содержимого транскриптов

## Мониторинг

### Prometheus метрики

Доступны по адресу: http://localhost:8000/metrics

Основные метрики:
- `stt_transcription_requests_total` - количество запросов на транскрибацию
- `stt_transcription_duration_seconds` - время обработки транскрибаций
- `stt_summarization_requests_total` - количество запросов на саммаризацию
- `stt_rag_queries_total` - количество RAG запросов
- `stt_rag_query_duration_seconds` - время обработки RAG запросов

## Troubleshooting

### Проблемы с подключением к БД

Убедитесь, что PostgreSQL контейнер запущен:
```bash
docker-compose ps
```

### Проблемы с Qdrant

Qdrant должен быть доступен на порту 6333. Проверьте логи:
```bash
docker-compose logs qdrant
```

### Проблемы с API ключами

Убедитесь, что в `.env` файле указаны правильные ключи:
```bash
cat .env | grep EVOLUTION
```

### Очистка данных

Для полной очистки всех данных:
```bash
docker-compose down -v
```

Это удалит все volumes, включая базу данных и файлы.

## Разработка

### Backend разработка

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### Frontend разработка

```bash
cd frontend
npm install
npm run dev
```

## Структура проекта

```
STT-app/
├── backend/              # FastAPI backend
│   ├── app/
│   │   ├── main.py      # Основное приложение
│   │   ├── database.py   # Модели БД
│   │   ├── models.py    # Pydantic модели
│   │   ├── services/     # Бизнес-логика
│   │   └── monitoring.py # Prometheus метрики
│   └── Dockerfile
├── frontend/            # React frontend
│   ├── src/
│   │   ├── pages/       # Страницы
│   │   └── api/         # API клиент
│   └── Dockerfile
├── volumes/             # Persistent storage
│   ├── audio/           # Загруженные файлы
│   ├── transcripts/     # Результаты
│   └── logs/            # Логи
├── docker-compose.yml   # Docker Compose конфигурация
└── README.md            # Основная документация
```

## Поддерживаемые форматы

- **Аудио**: mp3, mp4, mpeg, mpga, m4a, wav, webm
- **Максимальный размер**: 25MB на запрос (автоматическое разбиение для больших файлов)

## API Endpoints

Основные endpoints:
- `POST /api/transcripts/upload` - Загрузка файла
- `GET /api/transcripts` - Список транскриптов
- `GET /api/transcripts/{id}` - Получить транскрипт
- `PUT /api/transcripts/{id}` - Обновить транскрипт
- `POST /api/summaries` - Создать саммари
- `POST /api/rag/ask` - Задать вопрос RAG
- `GET /metrics` - Prometheus метрики

Полная документация доступна по адресу: http://localhost:8000/docs

