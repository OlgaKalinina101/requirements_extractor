# Demo Plan - Прототип системы управления требованиями
**Срок: 1 неделя (7 дней)**

---

## 🎯 Цель демо

Создать **работающий прототип** системы управления требованиями, который можно показать стейкхолдерам и использовать для валидации концепции.

**Демо должно показать:**
1. Загрузку PDF документа
2. Автоматическое извлечение требований через AI
3. UI для review требований (accept/reject/edit)
4. Привязку к странице документа
5. Аудит изменений (AI → Human)
6. Метрики покрытия

**НЕ входит в демо (на 2-й этап):**
- ❌ Diff между версиями документов
- ❌ Аутентификация и роли
- ❌ Production deployment

---

## 📊 Scope демо

### ✅ Что будет работать

```
┌─────────────────────────────────────────────┐
│  FRONTEND (упрощенный Vue UI)              │
├─────────────────────────────────────────────┤
│  1. One Project (hardcoded)                │
│  2. Document Upload                         │
│  3. Requirements Review (split view)       │
│     ├─ PDF viewer (simple)                 │
│     └─ Requirements list                   │
│  4. Accept/Reject/Edit actions             │
│  5. Coverage metrics (basic)               │
└─────────────────────────────────────────────┘
                      ↕
┌─────────────────────────────────────────────┐
│  BACKEND (FastAPI + PostgreSQL)            │
├─────────────────────────────────────────────┤
│  • Document upload & storage               │
│  • Extraction через DeepSeek               │
│  • PostgreSQL для хранения                 │
│  • Review API (accept/reject/edit)         │
│  • Basic metrics                            │
└─────────────────────────────────────────────┘
```

### 🎨 UI Mockup (что покажем)

#### 1. Document Upload
```
┌─────────────────────────────────────┐
│  📁 Проект: Система складского учета│
├─────────────────────────────────────┤
│                                      │
│  📤 Загрузить документ ТЗ           │
│                                      │
│  [Выберите файл] или перетащите     │
│                                      │
│  ┌────────────────────────┐         │
│  │  Техническое задание   │         │
│  │  📄 TZ_v1.pdf          │         │
│  │  225 страниц           │         │
│  │  [Загрузить]           │         │
│  └────────────────────────┘         │
└─────────────────────────────────────┘
```

#### 2. Processing Status
```
┌─────────────────────────────────────┐
│  🔄 Обработка документа...          │
├─────────────────────────────────────┤
│  [████████████░░░░░░░] 65%         │
│                                      │
│  ✓ Извлечение текста: 225/225      │
│  ⏳ Анализ требований: 15/25       │
│                                      │
│  Найдено требований: 87             │
│  Обработано страниц: 145/225        │
│                                      │
│  Примерное время: ~2 минуты         │
└─────────────────────────────────────┘
```

#### 3. Requirements Review (главный экран)
```
┌───────────────────────┬─────────────────────────────┐
│  PDF Viewer           │  Requirements Review        │
│  (страница 15)        │                             │
├───────────────────────┤  📊 Прогресс: 45/87 (52%) │
│                       │                             │
│  [PDF Page]           │  🔍 Фильтры:               │
│                       │  [ ] Pending                │
│  Highlighted text:    │  [✓] Accepted              │
│  "Система должна      │  [ ] Modified              │
│   поддерживать 100    │                             │
│   одновременных       │  ┌─────────────────────────┤
│   пользователей..."   │  │ REQ-1-015               │
│                       │  │ Статус: ⏳ Pending      │
│  [← Prev] [Next →]    │  ├─────────────────────────│
│                       │  │ 💬 AI предложил:        │
│                       │  │ "Система должна поддер- │
│                       │  │  живать 100 одновремен- │
│                       │  │  ных пользователей"     │
│                       │  │                         │
│                       │  │ 📍 Страница: 15         │
│                       │  │ 🏷️ Тип: Technical      │
│                       │  │ ⚡ Приоритет: Mandatory │
│                       │  ├─────────────────────────│
│                       │  │ [✓ Принять]             │
│                       │  │ [✗ Отклонить]           │
│                       │  │ [✏️ Редактировать]      │
│                       │  └─────────────────────────┤
│                       │                             │
│                       │  REQ-1-016                  │
│                       │  ...                        │
└───────────────────────┴─────────────────────────────┘
```

