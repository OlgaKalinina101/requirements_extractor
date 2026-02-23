# 📚 Documentation Index

Полная документация проекта Requirements Extractor.

## 📖 Основная документация

### Быстрый старт
- **[README.md](README.md)** - Основная документация проекта
- **[INSTALL.md](INSTALL.md)** - Инструкции по установке
- **[QUICK_TEST.md](QUICK_TEST.md)** - Быстрый тест UI

### Архитектура
- **[ARCHITECTURE.md](ARCHITECTURE.md)** - Архитектура системы
- **[ROADMAP.md](ROADMAP.md)** - План развития

---

## 🔍 PDF Processing Pipeline

**Главный документ:** [PDF_PROCESSING_PIPELINE.md](PDF_PROCESSING_PIPELINE.md)

Полное описание того, как система обрабатывает PDF документы:

1. **Куда извлекаются изображения**
   - Путь: `data/output/{timestamp}/images/`
   - Формат: `page_{N}_image_{I}.png`
   - Процесс: параллельная обработка всех страниц

2. **Как изображения передаются к AI**
   - По одному изображению за запрос
   - Кодируются в Base64
   - Multimodal message (текст + изображение)

3. **Как обрабатываются страницы**
   - ПО СЕКЦИЯМ (не по страницам!)
   - Текст секции → 1 запрос к AI
   - Изображения секции → N запросов к AI

4. **Как считаются обработанные страницы**
   - Страница с ≥1 требованием = обработанная
   - Остальные = пропущенные (это нормально!)

### Дополнительные материалы:
- **[PDF_PROCESSING_DIAGRAM.md](PDF_PROCESSING_DIAGRAM.md)** - Визуальные диаграммы процесса
- **[PIPELINE_QUICK_REFERENCE.md](PIPELINE_QUICK_REFERENCE.md)** - Краткая шпаргалка

---

## 🎨 UI & Frontend

### Основные компоненты:
1. **DocumentUpload** - Загрузка PDF
2. **DocumentsList** - Список документов
3. **ReviewView** - Основной экран review
4. **PDFViewer** - Просмотр PDF (PDF.js)
5. **RequirementsList** - Список требований
6. **RequirementCard** - Карточка требования
7. **MetricsPanel** - Панель метрик

### Возможности:
- ✅ PDF viewer с PDF.js (работает везде)
- ✅ Zoom 50%-300%
- ✅ Навигация по требованиям → PDF
- ✅ Клик по карточке → переход к странице
- ✅ Независимый скролл списка требований
- ✅ Цветовая индикация покрытия

---

## 🗄️ База данных

### Таблицы:
1. **documents** - Метаданные документов
2. **sections** - Секции документа
3. **requirements** - Извлеченные требования
4. **coverage_metrics** - Метрики покрытия

### Скрипты:
- **[recalculate_metrics.py](recalculate_metrics.py)** - Пересчет метрик для существующих документов
- **[create_tables.sql](create_tables.sql)** - SQL схема
- **[init_db_docker.py](init_db_docker.py)** - Инициализация БД в Docker

---

## 🚀 Deployment

### Docker:
- **[docker-compose.yml](docker-compose.yml)** - Docker Compose конфигурация
- **[Dockerfile](Dockerfile)** - Образ приложения

### Настройка:
- **[.env.example](.env.example)** - Пример переменных окружения
- **[requirements.txt](requirements.txt)** - Python зависимости
- **[frontend-vue/package.json](frontend-vue/package.json)** - Node.js зависимости

---

## 📊 Метрики и статистика

### Coverage Metrics (Исправлено!)

**Проблема:** Показывалось 100% покрытие (225/225 страниц), хотя обработано ~23 страницы.

**Решение:** Правильный подсчет - только страницы с требованиями.

**Результат:**
```
Было:  225/225 (100%)
Стало: 23/225 (10.2%)
```

**Документация:**
- Алгоритм подсчета: `api_server.py:872-893`
- Скрипт пересчета: `recalculate_metrics.py`
- Цветовая индикация: `MetricsPanel.vue`

### Цветовая индикация покрытия:
- 🟢 **90%+** - Отличное покрытие (зеленый)
- 🔵 **70-90%** - Хорошее покрытие (синий)
- 🟠 **50-70%** - Среднее покрытие (оранжевый)
- 🔴 **<50%** - Низкое покрытие (красный)

---

## 🤖 AI Models

### Поддерживаемые модели:

