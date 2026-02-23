# Architecture - Система управления требованиями
**Requirements Management System (RMS)**

---

## 🏗️ Высокоуровневая архитектура

```
┌──────────────────────────────────────────────────────────────┐
│                         FRONTEND                              │
│  Vue 3 + Vuetify + PDF.js + WebSocket                       │
├──────────────────────────────────────────────────────────────┤
│  • Projects Dashboard                                         │
│  • Document Upload & Processing                               │
│  • Requirements Review (Split View: PDF + Requirements)      │
│  • Diff View (версии документов)                            │
│  • Coverage Metrics & Analytics                               │
└──────────────────────────────────────────────────────────────┘
                            ↕ HTTP/WebSocket
┌──────────────────────────────────────────────────────────────┐
│                      API LAYER (FastAPI)                      │
├──────────────────────────────────────────────────────────────┤
│  REST API:                                                    │
│    /api/projects/*          - CRUD проектов                  │
│    /api/documents/*         - CRUD документов                │
│    /api/requirements/*      - CRUD требований                │
│    /api/upload              - загрузка PDF                   │
│    /api/extract             - запуск извлечения              │
│    /api/diff                - сравнение версий               │
│    /api/review              - accept/reject/edit             │
│    /api/metrics             - метрики покрытия               │
│  WebSocket:                                                   │
│    /ws/logs                 - real-time логи                 │
│    /ws/progress             - прогресс обработки             │
└──────────────────────────────────────────────────────────────┘
                            ↕
┌──────────────────────────────────────────────────────────────┐
│                    BUSINESS LOGIC LAYER                       │
├──────────────────────────────────────────────────────────────┤
│  Services:                                                    │
│    • ProjectService        - управление проектами            │
│    • DocumentService       - управление документами          │
│    • ExtractionService     - оркестрация извлечения          │
│    • DiffService           - сравнение версий                │
│    • ReviewService         - обработка review действий       │
│    • MetricsService        - расчет метрик                   │
└──────────────────────────────────────────────────────────────┘
                            ↕
┌──────────────────────────────────────────────────────────────┐
│                    DATA ACCESS LAYER                          │
├──────────────────────────────────────────────────────────────┤
│  CRUD Operations (SQLAlchemy):                               │
│    • ProjectCRUD                                             │
│    • DocumentCRUD                                            │
│    • RequirementCRUD                                         │
│    • RelationCRUD                                            │
└──────────────────────────────────────────────────────────────┘
                            ↕
┌──────────────────────────────────────────────────────────────┐
│                    DATABASE (PostgreSQL)                      │
├──────────────────────────────────────────────────────────────┤
│  Tables:                                                      │
│    • projects              - проекты                         │
│    • documents             - документы (с версионностью)     │
│    • sections              - разделы документов              │
│    • requirements          - извлеченные требования          │
│    • requirement_relations - связи (дубли, противоречия)     │
│    • coverage_metrics      - метрики покрытия                │
│    • audit_log             - аудит действий                  │
└──────────────────────────────────────────────────────────────┘
                            ↕
┌──────────────────────────────────────────────────────────────┐
│                    EXTRACTION ENGINE                          │
├──────────────────────────────────────────────────────────────┤
│  Components:                                                  │
│    • PDFProcessor          - извлечение текста + bbox        │
│    • DeepSeekClient        - AI анализ (async)               │
│    • RequirementsExtractor - оркестратор                     │
│    • UsageTracker          - трекинг использования AI        │
└──────────────────────────────────────────────────────────────┘
                            ↕
┌──────────────────────────────────────────────────────────────┐
│                    EXTERNAL SERVICES                          │
├──────────────────────────────────────────────────────────────┤
│    • DeepSeek API          - извлечение требований           │
│    • File Storage          - хранение PDF (local/S3)         │
│    • Redis (optional)      - кэш + очереди                   │
└──────────────────────────────────────────────────────────────┘
```

---

## 📊 Модель данных (детально)

### ER-диаграмма