#### 4. Edit Modal
```
┌─────────────────────────────────────────────┐
│  ✏️ Редактировать требование REQ-1-015     │
├─────────────────────────────────────────────┤
│  AI предложил:                              │
│  ┌─────────────────────────────────────────┤
│  │ Система должна поддерживать 100         │
│  │ одновременных пользователей             │
│  └─────────────────────────────────────────┤
│                                              │
│  Ваша версия:                               │
│  ┌─────────────────────────────────────────┤
│  │ Система должна поддерживать минимум     │
│  │ 150 одновременных пользователей без     │
│  │ деградации производительности           │
│  └─────────────────────────────────────────┤
│                                              │
│  Причина изменения (опционально):          │
│  ┌─────────────────────────────────────────┤
│  │ Уточнение: добавлено "минимум" и       │
│  │ условие производительности              │
│  └─────────────────────────────────────────┤
│                                              │
│  [Отмена]                    [Сохранить]   │
└─────────────────────────────────────────────┘
```

#### 5. Coverage Metrics
```
┌─────────────────────────────────────┐
│  📊 Метрики покрытия документа      │
├─────────────────────────────────────┤
│  Всего страниц: 225                 │
│  Обработано: 218 (97%)              │
│  Пропущено: 7                       │
│                                      │
│  [████████████████████░] 97%       │
│                                      │
│  Пропущенные страницы:              │
│  • Страница 1 (титульная)           │
│  • Страница 2 (содержание)          │
│  • Страницы 220-225 (приложения)    │
│                                      │
│  Извлечено требований: 87           │
│  ├─ Technical: 34                   │
│  ├─ Functional: 28                  │
│  ├─ Organizational: 15              │
│  └─ Other: 10                       │
│                                      │
│  Статус review:                     │
│  ├─ Accepted: 45 (52%)              │
│  ├─ Modified: 12 (14%)              │
│  ├─ Rejected: 8 (9%)                │
│  └─ Pending: 22 (25%)               │
└─────────────────────────────────────┘
```

---

## 🗓️ План работы (7 дней)

### День 1: Настройка инфраструктуры

**Backend:**
- [x] Настроить PostgreSQL
- [x] SQLAlchemy models (projects, documents, requirements)
- [x] Alembic migrations
- [x] Basic CRUD операции

**Задачи:**
```bash
# 1. Создать docker-compose.yml с PostgreSQL
# 2. Создать src/database/models.py
# 3. Создать src/database/crud.py
# 4. Инициализировать Alembic
# 5. Создать первую миграцию
```

**Результат:** БД готова, можно создавать записи

---

### День 2: Backend API (основа)

**API Endpoints:**
- `POST /api/upload` - загрузка PDF
- `POST /api/extract/{document_id}` - запуск извлечения
- `GET /api/documents/{id}` - получить документ
- `GET /api/documents/{id}/requirements` - все требования

**Задачи:**
```bash
# 1. Рефакторинг ExtractionService
# 2. Интеграция с БД
# 3. API endpoints
# 4. Тестирование через Postman/curl
```

**Результат:** Можно загрузить PDF и получить требования в БД

---

### День 3: Review API + Аудит

**API Endpoints:**
- `POST /api/requirements/{id}/accept`
- `POST /api/requirements/{id}/reject`
- `POST /api/requirements/{id}/edit`
- `GET /api/requirements/{id}` - с историей изменений

**Задачи:**
```bash
# 1. ReviewService
# 2. Аудит: ai_suggested, human_edited
# 3. Обновление статусов
# 4. Тестирование
```

**Результат:** Можно accept/reject/edit через API

