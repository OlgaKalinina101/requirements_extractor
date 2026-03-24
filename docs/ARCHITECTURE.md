# Архитектура системы
**Requirements Management System (RMS) — прототип**

---

## Высокоуровневая архитектура

```
┌──────────────────────────────────────────────────────────────┐
│                         FRONTEND                              │
│  Vue 3 + Vuetify + PDF.js + WebSocket                       │
├──────────────────────────────────────────────────────────────┤
│  • Dashboard (список проектов и статистика)                  │
│  • Document Upload & Processing (прогресс-бар, модели)      │
│  • Requirements Review (Split View: PDF + Requirements)      │
│  • Requirement Detail (история изменений)                    │
│  • Coverage Metrics Panel                                     │
└──────────────────────────────────────────────────────────────┘
                            ↕ HTTP / WebSocket
┌──────────────────────────────────────────────────────────────┐
│                      API LAYER (FastAPI)                      │
├──────────────────────────────────────────────────────────────┤
│  REST API:                                                    │
│    /api/projects/*          - CRUD проектов                  │
│    /api/documents/*         - CRUD документов                │
│    /api/requirements/*      - CRUD требований                │
│    /api/extract             - загрузка PDF + извлечение      │
│    /api/documents/{id}/export/*  - Word / JSON / TXT         │
│    /api/documents/{id}/pdf  - PDF для просмотра              │
│    /api/models               - список AI-моделей для извлечения│
│  WebSocket:                                                   │
│    /ws/logs                 - real-time логи + прогресс      │
└──────────────────────────────────────────────────────────────┘
                            ↕
┌──────────────────────────────────────────────────────────────┐
│                    BUSINESS LOGIC LAYER                       │
├──────────────────────────────────────────────────────────────┤
│  src/extraction_service.py — ExtractionService               │
│    Оркестрирует полный pipeline: файл → PDF → AI → БД        │
│    Шаги: _save_file, _create_db_document, _init_extractor,   │
│           _extract_pdf_pages, _extract_requirements,           │
│           _refine_page_numbers (page_finder fallback),        │
│           _save_to_db, _save_coverage_metrics, _build_word    │
│                                                               │
│  src/requirements_extractor.py — RequirementsExtractor       │
│    LLM-клиент через src/llm/factory (BaseLLMClient)          │
│    Параллельная постраничная обработка батчами (batch_size=7)│
│    Текст + изображения на каждой странице                    │
│                                                               │
│  src/word_exporter.py — генерация Word из БД и из памяти    │
└──────────────────────────────────────────────────────────────┘
                            ↕
┌──────────────────────────────────────────────────────────────┐
│                    DATA ACCESS LAYER                          │
├──────────────────────────────────────────────────────────────┤
│  src/database/crud/ — CRUD-модули по доменам (requirements,  │
│    documents, projects, users и т.д.)                         │
│  src/database/models.py — SQLAlchemy ORM модели              │
│  src/database/database.py — QueuePool (size=5, overflow=10) │
└──────────────────────────────────────────────────────────────┘
                            ↕
┌──────────────────────────────────────────────────────────────┐
│                    DATABASE (PostgreSQL 16)                   │
├──────────────────────────────────────────────────────────────┤
│  Таблицы:                                                     │
│    projects              - проекты                           │
│    documents             - документы (с model_used)          │
│    document_pages        - текст и text_blocks по страницам  │
│    sections              - разделы документов                │
│    requirements          - извлечённые требования            │
│    coverage_metrics      - метрики покрытия                  │
│  Индексы (005_add_indexes):                                   │
│    ix_requirements_document_id                               │
│    ix_requirements_section_id                                │
│    ix_documents_project_id                                   │
│    ix_sections_document_id                                   │
└──────────────────────────────────────────────────────────────┘
                            ↕
┌──────────────────────────────────────────────────────────────┐
│                    AI / EXTERNAL SERVICES                     │
├──────────────────────────────────────────────────────────────┤
│  OpenRouter API — доступ к моделям:                          │
│    • claude-sonnet-4.5 (рекомендуется)                       │
│    • claude-opus-4.6                                         │
│    • gpt-4.1                                                 │
│    • qwen-3.5-plus                                           │
│    • gemini-3.1-pro                                          │
│  src/openrouter_client.py — HTTP + tenacity retry            │
└──────────────────────────────────────────────────────────────┘
```