```
┌─────────────┐
│  projects   │
├─────────────┤
│ id          │──┐
│ name        │  │
│ description │  │
│ created_at  │  │
└─────────────┘  │
                 │
                 │ 1:N
                 │
                 ↓
            ┌──────────────┐
            │  documents   │
            ├──────────────┤
            │ id           │──┐
            │ project_id   │  │
            │ filename     │  │
            │ version      │  │
            │ file_path    │  │
            │ status       │  │
            │ total_pages  │  │
            └──────────────┘  │
                              │
                              │ 1:N
                              │
         ┌────────────────────┼────────────────────┐
         ↓                    ↓                    ↓
    ┌──────────┐      ┌──────────────┐    ┌──────────────────┐
    │ sections │      │ requirements │    │ coverage_metrics │
    ├──────────┤      ├──────────────┤    ├──────────────────┤
    │ id       │──┐   │ id           │    │ id               │
    │ doc_id   │  │   │ document_id  │    │ document_id      │
    │ number   │  │   │ section_id   │    │ total_pages      │
    │ title    │  │   │ text         │    │ processed_pages  │
    │ ...      │  │   │ type         │    │ coverage_percent │
    └──────────┘  │   │ priority     │    └──────────────────┘
                  │   │ page_number  │
                  │   │ bbox         │
                  │   │ status       │
                  │   │ ai_suggested │
                  │ ┌─│ human_edited │
                  │ │ │ ...          │
                  │ │ └──────────────┘
                  │ │         │
                  │ │         │ M:N
                  │ │         ↓
                  │ │ ┌────────────────────────┐
                  │ │ │ requirement_relations  │
                  │ │ ├────────────────────────┤
                  │ └─│ requirement_id         │
                  │   │ related_id             │
                  └───│ relation_type          │
                      │ confidence             │
                      │ status                 │
                      └────────────────────────┘
```

### Таблицы и индексы

#### 1. projects

```sql
CREATE TABLE projects (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL UNIQUE,
    description TEXT,
    created_by VARCHAR(255),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_projects_created_at ON projects(created_at DESC);
```

**Примеры запросов:**
- Список всех проектов: `SELECT * FROM projects ORDER BY created_at DESC`
- Поиск по имени: `SELECT * FROM projects WHERE name ILIKE '%складом%'`

---

#### 2. documents

```sql
CREATE TABLE documents (
    id SERIAL PRIMARY KEY,
    project_id INTEGER REFERENCES projects(id) ON DELETE CASCADE,
    filename VARCHAR(255) NOT NULL,
    version INTEGER DEFAULT 1,
    file_path TEXT NOT NULL,
    file_size BIGINT,
    file_hash VARCHAR(64),  -- SHA256 для дедупликации
    
    -- Статус обработки
    status VARCHAR(50) DEFAULT 'pending',
    -- pending, processing, completed, failed
    
    -- Метаданные
    total_pages INTEGER,
    language VARCHAR(10) DEFAULT 'ru',
    
    -- Временные метки
    uploaded_at TIMESTAMP DEFAULT NOW(),
    processing_started_at TIMESTAMP,
    processing_completed_at TIMESTAMP,
    
    -- Кто загрузил
    uploaded_by VARCHAR(255),
    
    UNIQUE(project_id, filename, version)
);

CREATE INDEX idx_documents_project ON documents(project_id);
CREATE INDEX idx_documents_status ON documents(status);
CREATE INDEX idx_documents_version ON documents(project_id, filename, version);
CREATE INDEX idx_documents_hash ON documents(file_hash);  -- для дедупликации
```

**Примеры запросов:**
- Все документы проекта: `SELECT * FROM documents WHERE project_id = 1 ORDER BY version DESC`
- Последняя версия: `SELECT * FROM documents WHERE project_id = 1 AND filename = 'TZ.pdf' ORDER BY version DESC LIMIT 1`
- В обработке: `SELECT * FROM documents WHERE status = 'processing'`

---

#### 3. sections