---

### День 4: Frontend - основа (Vue)

**Setup:**
- Vue 3 + Vite
- Vuetify (UI components)
- Vue Router
- Pinia (state)
- Axios

**Компоненты:**
- `DocumentUpload.vue`
- `ProcessingStatus.vue`
- `RequirementsList.vue`

**Задачи:**
```bash
# 1. npm create vite@latest frontend -- --template vue
# 2. Установить Vuetify
# 3. Создать layout
# 4. Компонент загрузки
# 5. Интеграция с API
```

**Результат:** Можно загрузить PDF через UI

---

### День 5: Requirements Review UI

**Компоненты:**
- `ReviewLayout.vue` (split view)
- `PDFViewer.vue` (простой, через iframe или PDF.js)
- `RequirementReviewCard.vue`
- `ReviewActions.vue`

**Задачи:**
```bash
# 1. Split layout (PDF + Requirements)
# 2. Простой PDF viewer
# 3. Карточки требований
# 4. Accept/Reject/Edit actions
# 5. Обновление UI после действий
```

**Результат:** Полноценный review workflow

---

### День 6: Metrics + Polish

**Backend:**
- Coverage metrics calculation
- `GET /api/documents/{id}/metrics`

**Frontend:**
- `MetricsView.vue`
- Фильтры в RequirementsList
- Статистика

**Задачи:**
```bash
# 1. MetricsService
# 2. Coverage calculation
# 3. UI для метрик
# 4. Фильтры (status, type, priority)
# 5. Поиск по требованиям
```

**Результат:** Видно покрытие и статистику

---

### День 7: Тестирование + Демо подготовка

**Задачи:**
- Сквозное тестирование workflow
- Исправление багов
- UI polish
- Подготовка демо данных
- Документация

**Демо сценарий:**
1. Загрузить реальное ТЗ (225 стр)
2. Дождаться обработки (~3 мин)
3. Показать review UI
4. Accept несколько требований
5. Edit одно требование
6. Показать метрики покрытия
7. Показать аудит (AI vs Human)

**Результат:** Готовое демо!

---

## 🛠️ Технические детали

### Database Schema (минимальный)

```sql
-- Для демо упрощаем: один проект (hardcoded)
CREATE TABLE documents (
    id SERIAL PRIMARY KEY,
    filename VARCHAR(255) NOT NULL,
    file_path TEXT NOT NULL,
    status VARCHAR(50) DEFAULT 'pending',
    total_pages INTEGER,
    uploaded_at TIMESTAMP DEFAULT NOW(),
    processed_at TIMESTAMP
);

CREATE TABLE sections (
    id SERIAL PRIMARY KEY,
    document_id INTEGER REFERENCES documents(id) ON DELETE CASCADE,
    section_number VARCHAR(50),
    title TEXT,
    page_start INTEGER,
    page_end INTEGER
);

CREATE TABLE requirements (
    id SERIAL PRIMARY KEY,
    document_id INTEGER REFERENCES documents(id) ON DELETE CASCADE,
    section_id INTEGER REFERENCES sections(id),
    requirement_id VARCHAR(50) NOT NULL,
    text TEXT NOT NULL,
    type VARCHAR(50),
    priority VARCHAR(50),
    page_number INTEGER,
    bbox JSONB,
    
    status VARCHAR(50) DEFAULT 'pending',
    ai_suggested TEXT NOT NULL,
    human_edited TEXT,
    edit_reason TEXT,
    edited_by VARCHAR(255),
    edited_at TIMESTAMP,
    
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE coverage_metrics (
    id SERIAL PRIMARY KEY,
    document_id INTEGER REFERENCES documents(id) ON DELETE CASCADE,
    total_pages INTEGER,
    processed_pages INTEGER,
    skipped_pages INTEGER[],
    coverage_percent FLOAT,
    requirements_count INTEGER,
    requirements_by_type JSONB,
    calculated_at TIMESTAMP DEFAULT NOW()
);
```

