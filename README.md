# STT App - Speech to Text Application

Локальное веб-приложение для транскрибации аудио/видео файлов с использованием Evolution Cloud.ru Whisper Large v3, саммаризации и Advanced RAG системы.

## Архитектура

- **Frontend**: React + Vite
- **Backend**: FastAPI (Python)
- **Database**: PostgreSQL
- **Vector Store**: Qdrant (для RAG)
- **Deployment**: Docker Compose

## Быстрый старт

### Предварительные требования

- Docker и Docker Compose
- API ключи от Evolution Cloud.ru

### Установка

1. Клонируйте репозиторий:
```bash
git clone <repository-url>
cd STT-app
```

2. Создайте файл `.env` на основе `.env.example`:
```bash
cp .env.example .env
```

3. Заполните `.env` файл вашими API ключами:
```env
EVOLUTION_API_KEY=sk-your-api-key
EVOLUTION_BASE_URL=https://foundation-models.api.cloud.ru/api/gigacube/openai/v1
```

4. Запустите приложение:
```bash
docker-compose up -d
```

5. Откройте браузер:
- Frontend: http://localhost:5173
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

## Использование

### Загрузка и транскрибация

1. Перейдите на главную страницу (Upload)
2. Перетащите аудио/видео файлы или выберите их
3. Опционально выберите язык (или оставьте автоопределение)
4. Нажмите "Upload" для начала обработки
5. Перейдите в "Transcripts" для просмотра результатов

### Просмотр транскриптов

- Список всех транскриптов с фильтрацией по статусу и языку
- Детальный просмотр с текстом, JSON и SRT форматами
- Скачивание результатов в различных форматах

## API Endpoints

### Transcripts

- `POST /api/transcripts/upload` - Загрузка файла для транскрибации
- `GET /api/transcripts` - Список транскриптов
- `GET /api/transcripts/{id}` - Получить транскрипт по ID
- `DELETE /api/transcripts/{id}` - Удалить транскрипт

### Jobs

- `GET /api/jobs/{id}` - Статус обработки
- `GET /api/transcripts/{id}/jobs` - Все задачи для транскрипта

## Структура проекта

```
STT-app/
├── backend/           # FastAPI backend
│   ├── app/
│   │   ├── main.py    # Основное приложение
│   │   ├── database.py # Модели БД
│   │   ├── models.py  # Pydantic модели
│   │   └── services/  # Бизнес-логика
│   └── Dockerfile
├── frontend/          # React frontend
│   ├── src/
│   │   ├── pages/     # Страницы приложения
│   │   └── api/       # API клиент
│   └── Dockerfile
├── volumes/           # Persistent storage
│   ├── audio/         # Загруженные файлы
│   ├── transcripts/   # Результаты транскрибации
│   └── logs/          # Логи приложения
└── docker-compose.yml # Docker Compose конфигурация
```

## Разработка

### Backend

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

## Поддерживаемые форматы

- Аудио: mp3, mp4, mpeg, mpga, m4a, wav, webm
- Максимальный размер файла: 25MB (настраивается)

## Функциональность

### Фаза 1 (MVP) - ✅ Реализовано

- [x] Загрузка и транскрибация аудио файлов
- [x] Просмотр списка транскриптов
- [x] Детальный просмотр транскриптов
- [x] Экспорт в различных форматах (text, JSON, SRT)
- [x] Отслеживание статуса обработки

### Фаза 2 - В разработке

- [ ] Саммаризация транскриптов
- [ ] Обработка больших файлов (>25MB)
- [ ] Редактор транскриптов

### Фаза 3 - Планируется

- [ ] Advanced RAG система
- [ ] Мониторинг (Prometheus + Grafana)

## Лицензия

MIT