```sql
CREATE TABLE sections (
    id SERIAL PRIMARY KEY,
    document_id INTEGER REFERENCES documents(id) ON DELETE CASCADE,
    section_number VARCHAR(50),  -- "1", "1.1", "1.1.1"
    title TEXT NOT NULL,
    level INTEGER,  -- 1, 2, 3 (вложенность)
    page_start INTEGER NOT NULL,
    page_end INTEGER,
    content TEXT,  -- markdown текст раздела
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_sections_document ON sections(document_id);
CREATE INDEX idx_sections_pages ON sections(document_id, page_start, page_end);
```

**Примеры запросов:**
- Все разделы документа: `SELECT * FROM sections WHERE document_id = 1 ORDER BY section_number`
- Раздел по странице: `SELECT * FROM sections WHERE document_id = 1 AND page_start <= 15 AND page_end >= 15`

---

#### 4. requirements (главная таблица)

```sql
CREATE TABLE requirements (
    id SERIAL PRIMARY KEY,
    document_id INTEGER REFERENCES documents(id) ON DELETE CASCADE,
    section_id INTEGER REFERENCES sections(id) ON DELETE SET NULL,
    
    -- Идентификация
    requirement_id VARCHAR(50) NOT NULL,  -- REQ-1-001
    
    -- Содержимое
    text TEXT NOT NULL,
    
    -- Классификация (может быть NULL если AI не уверен)
    type VARCHAR(50),
    -- technical, functional, organizational, documentation, non_functional, other
    
    priority VARCHAR(50),
    -- mandatory, recommended, optional
    
    -- Привязка к документу
    page_number INTEGER,
    bbox JSONB,  -- {x, y, width, height} координаты на странице
    
    -- Метаданные извлечения
    extraction_confidence FLOAT,  -- уверенность AI (0-1)
    extraction_method VARCHAR(50),  -- ai, manual, imported
    
    -- Статус обработки человеком
    status VARCHAR(50) DEFAULT 'pending',
    -- pending, accepted, rejected, modified, archived
    
    -- Аудит (ключевая фича!)
    ai_suggested TEXT NOT NULL,    -- что предложил AI (неизменяемое)
    human_edited TEXT,             -- что изменил человек
    edit_reason TEXT,              -- причина изменения
    edited_by VARCHAR(255),
    edited_at TIMESTAMP,
    
    -- Временные метки
    created_at TIMESTAMP DEFAULT NOW(),
    
    UNIQUE(document_id, requirement_id)
);

-- Индексы для производительности
CREATE INDEX idx_requirements_document ON requirements(document_id);
CREATE INDEX idx_requirements_section ON requirements(section_id);
CREATE INDEX idx_requirements_page ON requirements(document_id, page_number);
CREATE INDEX idx_requirements_status ON requirements(status);
CREATE INDEX idx_requirements_type ON requirements(type);
CREATE INDEX idx_requirements_priority ON requirements(priority);

-- Составной индекс для частых запросов
CREATE INDEX idx_requirements_doc_status ON requirements(document_id, status);

-- Full-text search по тексту требований
CREATE INDEX idx_requirements_text_search ON requirements USING gin(to_tsvector('russian', text));
```

**Примеры запросов:**
- Все требования документа: `SELECT * FROM requirements WHERE document_id = 1`
- Непроверенные: `SELECT * FROM requirements WHERE document_id = 1 AND status = 'pending'`
- По странице: `SELECT * FROM requirements WHERE document_id = 1 AND page_number = 15`
- Поиск по тексту: `SELECT * FROM requirements WHERE to_tsvector('russian', text) @@ to_tsquery('russian', 'пользовател')`
- Измененные человеком: `SELECT * FROM requirements WHERE human_edited IS NOT NULL`

---

#### 5. requirement_relations (для diff)

