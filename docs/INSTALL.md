# Установка и запуск

## Быстрый старт (Docker Compose — рекомендуется)

```bash
# 1. Скопировать файл с переменными окружения
cp .env.example .env

# 2. Добавить API-ключ в .env
OPENROUTER_API_KEY=sk-or-v1-твой-ключ

# 3. Запустить всё одной командой
docker compose up --build
```

После запуска:
- **Frontend** → http://localhost:8080
- **Backend API** → http://localhost:8000
- **API Docs** → http://localhost:8000/docs

---

## Локальный запуск (без Docker)

### 1. Требования

- Python 3.11+
- Node.js 20+
- PostgreSQL 16+

### 2. Backend

```bash
# Установить зависимости
pip install -r requirements.txt

# Настроить .env
cp .env.example .env
# Заполнить OPENROUTER_API_KEY и DATABASE_URL

# Применить миграции
alembic upgrade head

# Запустить сервер
python api_server.py
```

Сервер запустится на `http://localhost:8000`

### 3. Frontend

```bash
cd frontend-vue
npm install
npm run dev
```

Frontend запустится на `http://localhost:5173`

---

## Переменные окружения

| Переменная | Обязательная | Описание |
|---|---|---|
| `OPENROUTER_API_KEY` | ✅ | API-ключ OpenRouter (https://openrouter.ai/keys) |
| `DATABASE_URL` | ✅ | URL PostgreSQL (`postgresql://user:pass@host:5432/db`) |
| `ALLOWED_ORIGINS` | — | CORS: список origins через запятую (default: `http://localhost:5173,http://localhost:8080`) |
| `LOG_LEVEL` | — | Уровень логов: `DEBUG`, `INFO` (по умолчанию), `WARNING` |

---

## Зависимости Python

| Пакет | Назначение |
|---|---|
| `fastapi` + `uvicorn` | Web-фреймворк и ASGI-сервер |
| `sqlalchemy` + `alembic` | ORM и миграции БД |
| `psycopg[binary]` | PostgreSQL драйвер |
| `pymupdf` + `pymupdf4llm` | Обработка PDF |
| `requests` + `tenacity` | HTTP-клиент + retry-логика |
| `python-docx` | Генерация Word-документов |
| `pydantic` | Валидация данных |
| `python-dotenv` | Загрузка `.env` |

---

## Миграции БД

### Через Docker (рекомендуется)

Миграции применяются автоматически при старте API-контейнера. Для ручного запуска:

```bash
# Применить все миграции
docker compose run --rm api alembic upgrade head

# Откатить последнюю
docker compose run --rm api alembic downgrade -1

# Статус
docker compose run --rm api alembic current
```

### Локально (без Docker)

```bash
# Применить все миграции
alembic upgrade head

# Откатить последнюю
alembic downgrade -1

# Статус
alembic current
```

Файлы миграций: `alembic/versions/`

| Миграция | Описание |
|---|---|
| `001_initial_schema` | Начальная схема (projects, documents, requirements, sections, metrics) |
| `002_remove_enums` | Замена PostgreSQL enum-типов на VARCHAR |
| `003_add_projects_and_model_used` | Добавлен `model_used` в documents |
| `004_add_subitems` | Подтребования (subitems) |
| `005_add_indexes` | Индексы на FK-колонках для производительности |
| `006_add_users_and_auth` | Пользователи, JWT |
| `007_add_dictionary_items` | Справочники |
| `008_add_requirement_history` | История изменений требований |
| `009_add_discipline_deadline` | Дисциплина, сроки |
| `010_add_parent_id` | Иерархия требований |
| `011_add_verification_method_and_document_type` | Метод верификации, тип документа |
| `012_add_requirement_links` | Связи между требованиями |
| `013_add_project_requirement_manager` | Менеджер требований проекта |
| `014_add_lifecycle_status` | Статус жизненного цикла |
| `015_prompts_table` | Таблица промптов |
| `016_add_document_pages` | Страницы документов, text_blocks |
| `017_add_source_quote` | Цитата из источника |