### API Endpoints (минимальные)

```python
# api/documents.py
@router.post("/upload")
async def upload_document(file: UploadFile):
    """Загрузить PDF документ."""
    pass

@router.post("/{document_id}/extract")
async def extract_requirements(document_id: int):
    """Запустить извлечение требований."""
    pass

@router.get("/{document_id}")
async def get_document(document_id: int):
    """Получить документ с метаданными."""
    pass

@router.get("/{document_id}/requirements")
async def get_requirements(
    document_id: int,
    status: Optional[str] = None,
    type: Optional[str] = None
):
    """Получить требования документа с фильтрами."""
    pass

@router.get("/{document_id}/metrics")
async def get_metrics(document_id: int):
    """Получить метрики покрытия."""
    pass

# api/requirements.py
@router.get("/{requirement_id}")
async def get_requirement(requirement_id: int):
    """Получить требование."""
    pass

@router.post("/{requirement_id}/accept")
async def accept_requirement(requirement_id: int):
    """Принять требование как есть."""
    pass

@router.post("/{requirement_id}/reject")
async def reject_requirement(requirement_id: int, reason: Optional[str] = None):
    """Отклонить требование."""
    pass

@router.post("/{requirement_id}/edit")
async def edit_requirement(
    requirement_id: int,
    edited_text: str,
    reason: Optional[str] = None
):
    """Редактировать требование."""
    pass
```

### Frontend Structure (минимальная)

```
frontend/
├── src/
│   ├── components/
│   │   ├── DocumentUpload.vue       # День 4
│   │   ├── ProcessingStatus.vue     # День 4
│   │   ├── ReviewLayout.vue         # День 5
│   │   ├── PDFViewer.vue            # День 5
│   │   ├── RequirementsList.vue     # День 5
│   │   ├── RequirementCard.vue      # День 5
│   │   ├── EditDialog.vue           # День 5
│   │   └── MetricsPanel.vue         # День 6
│   │
│   ├── views/
│   │   ├── HomeView.vue             # Upload + список документов
│   │   └── ReviewView.vue           # Review UI
│   │
│   ├── stores/
│   │   ├── documents.js             # Document state
│   │   └── requirements.js          # Requirements state
│   │
│   ├── services/
│   │   └── api.js                   # Axios wrapper
│   │
│   └── App.vue
```

---

## 📦 Deliverables (что отдаем через неделю)

### 1. Рабочий прототип

**Backend:**
- ✅ FastAPI app с PostgreSQL
- ✅ Upload + Extract + Review API
- ✅ Интеграция с DeepSeek
- ✅ Аудит изменений

**Frontend:**
- ✅ Vue 3 SPA
- ✅ Document upload
- ✅ Requirements review UI
- ✅ Metrics dashboard

**Docker:**
- ✅ `docker-compose.yml` для быстрого запуска
- ✅ PostgreSQL в контейнере
- ✅ Backend + Frontend в контейнерах

### 2. Документация

- ✅ README с инструкциями по запуску
- ✅ API documentation (автоматическая FastAPI docs)
- ✅ Демо сценарий

### 3. Демо-данные

- ✅ Пример ТЗ (можно использовать предоставленный клиентом)
- ✅ Уже обработанный документ для быстрой демонстрации

---

## 🎬 Демо-сценарий (что показываем)

### Сценарий 1: Загрузка и обработка (5 минут)

```
1. Открываем UI: http://localhost:3000
2. "Вот наша главная страница"
3. Нажимаем "Загрузить документ"
4. Выбираем ТЗ (225 страниц)
5. "Система загружает файл и начинает обработку"
6. Показываем real-time прогресс:
   - Извлечение страниц: 1/225, 50/225, 225/225
   - Анализ требований: 5/25, 15/25, 25/25
7. "Через ~3 минуты обработка завершена"
8. "Найдено 87 требований"
```

### Сценарий 2: Review workflow (10 минут)