```sql
CREATE TABLE requirement_relations (
    id SERIAL PRIMARY KEY,
    requirement_id INTEGER REFERENCES requirements(id) ON DELETE CASCADE,
    related_id INTEGER REFERENCES requirements(id) ON DELETE CASCADE,
    
    -- Тип связи
    relation_type VARCHAR(50) NOT NULL,
    -- duplicates, contradicts, refines, depends_on, similar
    
    -- Метаданные
    confidence FLOAT,  -- уверенность AI в связи (0-1)
    similarity_score FLOAT,  -- для дублей
    explanation TEXT,  -- почему AI считает это связью
    
    -- Статус проверки человеком
    status VARCHAR(50) DEFAULT 'pending',
    -- pending, confirmed, rejected
    
    verified_by VARCHAR(255),
    verified_at TIMESTAMP,
    
    created_at TIMESTAMP DEFAULT NOW(),
    
    -- Нельзя связать требование само с собой
    CHECK (requirement_id != related_id),
    -- Уникальная пара (в одну сторону)
    UNIQUE(requirement_id, related_id, relation_type)
);

CREATE INDEX idx_relations_requirement ON requirement_relations(requirement_id);
CREATE INDEX idx_relations_related ON requirement_relations(related_id);
CREATE INDEX idx_relations_type ON requirement_relations(relation_type);
CREATE INDEX idx_relations_status ON requirement_relations(status);

-- Составной для поиска связей обоих направлений
CREATE INDEX idx_relations_bidirectional ON requirement_relations(
    LEAST(requirement_id, related_id),
    GREATEST(requirement_id, related_id)
);
```

**Примеры запросов:**
- Все связи требования: `SELECT * FROM requirement_relations WHERE requirement_id = 123 OR related_id = 123`
- Дубли: `SELECT * FROM requirement_relations WHERE relation_type = 'duplicates'`
- Противоречия: `SELECT * FROM requirement_relations WHERE relation_type = 'contradicts' AND status = 'pending'`

---

#### 6. coverage_metrics

```sql
CREATE TABLE coverage_metrics (
    id SERIAL PRIMARY KEY,
    document_id INTEGER REFERENCES documents(id) ON DELETE CASCADE,
    
    -- Общая статистика
    total_pages INTEGER NOT NULL,
    processed_pages INTEGER NOT NULL,
    skipped_pages INTEGER[],  -- массив номеров страниц
    
    -- Покрытие
    coverage_percent FLOAT,  -- (processed / total) * 100
    
    -- Статистика требований
    requirements_count INTEGER,
    requirements_by_type JSONB,  -- {"technical": 15, "functional": 20, ...}
    requirements_by_priority JSONB,
    
    -- Временные метки
    calculated_at TIMESTAMP DEFAULT NOW(),
    
    UNIQUE(document_id)
);

CREATE INDEX idx_coverage_document ON coverage_metrics(document_id);
```

**Примеры запросов:**
- Метрики документа: `SELECT * FROM coverage_metrics WHERE document_id = 1`
- Документы с низким покрытием: `SELECT d.*, c.coverage_percent FROM documents d JOIN coverage_metrics c ON d.id = c.document_id WHERE c.coverage_percent < 80`

---

#### 7. audit_log (опционально, для детального аудита)

```sql
CREATE TABLE audit_log (
    id BIGSERIAL PRIMARY KEY,
    
    -- Что изменилось
    entity_type VARCHAR(50) NOT NULL,  -- requirement, document, project
    entity_id INTEGER NOT NULL,
    action VARCHAR(50) NOT NULL,  -- created, updated, deleted, accepted, rejected
    
    -- Кто и когда
    user_id VARCHAR(255),
    timestamp TIMESTAMP DEFAULT NOW(),
    
    -- Детали изменения
    old_value JSONB,
    new_value JSONB,
    changes JSONB,  -- diff между old и new
    
    -- IP и user-agent для безопасности
    ip_address INET,
    user_agent TEXT
);

CREATE INDEX idx_audit_entity ON audit_log(entity_type, entity_id);
CREATE INDEX idx_audit_user ON audit_log(user_id);
CREATE INDEX idx_audit_timestamp ON audit_log(timestamp DESC);
```

---

## 🔄 Workflow и потоки данных

### 1. Загрузка и обработка документа