| Model | Provider | Context | Best for |
|-------|----------|---------|----------|
| claude-sonnet-4.5 | Anthropic | 200K | ✅ Основная (рекомендуется) |
| claude-opus-4.6 | Anthropic | 200K | Сложные документы |
| gpt-4.1 | OpenAI | 128K | Альтернатива Claude |
| qwen-3.5-plus | Alibaba | 128K | Бюджетный вариант |
| gemini-3.1-pro | Google | 2M | Очень длинные документы |

### Конфигурация:
- **[src/openrouter_client.py](src/openrouter_client.py)** - OpenRouter клиент
- **[src/prompts.yaml](src/prompts.yaml)** - Промпты для AI

---

## 📁 Структура проекта

```
test2/
├── api_server.py              # FastAPI backend
├── src/
│   ├── openrouter_client.py   # AI client (OpenRouter)
│   ├── pdf_processor.py       # PDF extraction (pymupdf4llm)
│   ├── requirements_extractor.py  # Main extractor orchestrator
│   ├── prompts.yaml           # AI prompts
│   ├── models.py              # Data models
│   ├── config.py              # Configuration
│   └── database/
│       ├── models.py          # SQLAlchemy models
│       ├── crud.py            # Database operations
│       └── database.py        # DB connection
├── frontend-vue/              # Vue 3 frontend
│   ├── src/
│   │   ├── views/             # Pages
│   │   ├── components/        # UI components
│   │   ├── stores/            # Pinia stores
│   │   └── services/          # API client
│   └── vite.config.js         # Vite configuration
├── data/
│   ├── uploads/               # Uploaded PDFs
│   └── output/                # Extraction results
│       └── {timestamp}/
│           ├── images/        # Extracted images
│           ├── registry.json  # Requirements registry
│           └── result.docx    # Word report
├── docker-compose.yml         # Docker services
└── requirements.txt           # Python dependencies
```

---

## 🛠️ Полезные команды

### Запуск проекта:
```bash
# Backend
python api_server.py

# Frontend
cd frontend-vue
npm run dev

# Docker (full stack)
docker-compose up
```

### База данных:
```bash
# Пересчитать метрики
python recalculate_metrics.py

# Проверить подключение
python check_db.py

# Инициализировать схему
python init_db_docker.py
```

### Разработка:
```bash
# Установить зависимости
pip install -r requirements.txt
cd frontend-vue && npm install

# Линтинг
cd frontend-vue && npm run lint

# Тесты
pytest
```

---

## 📝 Миграции и история изменений

### Последние изменения:

**2026-02-22:**
- ✅ Исправлены метрики покрытия (правильный подсчет страниц)
- ✅ PDF Viewer с PDF.js (замена iframe)
- ✅ Навигация по требованиям → PDF
- ✅ Независимый скролл списка требований
- ✅ Axios через Vite proxy (исправлено подключение)

**2026-02-21:**
- ✅ PostgreSQL интеграция
- ✅ Alembic миграции
- ✅ ENUM → VARCHAR для type/priority
- ✅ Frontend Review UI (Vue 3)

**2026-02-20:**
- ✅ OpenRouter AI client
- ✅ Multimodal image processing
- ✅ WebSocket progress tracking
- ✅ Docker Compose setup

---

## 🐛 Troubleshooting

### PDF не отображается:
1. Проверьте Network tab в DevTools
2. Убедитесь что API сервер запущен
3. Проверьте Vite proxy: `vite.config.js`
4. Проверьте Content-Disposition header

### Метрики показывают 100%:
```bash
python recalculate_metrics.py
```

### База данных не подключается:
1. Проверьте Docker: `docker ps`
2. Проверьте порт: `5433` (не `5432`)
3. Проверьте `.env`: `DATABASE_URL`

### AI не извлекает требования:
1. Проверьте API ключ: `OPENROUTER_API_KEY`
2. Проверьте модель: `available_models`
3. Проверьте логи: `api_server.py` console

---

## 📧 Поддержка

Если у вас есть вопросы или проблемы:
1. Проверьте эту документацию
2. Посмотрите логи backend/frontend
3. Проверьте Network tab в DevTools
4. Изучите код в `src/` и `frontend-vue/src/`

---

## 🎯 Roadmap

См. **[ROADMAP.md](ROADMAP.md)** для полного плана развития.

**Next steps:**
- [ ] Batch обработка изображений
- [ ] Redis кэш для AI ответов
- [ ] Celery для фоновых задач
- [ ] Export в различные форматы
- [ ] API документация (Swagger)
- [ ] Unit tests coverage >80%
