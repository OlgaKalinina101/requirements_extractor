# 📊 PDF Processing Pipeline - Complete Flow

## Вопросы, на которые отвечает этот документ:

1. ✅ **Куда извлекаются изображения?**
2. ✅ **Как изображения передаются модели?**
3. ✅ **Как передаются страницы для обработки?**
4. ✅ **Как считаются обработанные страницы?**

---

## 1. 📥 Извлечение изображений

### Где и как сохраняются изображения

**Путь:** `data/output/{timestamp}/images/`

**Код:** `api_server.py:449-455`
```python
config.image_dir = output_dir / "images"
config.image_dir.mkdir(parents=True, exist_ok=True)
```

**Пример:** `data/output/20260222_123456/images/`

### Процесс извлечения

**1. PDF → Параллельная обработка страниц**

`pdf_processor.py:204-309` - `extract_pages()`

- Использует `ThreadPoolExecutor` с автоопределением количества потоков
- Обрабатывает **ВСЕ страницы параллельно** одновременно
- Каждая страница обрабатывается в отдельном потоке

```python
with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
    future_to_page = {
        executor.submit(self._extract_single_page, pdf_path, page_num, image_dir): page_num
        for page_num in range(total_pages)
    }
```

**2. Обработка одной страницы**

`pdf_processor.py:70-203` - `_extract_single_page()`

```python
chunk = pymupdf4llm.to_markdown(
    str(pdf_path),
    page_chunks=True,
    pages=[page_num],
    write_images=True,        # ✅ ИЗВЛЕКАТЬ ИЗОБРАЖЕНИЯ
    image_path=str(image_dir), # ✅ ПУТЬ СОХРАНЕНИЯ
    dpi=self.config.dpi,       # Качество (обычно 150-300 DPI)
)
```

**Что извлекается:**
- ✅ Текст страницы (markdown формат)
- ✅ Изображения (PNG/JPG файлы)
- ✅ Метаданные изображений (имя файла, индекс, страница)

### Формат имен файлов изображений

**Исходный формат (pymupdf4llm):**
```
{pdf_name}-p{page_num}-img{index}.{ext}
```

**Переименовывается в:**
```
page_{page_1based}_image_{index}.{ext}
```

**Примеры:**
```
doc-p0-img0.png  →  page_1_image_0.png
doc-p5-img2.jpg  →  page_6_image_2.jpg
doc-p10-img1.png →  page_11_image_1.png
```

**Код переименования:** `pdf_processor.py:155-175`

### Метаданные изображений

**Структура:** `Dict[int, List[Dict]]`

**Ключ:** Номер страницы (1-based)
**Значение:** Список словарей с метаданными

```python
image_metadata = {
    1: [],  # Нет изображений на странице 1
    5: [    # 2 изображения на странице 5
        {
            "filename": "page_5_image_0.png",
            "path": "data/output/.../images/page_5_image_0.png",
            "page_number": 5,
            "index": 0
        },
        {
            "filename": "page_5_image_1.png",
            "path": "data/output/.../images/page_5_image_1.png",
            "page_number": 5,
            "index": 1
        }
    ],
    10: [   # 1 изображение на странице 10
        {
            "filename": "page_10_image_0.png",
            "path": "data/output/.../images/page_10_image_0.png",
            "page_number": 10,
            "index": 0
        }
    ]
}
```

---

## 2. 🤖 Передача данных к AI модели

### Как работает обработка секциями

**Важно:** Документ обрабатывается **ПО СЕКЦИЯМ**, а не по страницам.

**Процесс:**

1. **TOC (Table of Contents)** определяет секции
2. Каждая секция обрабатывается **отдельным запросом к AI**
3. Для каждой секции:
   - Отправляется **текст секции** (может быть 1-50 страниц)
   - Отправляются **все изображения секции** (по одному)

### Обработка ОДНОЙ секции

**Код:** `api_server.py:651-810`

