# PDF Processing — Visual Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        1. UPLOAD & VALIDATION                           │
│                                                                         │
│  POST /api/extract (multipart: file, model, generate_word, project_id) │
│  └─ Validation: file.endswith('.pdf')                                   │
│  └─ Save to: data/uploads/{timestamp}_{filename}.pdf                   │
│  └─ Create Document record in DB (status: "pending")                   │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                     2. PDF EXTRACTION (PARALLEL)                        │
│                                                                         │
│  ThreadPoolExecutor — все страницы параллельно                         │
│                                                                         │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐       ┌──────────┐         │
│  │ Thread 1 │  │ Thread 2 │  │ Thread 3 │  ...  │ Thread N │         │
│  │  Page 1  │  │  Page 2  │  │  Page 3  │       │  Page N  │         │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘       └────┬─────┘         │
│       │             │             │                    │                │
│       ▼             ▼             ▼                    ▼                │
│  pymupdf4llm → markdown text + PNG/JPG images                          │
│       │                                                                 │
│       ▼                                                                 │
│  pages = [                                                             │
│    {"page_number": 1, "text": "..."},                                  │
│    {"page_number": 2, "text": "..."},                                  │
│    ...                                                                  │
│  ]                                                                     │
│                                                                         │
│  page_image_metadata = {                                               │
│    5:  [{"path": ".../page_5_image_0.png", ...}],                     │
│    10: [{"path": ".../page_10_image_0.png", ...},                     │
│         {"path": ".../page_10_image_1.png", ...}]                     │
│  }                                                                     │
│                                                                         │
│  Images: output_dir/images/page_{N}_image_{I}.{ext}                   │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│              3. AI EXTRACTION (PAGE BATCHES, batch_size=7)              │
│                                                                         │
│  Батч 1: страницы 1-7 (asyncio.gather)                                │
│  ┌────────────────────────────────────────────────────────────────┐   │
│  │ Page 1  Page 2  Page 3  Page 4  Page 5  Page 6  Page 7        │   │
│  │   │       │       │       │       │       │       │            │   │
│  │   ▼       ▼       ▼       ▼       ▼       ▼       ▼            │   │
│  │ run_in_executor (thread pool) — синхронный HTTP-запрос         │   │
│  │   │                                                             │   │
│  │   ├─ TEXT: OpenRouter.extract_requirements(page_text)          │   │
│  │   │         → [Requirement, Requirement, ...]                  │   │
│  │   │                                                             │   │
│  │   └─ IMAGES (если есть): OpenRouter.extract_requirements_from_image()│
│  │         image encoded to Base64 → multimodal API request       │   │
│  │         → [Requirement, Requirement, ...]                      │   │
│  └────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  Батч 2: страницы 8-14 ... (аналогично)                               │
│  ...                                                                    │
│  Батч N: последние страницы                                            │
│                                                                         │
│  Прогресс WebSocket: completed_pages / total_pages → 30%–88%          │
│                                                                         │
│  Retry-логика (до 3 попыток, backoff 2^n секунд):                     │
│  ├─ Attempt 1 → parse JSON                                             │
│  ├─ Attempt 2 (delay 1s) → если JSON parse error                      │
│  └─ Attempt 3 (delay 2s) → если снова ошибка → return []              │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                      4. SAVE TO DATABASE                                │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐  │
│  │ sections (1 row)                                                │  │
│  │   section_number="1", title="All Pages"                        │  │
│  │   page_start=1, page_end=N                                     │  │
│  └─────────────────────────────────────────────────────────────────┘  │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐  │
│  │ requirements (bulk INSERT, один SQL-запрос)                     │  │
│  │   requirement_id, text, type, priority                         │  │
│  │   page_number, source_page, source_type ("text"/"image")       │  │
│  │   status="pending", ai_suggested=text                          │  │
│  └─────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                      5. COVERAGE METRICS                                │
│                                                                         │
│  pages_with_reqs = {r.source_page for r in requirements}               │
│  skipped_pages = all_pages - pages_with_reqs                           │
│  coverage_percent = len(pages_with_reqs) / total_pages * 100           │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐  │
│  │ coverage_metrics (1 row)                                        │  │
│  │   total_pages: N                                               │  │
│  │   processed_pages: M  (страницы с требованиями)                │  │
│  │   skipped_pages: [1,2,3,...]                                   │  │
│  │   coverage_percent: M/N * 100                                  │  │
│  │   requirements_by_type: {"technical": 15, "functional": 8, ...}│  │
│  └─────────────────────────────────────────────────────────────────┘  │
│                                                                         │
│  Document.status → "completed"                                         │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                     6. GENERATE REPORTS (опционально)                   │
│                                                                         │
│  ├─ JSON registry: output_dir/registry.json                           │
│  └─ Word document: output_dir/requirements_report.docx                │
│                                                                         │
│  Временный каталог удаляется после возврата ответа                    │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         7. RESPONSE                                     │
│                                                                         │
│  ExtractionResult:                                                     │
│  {                                                                     │
│    "success": true,                                                    │
│    "requirements_count": 87,                                           │
│    "sections_count": 1,                                                │
│    "total_tokens": 45000,                                              │
│    "total_cost": 0.23,                                                 │
│    "processing_time": 245.3,                                           │
│    "model_used": "claude-sonnet-4.5",                                  │
│    "document_id": 42,                                                  │
│    "files": {"registry": "...", "word_document": "..."}                │
│  }                                                                     │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Пример обработки одной страницы

```
Page 10: "Насосы должны обеспечивать..."
    │
    ├─ TEXT EXTRACTION
    │  └─ Отправить в AI: текст страницы 10
    │  └─ AI возвращает:
    │       [
    │         {id: "REQ-10-001", text: "Насосы должны...", type: "technical", priority: "mandatory"},
    │         {id: "REQ-10-002", text: "Давление не менее...", type: "technical", priority: "mandatory"}
    │       ]
    │
    └─ IMAGE EXTRACTION (page 10 имеет 2 изображения)
       │
       ├─ page_10_image_0.png (технический чертёж)
       │   ├─ Encode to Base64
       │   ├─ Multimodal request → AI
       │   └─ AI возвращает:
       │        [{id: "REQ-10-IMG-001", text: "Максимальный диаметр...", ...}]
       │
       └─ page_10_image_1.png (таблица спецификаций)
           ├─ Encode to Base64
           ├─ Multimodal request → AI
           └─ AI возвращает:
                [{id: "REQ-10-IMG-002", text: "Вес не более...", ...},
                 {id: "REQ-10-IMG-003", text: "Габариты...", ...}]

Page 10 итого: 5 требований (2 текст + 3 изображения)
```

---

## Метрики покрытия — визуализация

```
Документ: 25 страниц

Страницы с требованиями (обработанные):
  7, 8, 9, 10, 11, 12, 15, 16, 17, 18, 20, 21 = 12 страниц

Страницы без требований (пропущенные):
  1, 2, 3, 4, 5, 6     — титул, оглавление
  13, 14                — пустые/разделители
  19                    — только схема (изображение без текста)
  22, 23, 24, 25        — приложения, литература
  = 13 страниц

Coverage: 12 / 25 * 100 = 48%
```