---

## Модель данных

### ER-диаграмма

```
┌─────────────┐
│  projects   │
├─────────────┤
│ id          │──┐
│ name        │  │ 1:N
│ description │  │
│ created_at  │  ↓
└─────────────┘
            ┌──────────────┐
            │  documents   │
            ├──────────────┤
            │ id           │──┐
            │ project_id   │  │ 1:N
            │ filename     │  │
            │ file_path    │  ├──────────────────────┐
            │ status       │  ↓                      ↓
            │ total_pages  │  ┌──────────┐   ┌──────────────────┐
            │ model_used   │  │ sections │   │ coverage_metrics │
            │ uploaded_at  │  ├──────────┤   ├──────────────────┤
            └──────────────┘  │ id       │──┐│ document_id      │
                              │ doc_id   │  ││ total_pages      │
                              │ number   │  ││ processed_pages  │
                              │ title    │  ││ skipped_pages[]  │
                              │ page_start│ ││ coverage_percent │
                              │ page_end │  ││ requirements_by_type│
                              └──────────┘  │└──────────────────┘
                                            │
                                            │ 1:N
                                            ↓
                              ┌──────────────────────┐
                              │    requirements      │
                              ├──────────────────────┤
                              │ id                   │
                              │ document_id          │
                              │ section_id           │
                              │ requirement_id       │
                              │ text                 │
                              │ type                 │
                              │ priority             │
                              │ page_number          │
                              │ source_page          │
                              │ source_quote         │
                              │ source_type          │
                              │ status               │
                              │ ai_suggested         │
                              │ human_edited         │
                              │ edit_reason          │
                              │ edited_by / edited_at│
                              │ created_at           │
                              └──────────────────────┘
```

### Типы требований (RequirementType)

`technical`, `functional`, `organizational`, `non_functional`, `documentation`, `unknown`

### Приоритеты (RequirementPriority)

`mandatory`, `recommended`, `optional`, `unknown`

### Статусы требований

`pending` → `accepted` / `rejected` / `modified`

---

## Pipeline извлечения требований

### Последовательность шагов

```
POST /api/extract (PDF upload)
│
├─ [10%]  ExtractionService._save_file()
│          Сохранить PDF в data/uploads/{timestamp}_{filename}
│          Создать временный рабочий каталог
│
├─ [15%]  ExtractionService._create_db_document()
│          Создать запись Document в БД (status=pending)
│
├─ [20%]  ExtractionService._init_extractor()
│          Загрузить конфиг из .env
│          Создать RequirementsExtractor с выбранной моделью
│
├─ [25%]  ExtractionService._extract_pdf_pages()
│          PDFProcessor.extract_pages() — ThreadPoolExecutor
│          Каждая страница параллельно:
│            • pymupdf4llm → текст (Markdown)
│            • pymupdf4llm → изображения (PNG/JPG)
│          Результат: pages[], page_image_metadata{}
│
├─ [30–88%] ExtractionService._extract_requirements()
│          RequirementsExtractor.extract_requirements_from_all_pages()
│          Батчи по 7 страниц (asyncio.gather):
│            Для каждой страницы:
│            ├─ _async_extract_from_text_simple()
│            │   run_in_executor → OpenRouterClient.extract_requirements()
│            └─ _async_extract_from_image_simple() (если есть изображения)
│                run_in_executor → OpenRouterClient.extract_requirements_from_image()
│          Прогресс: completed_pages / total_pages, 30%→88%
│
├─ [89%]  ExtractionService._refine_page_numbers()
│          page_finder: fallback для source_page (текстовый поиск)
│
├─ [90%]  ExtractionService._save_to_db()
│          Создать одну секцию "All Pages"
│          crud.bulk_create_requirements() — bulk INSERT
│
│          ExtractionService._save_coverage_metrics()
│          Посчитать pages_with_requirements из source_page
│          Сохранить coverage_metrics
│
│          ExtractionService._finalize_db()
│          Обновить Document status → "completed"
│
├─ [95%]  ExtractionService._build_word() (если generate_word=True)
│          word_exporter.generate_word_document() — Word из памяти
│
└─ [100%] Вернуть ExtractionResult
           { success, requirements_count, document_id, model_used, ... }
```