```python
for idx, toc_entry in enumerate(extractor.toc_entries):
    # 1. Получить текст секции (все страницы секции)
    section_text = extractor.pdf_processor.get_section_text(
        extractor.pages,
        toc_entry.page_start,  # Например, страница 10
        end_page              # Например, страница 33
    )
    
    # 2. Извлечь требования из ТЕКСТА (1 запрос к AI)
    requirements = extractor.ai_client.extract_requirements(
        section_text=section_text  # Текст страниц 10-33
    )
    
    # 3. Найти изображения в этой секции
    section_images = []
    for page_num in range(10, 33):  # Страницы секции
        if page_num in extractor.page_image_metadata:
            section_images.extend(
                extractor.page_image_metadata[page_num]
            )
    
    # 4. Обработать КАЖДОЕ изображение ОТДЕЛЬНО
    for img_meta in section_images:
        img_reqs = extractor.ai_client.extract_requirements_from_image(
            image_path=Path(img_meta["path"]),
            page_number=img_meta["page_number"]
        )
        image_requirements.extend(img_reqs)
```

### Схема обработки секции

```
Секция 2.3 (страницы 10-33)
│
├─ Шаг 1: Текст → AI (1 запрос)
│  └─ Отправляется: весь текст страниц 10-33
│  └─ Возвращается: список требований из текста
│
├─ Шаг 2: Поиск изображений
│  ├─ Страница 10: 2 изображения
│  ├─ Страница 12: 1 изображение
│  └─ Страница 31: 3 изображения
│
└─ Шаг 3: Каждое изображение → AI (N запросов)
   ├─ page_10_image_0.png → AI → требования
   ├─ page_10_image_1.png → AI → требования
   ├─ page_12_image_0.png → AI → требования
   ├─ page_31_image_0.png → AI → требования
   ├─ page_31_image_1.png → AI → требования
   └─ page_31_image_2.png → AI → требования
```

**Итого для секции:**
- **1 запрос** для текста (весь текст секции)
- **6 запросов** для изображений (по одному на изображение)
- **Всего: 7 запросов к AI**

### Как изображение передается к AI

**Код:** `openrouter_client.py:384-533` - `extract_requirements_from_image()`

**1. Кодирование изображения в Base64**

```python
def _encode_image(self, image_path: Path) -> str:
    with open(image_path, "rb") as f:
        image_bytes = f.read()
    base64_image = base64.b64encode(image_bytes).decode('utf-8')
    
    # Определить MIME тип
    ext = image_path.suffix.lower()
    mime_type = {
        '.png': 'image/png',
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
    }.get(ext, 'image/png')
    
    # Data URI
    return f"data:{mime_type};base64,{base64_image}"
```

**2. Формирование запроса**

```python
messages = [
    {"role": "system", "content": "Ты — эксперт по извлечению требований..."},
    {
        "role": "user",
        "content": [
            {
                "type": "text",
                "text": f"Раздел: {section_number} {section_title}\nСтраница: {page_number}"
            },
            {
                "type": "image_url",
                "image_url": {
                    "url": "data:image/png;base64,iVBORw0KGgoAAAANS..."
                }
            }
        ]
    }
]
```

**3. Отправка к OpenRouter API**

```python
response = requests.post(
    "https://openrouter.ai/api/v1/chat/completions",
    headers={
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    },
    json={
        "model": "anthropic/claude-3.7-sonnet:beta",
        "messages": messages,
        "temperature": 0.7
    }
)
```

**Формат ответа AI:**
```json
{
  "requirements": [
    {
      "id": "REQ-23-IMG-001",
      "text": "Насос должен иметь максимальную производительность 150 м³/ч",
      "type": "Техническое",
      "priority": "Обязательно"
    },
    {
      "id": "REQ-23-IMG-002",
      "text": "Давление на выходе не менее 6 бар",
      "type": "Техническое",
      "priority": "Обязательно"
    }
  ]
}
```

---

## 3. 📄 Обработка страниц секциями

### Как определяются секции

**Метод 1: TOC из PDF (AI парсинг)**

`api_server.py:556-603`

1. Берутся **первые 10 страниц** документа
2. Отправляются к AI для парсинга оглавления
3. AI возвращает список секций с номерами страниц

```python
toc_text = "\n\n".join(extractor.pages[:10])
toc_entries = extractor.ai_client.parse_table_of_contents(toc_text)
```

**Пример TOC:**
```python
[
    TableOfContentsEntry(
        number="2.3",
        title="Технические требования к насосам",
        page_start=10,
        level=2
    ),
    TableOfContentsEntry(
        number="2.3.1",
        title="Основные параметры",
        page_start=12,
        level=3
    ),
    TableOfContentsEntry(
        number="3",
        title="Требования к электрооборудованию",
        page_start=33,
        level=1
    ),
]
```