```
USER → Upload PDF
  ↓
[API] POST /api/upload
  ↓
[DocumentService]
  • Сохранить файл в storage
  • Создать запись в DB (status=pending)
  • Вычислить file_hash
  • Проверить дедупликацию
  ↓
[API] POST /api/extract/{document_id}
  ↓
[ExtractionService]
  ├─→ [PDFProcessor] 
  │    • Извлечь текст
  │    • Извлечь bbox координаты
  │    • Создать sections в DB
  │
  ├─→ [DeepSeekClient]
  │    • Извлечь требования (async, parallel)
  │    • Классификация (type, priority)
  │
  ├─→ [RequirementCRUD]
  │    • Сохранить в DB
  │    • ai_suggested = full text
  │    • status = pending
  │
  └─→ [MetricsService]
       • Рассчитать coverage
       • Сохранить метрики
  ↓
[WebSocket] → FRONTEND
  • Real-time прогресс
  • Уведомление о завершении
```

---

### 2. Review процесс (Accept/Reject/Edit)

```
USER → Review requirement в UI
  ↓
[UI] Split view:
  • PDF viewer (подсветка bbox)
  • Requirement card
  ↓
USER → Action (Accept / Reject / Edit)
  ↓
[API] POST /api/review/{requirement_id}
{
  "action": "accept" | "reject" | "edit",
  "edited_text": "...",  // если edit
  "edit_reason": "..."   // опционально
}
  ↓
[ReviewService]
  ├─→ IF accept:
  │    • status = accepted
  │    • human_edited = NULL (оставляем AI версию)
  │
  ├─→ IF reject:
  │    • status = rejected
  │    • edit_reason записываем
  │
  └─→ IF edit:
       • status = modified
       • human_edited = new text
       • edited_by = current_user
       • edited_at = NOW()
  ↓
[AuditLog] (опционально)
  • Записать изменение
  ↓
RESPONSE → FRONTEND
  • Обновить UI
  • Перейти к следующему requirement
```

---

### 3. Diff между версиями (v1 → v2)

```
USER → Upload v2 of document
  ↓
[DocumentService]
  • Определить version = 2
  • Связать с project
  ↓
[API] POST /api/diff
{
  "document_v1_id": 1,
  "document_v2_id": 2
}
  ↓
[DiffService]
  ├─→ Загрузить requirements v1
  ├─→ Загрузить requirements v2
  │
  ├─→ [RequirementMatcher]
  │    • Найти идентичные (similarity > 0.95)
  │    • Найти похожие (0.7 < similarity < 0.95)
  │    • Найти новые (только в v2)
  │    • Найти удаленные (только в v1)
  │    • Найти противоречия (semantic analysis)
  │
  └─→ Создать requirement_relations
       • type = duplicates / contradicts / similar
       • confidence = similarity score
       • status = pending
  ↓
RESPONSE → FRONTEND
{
  "new": [...],           // новые требования
  "deleted": [...],       // удаленные
  "modified": [...],      // измененные
  "duplicates": [...],    // дубли
  "contradicts": [...]    // противоречия
}
  ↓
[UI] Diff View
  • Показать все категории
  • Возможность подтвердить/отклонить каждую связь
```

---

## 🛠️ Технологический стек

### Backend

```yaml
Core:
  - Python: 3.11+
  - FastAPI: 0.110+
  - Uvicorn: async ASGI server

Database:
  - PostgreSQL: 15+
  - SQLAlchemy: 2.0+ (ORM)
  - Alembic: migrations
  - psycopg2-binary: PostgreSQL driver

Async & Performance:
  - httpx: async HTTP client (для DeepSeek)
  - asyncio: async/await
  - Redis: (optional) кэш + task queue

AI Integration:
  - Существующий DeepSeekClient
  - tiktoken: token counting
  - sentence-transformers: (optional) для similarity

File Processing:
  - pymupdf / pymupdf4llm: PDF processing
  - Pillow: image processing

Utilities:
  - pydantic: validation
  - python-dotenv: config
  - python-jose: JWT (если auth нужен)
  - passlib: password hashing
```

### Frontend