### Параллельность и потоки

```
asyncio event loop (main thread)
    │
    ├─ await _extract_pdf_pages()
    │      ThreadPoolExecutor → PDFProcessor.extract_pages()
    │      (синхронный, CPU-bound, потоки)
    │
    └─ await _extract_requirements()
           asyncio.gather(*[page tasks]) — батч из 7 страниц параллельно
           Для каждой страницы:
               loop.run_in_executor(None, ai_client.extract_requirements)
               (синхронный HTTP-запрос, I/O-bound, потоки из пула)
```

---

## WebSocket прогресс

Фронтенд подключается к `ws://host/ws/logs` до отправки файла.

Все лог-сообщения от Python-логгеров (`api`, `src.openrouter_client`, `src.requirements_extractor`, `src.pdf_processor`) форвардятся через `WebSocketHandler` в виде:

```json
{"type": "log", "level": "INFO", "message": "...", "timestamp": "..."}
```

Явные прогресс-обновления:

```json
{"type": "progress", "step": "extract", "progress": 47, "message": "Обработано страниц: 12/25"}
```

Фронтенд (`DocumentUpload.vue`) реагирует на `type === "progress"` и обновляет прогресс-бар.

---

## Технологический стек

### Backend

| Компонент | Технология |
|---|---|
| Web-фреймворк | FastAPI 0.110+ |
| ASGI-сервер | Uvicorn |
| ORM | SQLAlchemy 2.0+ |
| Миграции | Alembic |
| БД | PostgreSQL 16 |
| PostgreSQL-драйвер | psycopg[binary] |
| PDF-обработка | pymupdf, pymupdf4llm |
| HTTP-клиент | requests + tenacity |
| Word-генерация | python-docx |
| Валидация | Pydantic v2 |
| Connection pool | QueuePool (size=5, overflow=10) |

### Frontend

| Компонент | Технология |
|---|---|
| Framework | Vue 3 (Composition API) |
| UI-библиотека | Vuetify 3 |
| Состояние | Pinia |
| Роутинг | Vue Router 4 |
| HTTP-клиент | Axios |
| PDF-просмотр | PDF.js (CDN) |
| Сборка | Vite |

### DevOps

| Компонент | Технология |
|---|---|
| Контейнеризация | Docker + Docker Compose |
| Reverse proxy | Nginx |
| БД в Docker | postgres:16-alpine |

---

## Структура проекта