**Метод 2: Автоматические секции (fallback)**

`api_server.py:609-626`

Если TOC не парсится:
- Документ делится на секции по ~20 страниц
- Секции нумеруются автоматически

```python
sections_per_doc = max(1, total_pages // 20)
for i in range(0, total_pages, sections_per_doc):
    manual_toc.append({
        "number": str(section_num),
        "title": f"Раздел {section_num} (стр. {i+1}-{min(i+sections_per_doc, total_pages)})",
        "page_start": i + 1
    })
```

### Как секция связывается со страницами

**Код:** `api_server.py:664-689`

```python
# Определить диапазон страниц секции
start_page = toc_entry.page_start  # 10
end_page = None

# Найти следующую секцию
for next_entry in extractor.toc_entries[idx+1:]:
    if next_entry.page_start > toc_entry.page_start:
        end_page = next_entry.page_start  # 33
        break

# Если нет следующей секции — до конца документа
if end_page is None:
    end_page = len(extractor.pages) + 1

# Получить текст секции (страницы 10-32)
section_text = extractor.pdf_processor.get_section_text(
    extractor.pages,
    start_page=10,
    end_page=33  # Не включается (range)
)
```

**`get_section_text()` - `pdf_processor.py:311-340`**

```python
def get_section_text(self, pages: List[str], start_page: int, end_page: int = None) -> str:
    if end_page is None:
        end_page = len(pages) + 1
    
    # 1-indexed → 0-indexed
    start_idx = start_page - 1  # 10 → 9
    end_idx = end_page - 1       # 33 → 32
    
    # Объединить страницы
    section_pages = pages[start_idx:end_idx]  # pages[9:32] = 23 страницы
    return "\n\n".join(section_pages)
```

### Пример полного цикла

**Документ: 225 страниц, 5 секций**

```
Секция 1: "Введение" (стр. 1-9)
├─ Текст: 9 страниц → AI (1 запрос)
└─ Изображения: 0

Секция 2: "Общие требования" (стр. 10-32)
├─ Текст: 23 страницы → AI (1 запрос)
└─ Изображения: 5 (на стр. 10, 12, 31)
   ├─ page_10_image_0.png → AI
   ├─ page_10_image_1.png → AI
   ├─ page_12_image_0.png → AI
   ├─ page_31_image_0.png → AI
   └─ page_31_image_1.png → AI

Секция 3: "Технические требования" (стр. 33-180)
├─ Текст: 148 страниц → AI (1 запрос)
└─ Изображения: 199 (на разных страницах)
   └─ 199 запросов к AI

Секция 4: "Приложения" (стр. 181-220)
├─ Текст: 40 страниц → AI (1 запрос)
└─ Изображения: 15
   └─ 15 запросов к AI

Секция 5: "Справочная информация" (стр. 221-225)
├─ Текст: 5 страниц → AI (1 запрос)
└─ Изображения: 0

ИТОГО:
- Текстовых запросов: 5
- Запросов изображений: 219
- ВСЕГО: 224 запроса к AI
```

---

## 4. 📊 Подсчет обработанных страниц

### Как считаются обработанные страницы

**Код:** `api_server.py:872-893`

```python
# Найти страницы, у которых есть требования
pages_with_requirements = set()
for section in extractor.registry.sections:
    for req in section.requirements:
        if req.page_number:
            pages_with_requirements.add(req.page_number)

# Все страницы документа
all_pages = set(range(1, len(extractor.pages) + 1))

# Вычислить пропущенные
skipped_pages = sorted(list(all_pages - pages_with_requirements))
processed_pages = len(pages_with_requirements)
```

**Логика:**
- **Обработанная страница** = страница, на которой найдено **хотя бы одно требование**
- **Пропущенная страница** = страница **без требований**

### Пример подсчета

**Документ: 225 страниц**

```python
# Требования найдены на страницах:
pages_with_requirements = {10, 11, 12, 31, 32, 33, 34, ...}
# 23 уникальные страницы

# Все страницы:
all_pages = {1, 2, 3, 4, 5, ..., 225}
# 225 страниц

# Пропущенные:
skipped_pages = [1, 2, 3, 4, 5, 6, 7, 8, 9, 13, 14, ..., 224, 225]
# 202 страницы

# Метрики:
processed_pages = 23
coverage_percent = (23 / 225) * 100 = 10.2%
```