```yaml
Core:
  - Vue 3: reactive framework
  - Vite: build tool
  - TypeScript: (optional) type safety

UI Components:
  - Vuetify 3: Material Design components
  - OR Element Plus: (альтернатива)

PDF Viewing:
  - vue-pdf-embed: PDF viewer component
  - OR pdf.js: direct integration

State Management:
  - Pinia: state management

HTTP & WebSocket:
  - axios: HTTP client
  - native WebSocket API

Routing:
  - vue-router: SPA routing

Utilities:
  - date-fns: date formatting
  - lodash: utilities
```

### DevOps

```yaml
Containerization:
  - Docker: containers
  - Docker Compose: local development

Database:
  - PostgreSQL: official image
  - pgAdmin: (optional) DB management UI

Reverse Proxy:
  - Nginx: static + proxy

Monitoring (future):
  - Prometheus: metrics
  - Grafana: dashboards
```

---

## 📁 Структура проекта (финальная)

```
requirements-management-system/
│
├── backend/
│   ├── alembic/                      # DB migrations
│   │   ├── versions/
│   │   ├── env.py
│   │   └── alembic.ini
│   │
│   ├── src/
│   │   ├── database/
│   │   │   ├── __init__.py
│   │   │   ├── connection.py         # DB connection pool
│   │   │   ├── models.py             # SQLAlchemy ORM models
│   │   │   └── crud.py               # CRUD operations
│   │   │
│   │   ├── services/                 # Business logic
│   │   │   ├── __init__.py
│   │   │   ├── project_service.py
│   │   │   ├── document_service.py
│   │   │   ├── extraction_service.py
│   │   │   ├── diff_service.py
│   │   │   ├── review_service.py
│   │   │   └── metrics_service.py
│   │   │
│   │   ├── api/                      # API routes
│   │   │   ├── __init__.py
│   │   │   ├── deps.py               # Dependencies (DB session, auth)
│   │   │   ├── projects.py
│   │   │   ├── documents.py
│   │   │   ├── requirements.py
│   │   │   ├── diff.py
│   │   │   ├── review.py
│   │   │   └── websocket.py
│   │   │
│   │   ├── diff/                     # Diff engine
│   │   │   ├── __init__.py
│   │   │   ├── document_differ.py
│   │   │   └── requirement_matcher.py
│   │   │
│   │   ├── schemas/                  # Pydantic schemas
│   │   │   ├── __init__.py
│   │   │   ├── project.py
│   │   │   ├── document.py
│   │   │   ├── requirement.py
│   │   │   └── diff.py
│   │   │
│   │   ├── core/                     # Core utilities
│   │   │   ├── config.py             # Settings
│   │   │   ├── security.py           # Auth (если нужен)
│   │   │   └── logger.py
│   │   │
│   │   ├── extraction/               # Существующий код (рефакторинг)
│   │   │   ├── __init__.py
│   │   │   ├── pdf_processor.py      # + bbox extraction
│   │   │   ├── deepseek_client.py    # async version
│   │   │   ├── extractor.py
│   │   │   ├── models.py
│   │   │   └── usage_tracker.py
│   │   │
│   │   └── utils/
│   │       ├── file_storage.py       # File upload/download
│   │       └── hash.py               # File hashing
│   │
│   ├── tests/
│   │   ├── test_api/
│   │   ├── test_services/
│   │   └── test_diff/
│   │
│   ├── main.py                       # FastAPI app
│   ├── requirements.txt
│   ├── pyproject.toml
│   └── .env.example
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── projects/
│   │   │   │   ├── ProjectsList.vue
│   │   │   │   ├── ProjectCard.vue
│   │   │   │   └── CreateProjectDialog.vue
│   │   │   │
│   │   │   ├── documents/
│   │   │   │   ├── DocumentsList.vue
│   │   │   │   ├── DocumentUpload.vue
│   │   │   │   └── ProcessingStatus.vue
│   │   │   │
│   │   │   ├── requirements/
│   │   │   │   ├── RequirementsList.vue
│   │   │   │   ├── RequirementCard.vue
│   │   │   │   └── RequirementFilters.vue
│   │   │   │
│   │   │   ├── review/
│   │   │   │   ├── ReviewLayout.vue          # Split view
│   │   │   │   ├── PDFViewer.vue             # PDF с подсветкой
│   │   │   │   ├── RequirementReviewCard.vue # Карточка для review
│   │   │   │   └── ReviewActions.vue         # Accept/Reject/Edit
│   │   │   │
│   │   │   ├── diff/
│   │   │   │   ├── DiffView.vue
│   │   │   │   ├── DiffSummary.vue
│   │   │   │   ├── DiffRequirementPair.vue
│   │   │   │   └── ConflictResolver.vue
│   │   │   │
│   │   │   └── common/
│   │   │       ├── AppHeader.vue
│   │   │       ├── Sidebar.vue
│   │   │       └── LoadingSpinner.vue
│   │   │
│   │   ├── views/
│   │   │   ├── ProjectsView.vue
│   │   │   ├── ProjectDetailView.vue
│   │   │   ├── DocumentDetailView.vue
│   │   │   ├── RequirementsReviewView.vue
│   │   │   └── DiffView.vue
│   │   │
│   │   ├── stores/
│   │   │   ├── projects.js
│   │   │   ├── documents.js
│   │   │   ├── requirements.js
│   │   │   └── websocket.js
│   │   │
│   │   ├── services/
│   │   │   └── api.js                # Axios instance
│   │   │
│   │   ├── router/
│   │   │   └── index.js
│   │   │
│   │   ├── App.vue
│   │   └── main.js
│   │
│   ├── public/
│   ├── package.json
│   ├── vite.config.js
│   └── .env.example
│
├── data/
│   ├── uploads/                      # Загруженные PDF
│   ├── processed/                    # Обработанные (с bbox)
│   └── database/                     # SQLite (для dev)
│
├── docs/
│   ├── README.md
│   ├── ARCHITECTURE.md               # Этот файл
│   ├── ROADMAP.md
│   ├── DEMO_PLAN.md
│   ├── MIGRATION_GUIDE.md
│   ├── API.md                        # API documentation
│   └── DEPLOYMENT.md
│
├── docker/
│   ├── backend.Dockerfile
│   ├── frontend.Dockerfile
│   └── nginx.conf
│
├── docker-compose.yml
├── docker-compose.dev.yml
└── README.md
```