```
1. Открываем документ
2. "Вот наш основной интерфейс для review"
3. Split view:
   - Слева: PDF с подсветкой
   - Справа: список требований
4. "Выбираем первое требование"
5. "AI предложил такой текст"
6. "Мы видим номер страницы и тип требования"
7. Показываем три действия:
   
   A. Accept:
   "Если всё правильно - просто принимаем"
   Нажимаем "✓ Принять"
   "Статус меняется на Accepted, переходим к следующему"
   
   B. Reject:
   "Если AI ошибся и это не требование"
   Нажимаем "✗ Отклонить"
   "Можем указать причину"
   
   C. Edit:
   "Если требование правильное, но нужно уточнить"
   Нажимаем "✏️ Редактировать"
   "Редактируем текст"
   "Указываем причину изменения"
   "Сохраняем"
   
8. "Система сохраняет и AI версию, и нашу"
9. "Это нужно для аудита и обучения модели"
```

### Сценарий 3: Метрики и аудит (5 минут)

```
1. Открываем панель метрик
2. "Вот что мы видим:"
   - Покрытие: 97% (218 из 225 страниц)
   - Пропущено: 7 страниц (титульная, содержание, приложения)
   - Всего требований: 87
   - По типам: Technical 34, Functional 28, ...
   - По статусу: Accepted 45, Modified 12, ...
3. "Кликаем на пропущенные страницы"
4. "Можем посмотреть, что там было"
5. Открываем одно измененное требование
6. "Вот что предложил AI"
7. "А вот что изменил инженер"
8. "И причина изменения"
```

---

## 💰 Оценка трудозатрат

### Разработка (7 дней)

| Компонент | Часов | Описание |
|-----------|-------|----------|
| **Database** | 8 | Schema, migrations, CRUD |
| **Backend API** | 16 | Upload, extract, review endpoints |
| **Integration** | 8 | Extractor → Database |
| **Frontend Setup** | 6 | Vue, Vuetify, routing |
| **Upload UI** | 4 | Document upload component |
| **Review UI** | 12 | Split view, PDF, requirements |
| **Metrics** | 6 | Coverage calculation + UI |
| **Testing** | 8 | End-to-end testing |
| **Polish** | 4 | Bug fixes, UX improvements |
| **Documentation** | 4 | README, API docs, demo script |

**Итого:** 76 часов ≈ 10 рабочих дней (при 8 ч/день)

**При интенсивной работе:** 7 дней реально (10-12 ч/день)

### После демо (для обсуждения)

**Что можно добавить на 2-й этап:**
- Diff между версиями (+2 недели)
- Улучшение AI промптов (+1 неделя)
- Production deployment (+1 неделя)
- Аутентификация и роли (+1 неделя)
- Advanced UI features (+2 недели)

---

## 🚀 Как запустить демо

### Quick Start

```bash
# 1. Клонировать репо
git clone <repo>
cd requirements-management-system

# 2. Запустить через Docker Compose
docker-compose up -d

# 3. Открыть UI
http://localhost:3000

# 4. API docs
http://localhost:8000/docs
```

### Manual Start (для разработки)

```bash
# Backend
cd backend
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
alembic upgrade head
uvicorn main:app --reload

# Frontend
cd frontend
npm install
npm run dev
```

---

## ✅ Definition of Done

**Демо считается готовым, когда:**

1. ✅ Можно загрузить PDF через UI
2. ✅ Система извлекает требования и сохраняет в БД
3. ✅ UI показывает прогресс в реальном времени
4. ✅ Можно открыть review интерфейс
5. ✅ Можно accept/reject/edit требования
6. ✅ Видны метрики покрытия
7. ✅ Аудит работает (AI vs Human)
8. ✅ Всё запускается через `docker-compose up`
9. ✅ Есть README с инструкциями
10. ✅ Подготовлен демо-сценарий

---

<div align="center">

**План демо готов к исполнению! 🎯**

*7 дней → Working Prototype → Validation → Next Steps*

</div>