```
test2/
│
├── api_server.py              # Точка входа: uvicorn, подключает src.api.app
│
├── src/
│   ├── extraction_service.py  # ExtractionService — оркестратор pipeline
│   ├── requirements_extractor.py  # Параллельная AI-обработка страниц
│   ├── api/                   # FastAPI приложение, роутеры, serializers
│   ├── llm/                   # BaseLLMClient, factory, json_utils
│   ├── openrouter_client.py   # HTTP-клиент OpenRouter (BaseLLMClient)
│   ├── word_exporter.py       # Генерация Word (из памяти и из БД)
│   ├── pdf_processor.py       # Парсинг PDF, извлечение изображений
│   ├── models.py              # Pydantic-модели (Requirement, Registry и т.д.)
│   ├── config.py              # ApplicationConfig, load_from_env()
│   ├── logger.py              # Настройка логгеров + ротация файлов
│   ├── usage_tracker.py       # Учёт токенов и стоимости AI-вызовов
│   └── database/
│       ├── database.py        # Engine (QueuePool), SessionLocal, init_db
│       ├── models.py          # SQLAlchemy ORM (Document, Requirement и т.д.)
│       └── crud/              # CRUD по доменам (requirements, documents, ...)
│
├── alembic/
│   ├── versions/
│   │   ├── 001_initial_schema.py
│   │   ├── 002_remove_enums.py
│   │   ├── 003_add_projects_and_model_used.py
│   │   ├── 004_add_subitems.py
│   │   └── 005_add_indexes.py
│   └── env.py
│
├── frontend-vue/
│   ├── src/
│   │   ├── App.vue                    # Глобальный snackbar (useNotificationsStore)
│   │   ├── main.js
│   │   ├── router/index.js
│   │   ├── services/api.js            # Централизованный API-слой (axios)
│   │   ├── stores/
│   │   │   ├── auth.js
│   │   │   ├── documents.js
│   │   │   ├── projects.js
│   │   │   ├── requirements.js
│   │   │   ├── dictionaries.js
│   │   │   ├── models.js              # AI-модели с /api/models
│   │   │   └── notifications.js       # Глобальные уведомления
│   │   ├── components/
│   │   │   ├── DocumentUpload.vue     # Загрузка + WebSocket прогресс
│   │   │   ├── ExtractionResults.vue  # Результаты + ссылки экспорта
│   │   │   ├── RequirementsList.vue
│   │   │   ├── RequirementCard.vue
│   │   │   ├── PDFViewer.vue          # PDF.js viewer
│   │   │   ├── MetricsPanel.vue
│   │   │   └── ProcessingStatus.vue
│   │   └── views/
│   │       ├── HomeView.vue
│   │       ├── ProjectsView.vue
│   │       ├── ProjectView.vue
│   │       ├── ReviewView.vue         # Split View: PDF + требования
│   │       ├── DashboardView.vue      # Статистика проектов из API
│   │       ├── ExecutorDashboardView.vue  # Дашборд исполнителя
│   │       ├── AllRequirementsView.vue   # Все требования системы
│   │       ├── RequirementDetailView.vue  # Детали + история изменений
│   │       └── AdminView.vue          # Справочники (статические)
│   ├── package.json
│   └── vite.config.js
│
├── data/uploads/              # Загруженные PDF-файлы
├── logs/                      # Лог-файлы (api.log, extractor.log и т.д.)
├── Dockerfile                 # Backend image
├── Dockerfile.frontend        # Frontend (nginx) image
├── docker-compose.yml
├── nginx.conf                 # Reverse proxy: / → frontend, /api/ + /ws/ → backend
├── requirements.txt
├── .env.example
└── docs/
    ├── ARCHITECTURE.md        # Этот файл
    ├── INSTALL.md
    ├── QUICK_TEST.md
    ├── PDF_PROCESSING_PIPELINE.md
    └── PDF_PROCESSING_DIAGRAM.md
```

---

## Ключевые решения и их обоснование

### QueuePool вместо NullPool

`NullPool` создаёт новое соединение с БД на каждый запрос. При параллельных AI-вызовах (батчи по 7 страниц) это приводит к исчерпанию соединений. Используется `QueuePool(pool_size=5, max_overflow=10, pool_pre_ping=True)`.

### db_session context manager

Все DB-сессии управляются через `with db_session() as db:` — гарантирует закрытие даже при исключении.

### BackgroundTasks для временных файлов

Экспортные файлы (Word, JSON, TXT) создаются как `NamedTemporaryFile(delete=False)` и удаляются через `BackgroundTasks(os.unlink, path)` после отдачи клиенту.

### FileResponse для PDF

`FileResponse` автоматически управляет файловым дескриптором в отличие от `StreamingResponse(open(...))`, который не закрывал файл.

### Монотонный прогресс-бар

Страницы обрабатываются параллельно, поэтому прогресс считается от `completed_pages` (счётчик завершённых), а не от номера страницы. Обновления из потоков отправляются через `asyncio.run_coroutine_threadsafe`.