---

## 🔐 Безопасность (если нужна аутентификация)

### Authentication Flow (опционально)

```
USER → Login
  ↓
[API] POST /api/auth/login
{
  "username": "engineer@company.com",
  "password": "..."
}
  ↓
[SecurityService]
  • Проверить credentials
  • Создать JWT token
  ↓
RESPONSE
{
  "access_token": "eyJ...",
  "token_type": "bearer"
}
  ↓
FRONTEND → Сохранить token в localStorage
  ↓
Все последующие запросы:
Authorization: Bearer eyJ...
```

### Роли (если нужны)

```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    full_name VARCHAR(255),
    role VARCHAR(50) DEFAULT 'engineer',
    -- admin, engineer, viewer
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE user_project_access (
    user_id INTEGER REFERENCES users(id),
    project_id INTEGER REFERENCES projects(id),
    role VARCHAR(50),  -- owner, editor, viewer
    PRIMARY KEY (user_id, project_id)
);
```

---

## 📡 API Endpoints (полный список)

### Projects

```
GET    /api/projects                    # Список проектов
POST   /api/projects                    # Создать проект
GET    /api/projects/{id}               # Детали проекта
PUT    /api/projects/{id}               # Обновить проект
DELETE /api/projects/{id}               # Удалить проект
```

### Documents

```
GET    /api/projects/{pid}/documents    # Список документов проекта
POST   /api/projects/{pid}/documents    # Загрузить документ
GET    /api/documents/{id}              # Детали документа
DELETE /api/documents/{id}              # Удалить документ
POST   /api/documents/{id}/extract      # Запустить извлечение
GET    /api/documents/{id}/status       # Статус обработки
```

