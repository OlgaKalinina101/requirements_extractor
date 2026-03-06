# PDF Processing Pipeline

Описание полного пайплайна обработки PDF-документа — от загрузки до сохранения требований в БД.

---

## Обзор

Система использует **постраничный подход** (page-by-page): каждая страница обрабатывается независимо батчами по 7 страниц. Это заменило ранее использовавшийся TOC-based подход.

```
PDF Upload
    │
    ▼
[1] Сохранение файла + запись в БД
    │
    ▼
[2] Извлечение страниц PDF (ThreadPoolExecutor)
    │  pages[]                page_image_metadata{}
    ▼
[3] AI-обработка страниц батчами
    │  batch_size=7, asyncio.gather
    │  Для каждой страницы: текст + изображения
    ▼
[4] Сохранение в БД
    │  Section "All Pages" + bulk INSERT requirements
    ▼
[5] Метрики покрытия
    │
    ▼
[6] Word-документ (опционально)
```

---

## Шаг 1: Сохранение файла

**Код:** `src/extraction_service.py` → `_save_file()`

```python
# Сохранить PDF
pdf_path = UPLOAD_DIR / f"{timestamp}_{filename}"
open(pdf_path, "wb").write(file_content)

# Создать рабочий каталог для изображений и отчётов
output_dir = Path(tempfile.mkdtemp(prefix="req_extract_"))
```

Путь сохранения: `data/uploads/{YYYYMMDD_HHMMSS}_{оригинальное_имя}.pdf`

---

## Шаг 2: Извлечение страниц PDF

**Код:** `src/pdf_processor.py` → `extract_pages()`

Используется `ThreadPoolExecutor` — все страницы обрабатываются параллельно:

```python
with ThreadPoolExecutor() as executor:
    futures = {
        executor.submit(_extract_single_page, pdf_path, page_num, image_dir): page_num
        for page_num in range(total_pages)
    }
```

Для каждой страницы:

```python
# pymupdf4llm → текст в Markdown-формате + изображения на диск
chunk = pymupdf4llm.to_markdown(
    pdf_path,
    page_chunks=True,
    pages=[page_num],
    write_images=True,
    image_path=str(image_dir),
    dpi=150
)
```

**Результат:**

```python
pages = [
    {"page_number": 1, "text": "# Введение\n..."},
    {"page_number": 2, "text": "## 1.1 Общие требования\n..."},
    ...
]

page_image_metadata = {
    5: [
        {"filename": "page_5_image_0.png", "path": ".../images/page_5_image_0.png", "page_number": 5, "index": 0}
    ],
    10: [
        {"filename": "page_10_image_0.png", ...},
        {"filename": "page_10_image_1.png", ...}
    ]
}
```

Формат имён изображений: `page_{N}_image_{I}.{ext}` (1-based)

---

## Шаг 3: AI-обработка страниц

**Код:** `src/requirements_extractor.py` → `extract_requirements_from_all_pages()`

### Батчевая обработка

```python
for batch_start in range(0, total_pages, batch_size):  # batch_size=7
    batch = pages[batch_start : batch_start + batch_size]
    batch_results = await _process_page_batch_simple(batch, image_dir, ...)
    all_requirements.extend(batch_results)
```

Внутри батча страницы обрабатываются параллельно через `asyncio.gather`.

### Обработка одной страницы

```python
async def _process_single_page_simple(page_obj, image_dir, ...):
    page_number = page_obj["page_number"]
    page_text = page_obj["text"]

    # 1. Пропустить пустые страницы
    if not page_text or len(page_text.strip()) < 50:
        return []

    # 2. Текст → AI (в потоке пула)
    text_reqs = await loop.run_in_executor(
        None,
        ai_client.extract_requirements,
        "Page", f"Page {page_number}", str(page_number), page_text
    )

    # 3. Изображения → AI (параллельно)
    if image_dir and page_number in page_image_metadata:
        image_tasks = [
            _async_extract_from_image_simple(Path(img["path"]), page_number)
            for img in page_image_metadata[page_number]
            if Path(img["path"]).exists()
        ]
        image_results = await asyncio.gather(*image_tasks, return_exceptions=True)

    return text_reqs + image_reqs
```