### Сохранение в БД

```python
crud.create_or_update_coverage_metrics(
    db=db,
    document_id=db_document.id,
    total_pages=225,
    processed_pages=23,           # ✅ Страницы с требованиями
    skipped_pages=[1, 2, 3, ...], # ✅ Страницы без требований
    requirements_count=662,
    requirements_by_type={
        "Техническое": 245,
        "Функциональное": 189,
        ...
    }
)
```

### Почему страницы пропускаются

**Нормальные причины:**
1. **Титульные страницы** (1-5) — нет требований
2. **Оглавление** (6-9) — только навигация
3. **Пустые/технические страницы** — разделители
4. **Справочные приложения** — таблицы, схемы без текста

**Ненормальные причины:**
1. AI не смог распознать требования
2. Страница содержит только изображение (без текста)
3. Ошибка обработки

---

## 5. 🔄 Полный Pipeline

```
1. UPLOAD
   └─ Файл сохранен в data/uploads/

2. EXTRACT PDF (параллельно)
   ├─ Страница 1 (поток 1) → текст + изображения
   ├─ Страница 2 (поток 2) → текст + изображения
   ├─ ...
   └─ Страница 225 (поток N) → текст + изображения
   └─ Результат: pages[], image_metadata{}

3. PARSE TOC
   ├─ AI парсит первые 10 страниц
   └─ Возвращает секции с номерами страниц

4. EXTRACT REQUIREMENTS (по секциям)
   ├─ Секция 1 (стр. 1-9)
   │  ├─ Текст → AI → требования (текст)
   │  └─ Изображения: нет
   │
   ├─ Секция 2 (стр. 10-32)
   │  ├─ Текст → AI → требования (текст)
   │  └─ Изображения:
   │     ├─ page_10_image_0.png → AI → требования (изображение)
   │     ├─ page_10_image_1.png → AI → требования (изображение)
   │     └─ ...
   │
   └─ Секция N
      └─ ...

5. SAVE TO DATABASE
   ├─ Документ (filename, total_pages, status)
   ├─ Секции (section_number, title, page_start)
   ├─ Требования (text, type, priority, page_number, source_type)
   └─ Метрики (processed_pages, skipped_pages, coverage_percent)

6. GENERATE REPORTS
   ├─ JSON registry
   └─ Word document (optional)
```

---

## 6. 📈 Статистика запросов

### Типичный документ (225 страниц, 5 секций)

**AI запросы:**
- TOC парсинг: **1 запрос**
- Текстовая обработка секций: **5 запросов** (по одному на секцию)
- Обработка изображений: **219 запросов** (по одному на изображение)
- **ИТОГО: 225 запросов к AI**

**Стоимость (Claude Sonnet 3.7):**
- Вход: ~$3/1M токенов
- Выход: ~$15/1M токенов
- Среднее: ~200K входных, ~50K выходных токенов
- **Стоимость: $0.60-$1.50** за документ

**Время обработки:**
- PDF extraction (параллельно): **1-2 минуты**
- AI обработка: **10-20 минут** (зависит от скорости API)
- **ИТОГО: 15-25 минут**

---

## 7. 💡 Ключевые выводы

### ✅ Что важно понять:

1. **Изображения извлекаются СРАЗУ** при обработке PDF (все страницы параллельно)
2. **Изображения сохраняются** в `data/output/{timestamp}/images/`
3. **Обработка идет ПО СЕКЦИЯМ**, а не по страницам
4. **Каждое изображение** отправляется к AI **отдельным запросом**
5. **Текст секции** (может быть 1-50 страниц) отправляется **одним запросом**
6. **Обработанная страница** = страница с хотя бы одним требованием
7. **Пропущенные страницы** = страницы без требований (это нормально!)

### 🎯 Оптимизации:

**Текущее решение оптимально для:**
- Точности извлечения (каждое изображение анализируется отдельно)
- Отслеживания прогресса (по секциям)
- Параллельности (PDF extraction многопоточный)

**Возможные улучшения:**
- Batch обработка изображений (несколько изображений в одном запросе)
- Кэширование результатов AI
- Предварительная фильтрация изображений (пропуск декоративных)