### Requirements

```
GET    /api/documents/{id}/requirements # Все требования документа
GET    /api/requirements/{id}           # Детали требования
PUT    /api/requirements/{id}           # Обновить требование
DELETE /api/requirements/{id}           # Удалить требование

# Фильтры
GET    /api/documents/{id}/requirements?status=pending
GET    /api/documents/{id}/requirements?type=technical
GET    /api/documents/{id}/requirements?page=15
```

### Review

```
POST   /api/requirements/{id}/accept    # Принять
POST   /api/requirements/{id}/reject    # Отклонить
POST   /api/requirements/{id}/edit      # Редактировать
GET    /api/requirements/{id}/audit     # История изменений
```

### Diff

```
POST   /api/diff                        # Сравнить две версии
GET    /api/diff/{id}                   # Результаты diff
POST   /api/relations/{id}/confirm      # Подтвердить связь
POST   /api/relations/{id}/reject       # Отклонить связь
```

### Metrics

```
GET    /api/documents/{id}/metrics      # Метрики покрытия
GET    /api/projects/{id}/metrics       # Агрегированные метрики проекта
```

### WebSocket

```
WS     /ws/logs                         # Real-time логи
WS     /ws/progress/{document_id}       # Прогресс обработки
```

---

## 🚀 Производительность и масштабирование

### Оптимизации

1. **Database:**
   - Правильные индексы (уже описаны)
   - Connection pooling (SQLAlchemy)
   - Read replicas (для больших нагрузок)

2. **API:**
   - Async endpoints где возможно
   - Pagination для списков
   - Кэширование через Redis (опционально)

3. **File Storage:**
   - Local для dev/MVP
   - S3 для production
   - CDN для static файлов

4. **Background Tasks:**
   - Celery + Redis для длительных задач (extraction)
   - Или FastAPI BackgroundTasks для простых случаев

### Масштабирование

```
┌─────────────────────────────────────────┐
│          Load Balancer (Nginx)          │
└─────────────────────────────────────────┘
                    ↓
    ┌───────────────┴───────────────┐
    ↓                               ↓
┌─────────┐                    ┌─────────┐
│ API #1  │                    │ API #2  │
└─────────┘                    └─────────┘
    ↓                               ↓
    └───────────────┬───────────────┘
                    ↓
         ┌──────────────────┐
         │   PostgreSQL     │
         │  (Master-Slave)  │
         └──────────────────┘
                    ↓
              ┌──────────┐
              │  Redis   │
              └──────────┘
```

---

## 📊 Мониторинг и логирование

### Метрики для отслеживания

1. **Производительность:**
   - Время обработки документа
   - Время извлечения одного требования
   - API response time

2. **Использование:**
   - Количество проектов/документов
   - Количество извлеченных требований
   - Частота review действий

3. **AI:**
   - DeepSeek API usage (tokens, cost)
   - Качество извлечения (% accepted vs rejected)
   - Confidence scores distribution

4. **Система:**
   - DB connection pool usage
   - Memory usage
   - Disk usage

### Логирование

```python
# Структурированные логи
{
    "timestamp": "2026-02-18T10:30:00Z",
    "level": "INFO",
    "service": "extraction_service",
    "action": "extract_requirements",
    "document_id": 123,
    "duration_ms": 45000,
    "requirements_count": 87,
    "ai_cost_usd": 0.42
}
```

---

## 🔮 Будущие улучшения

1. **Machine Learning:**
   - Fine-tune модель на размеченных данных
   - Active learning (учиться на правках инженеров)

2. **Интеграции:**
   - Jira / YouTrack
   - Confluence
   - Git (version control)

3. **Advanced Features:**
   - Граф зависимостей требований
   - Impact analysis (что затронет изменение)
   - Traceability matrix

4. **Collaboration:**
   - Comments на требованиях
   - @mentions
   - Real-time collaborative review

---

<div align="center">

**Архитектура готова к реализации! 🏗️**

*Масштабируемая • Поддерживаемая • Production-ready*

</div>