### Запрос к OpenRouter (текст)

**Код:** `src/openrouter_client.py` → `extract_requirements()`

```python
POST https://openrouter.ai/api/v1/chat/completions
Authorization: Bearer {api_key}

{
  "model": "anthropic/claude-sonnet-4-5",
  "messages": [
    {"role": "system", "content": "<system_prompt из prompts.yaml>"},
    {"role": "user", "content": "Раздел: Page\nСтраница: 15\n\n<текст страницы>"}
  ]
}
```

Ответ AI парсится из JSON-массива с retry-логикой (до 3 попыток, экспоненциальный backoff: 1с, 2с, 4с).

### Запрос к OpenRouter (изображение)

```python
{
  "model": "anthropic/claude-sonnet-4-5",
  "messages": [
    {"role": "system", "content": "<system_prompt>"},
    {
      "role": "user",
      "content": [
        {"type": "text", "text": "Страница: 10"},
        {"type": "image_url", "image_url": {"url": "data:image/png;base64,..."}}
      ]
    }
  ]
}
```

### Структура извлечённого требования

```json
{
  "id": "REQ-15-001",
  "text": "Насос должен обеспечивать производительность не менее 150 м³/ч",
  "type": "technical",
  "priority": "mandatory",
  "source_page": 15,
  "source_type": "text"
}
```

---

## Шаг 4: Сохранение в БД

**Код:** `src/extraction_service.py` → `_save_to_db()`

```python
# Создать одну секцию для всего документа
section = crud.create_section(
    document_id=db_document.id,
    section_number="1",
    title="All Pages",
    page_start=1,
    page_end=len(pages)
)

# Bulk INSERT всех требований
saved_count = crud.bulk_create_requirements(
    document_id=db_document.id,
    section_id=section.id,
    requirements=all_requirements
)
```

Используется `Session.execute(insert(Requirement), [...])` — один SQL-запрос для всех требований.

---

## Шаг 5: Метрики покрытия

**Код:** `src/extraction_service.py` → `_save_coverage_metrics()`

```python
pages_with_reqs = {r.source_page for r in all_requirements if r.source_page}
processed_pages = len(pages_with_reqs)
skipped_pages = sorted(set(range(1, total_pages + 1)) - pages_with_reqs)
coverage_pct = processed_pages / total_pages * 100
```

**Логика:**
- **Обработанная страница** = страница, на которой найдено хотя бы одно требование
- **Пропущенная страница** = страница без требований (нормально для титульных, оглавления и т.д.)

---

## Шаг 6: Экспорт Word (опционально)

**Код:** `src/word_exporter.py` → `generate_word_document()`

Word-документ генерируется из объектов в памяти сразу после AI-обработки. При запросе экспорта через API (`GET /api/documents/{id}/export/word`) используется `generate_word_from_db()` — строит документ из данных БД.

---

## Статистика запросов

### Типичный документ (50 страниц)

| Тип запроса | Количество | Примечание |
|---|---|---|
| Текстовых AI-запросов | ≤ 50 | По одному на непустую страницу |
| Запросов по изображениям | 0–50 | Зависит от содержимого |
| Батчей (по 7 страниц) | ~8 | `ceil(50/7)` |

### Стоимость (Claude Sonnet)

- Вход: ~$3/M токенов, выход: ~$15/M токенов
- Среднее на 50-страничный документ: **$0.15–$0.50**
- Время обработки: **3–10 минут** (зависит от скорости API)

---

## Обработка ошибок

| Ситуация | Поведение |
|---|---|
| Пустая/короткая страница (< 50 символов) | Страница пропускается, в лог идёт `debug` |
| Ошибка AI на одной странице | `asyncio.gather` возвращает `Exception`, страница пропускается с `logger.error` |
| Ошибка парсинга JSON от AI | До 3 retry с экспоненциальным backoff; если все неудачны — возвращается `[]` |
| Ошибка записи в БД | Логируется `exc_info=True`; `total_requirements_saved = len(all_requirements)` как fallback |
| Ошибка генерации Word | Логируется warning; результат возвращается без Word-файла |
