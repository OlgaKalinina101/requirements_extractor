# Модель данных

**Requirements Management System — описание сущностей и связей**

---

## ER-диаграмма (упрощённая)

```
┌──────────┐       ┌────────────┐       ┌──────────┐       ┌──────────────────┐
│  users   │──1:N──│ assignments│──N:1──│requirements│──N:1──│   documents     │
└──────────┘       └────────────┘       └──────────┘       └──────────────────┘
     │                                       │  │  │               │   │
     │                                       │  │  │  N:1          │   │
     │                                       │  │  └──────► sections   │
     │                                       │  │                      │
     │                                       │  └─── self-ref ◄───┘   │
     │                                       │       (parent_id)       │
     │                                       │                         │
     │                                  N:1  │                    1:1  │
     │                         ┌─────────────┘                ┌───────┘
     │                         ▼                              ▼
     │               ┌──────────────────┐        ┌──────────────────┐
     │               │ requirement_     │        │ coverage_metrics │
     │               │ history          │        └──────────────────┘
     │               └──────────────────┘
     │                                           ┌──────────────────┐
     │                                           │ document_pages   │
     │                                           └──────────────────┘
     │               ┌──────────────────┐
     │               │   comments       │
     │               └──────────────────┘
     │
     └───1:N────►  ┌──────────────────┐
                   │ requirement_links │
                   └──────────────────┘

┌──────────────────┐    ┌──────────┐
│ dictionary_items │    │ prompts  │
│ (все справочники)│    └──────────┘
└──────────────────┘

┌──────────┐
│ projects │──1:N──► documents
└──────────┘
```

---

## Перечень таблиц

| # | Таблица               | Описание по ТЗ                                                                 |
|---|-----------------------|--------------------------------------------------------------------------------|
| 1 | `users`               | Пользователи: логин (email), имя, роль, пароль                                |
| 2 | `projects`            | Справочник проектов                                                            |
| 3 | `documents`           | Загруженные ТТ-документы с привязкой к проекту, хранение исходного PDF         |
| 4 | `sections`            | Разделы документа (по оглавлению)                                              |
| 5 | `requirements`        | Требования: текст, тип, приоритет, статус, страница, ответственный, дисциплина |
| 6 | `assignments`         | Назначения: связь требования с ответственным (кто назначил, когда, срок)       |
| 7 | `coverage_metrics`    | Метрики покрытия документа (обработано / пропущено страниц)                    |
| 8 | `dictionary_items`    | Все управляемые справочники (типы, приоритеты, статусы, дисциплины и т.д.)     |
| 9 | `requirement_history` | Аудит: исходный текст ИИ, правки, автор правки, дата                           |
|10 | `comments`            | Комментарии к требованиям                                                      |
|11 | `requirement_links`   | Связи между требованиями (зависит от, конфликтует с, выведено из)              |
|12 | `document_pages`      | Текст и координаты блоков по страницам (для подсветки в PDF-просмотрщике)      |
|13 | `prompts`             | Шаблоны ИИ-промптов, редактируемые администратором                             |

---

## Детальное описание сущностей

### 1. users — Пользователи

| Поле            | Тип          | Обязательное | Описание                                          |
|-----------------|--------------|:------------:|---------------------------------------------------|
| `id`            | INTEGER PK   | да           | Первичный ключ                                    |
| `email`         | VARCHAR(255) | да           | Уникальный email (логин)                          |
| `hashed_password`| VARCHAR(255)| да           | Хеш пароля (bcrypt)                               |
| `full_name`     | VARCHAR(255) | нет          | ФИО пользователя                                  |
| `role`          | VARCHAR(50)  | да           | Роль: `admin`, `manager`, `department_head`, `user`|
| `is_active`     | BOOLEAN      | да           | Активен ли аккаунт (мягкое удаление)              |
| `created_at`    | TIMESTAMP    | да           | Дата создания                                     |

**Роли:**
- `admin` — полный доступ (загрузка документов, запуск обработки ИИ, назначение ответственных, управление справочниками и пользователями)
- `manager` — загрузка, обработка, назначение, верификация
- `department_head` — аналогично manager
- `user` — исполнитель: просмотр назначенных требований, фильтрация, изменение статусов выполнения

---

### 2. projects — Проекты

| Поле                    | Тип          | Обязательное | Описание                                |
|-------------------------|--------------|:------------:|-----------------------------------------|
| `id`                    | INTEGER PK   | да           | Первичный ключ                          |
| `name`                  | VARCHAR(255) | да           | Название проекта                        |
| `code`                  | VARCHAR(100) | нет          | Уникальный код проекта                  |
| `description`           | TEXT         | нет          | Описание                                |
| `status`                | VARCHAR(50)  | да           | Статус (`active`, `archived`)           |
| `requirement_manager_id`| INTEGER FK   | нет          | Менеджер требований (→ `users.id`)      |
| `created_at`            | TIMESTAMP    | да           | Дата создания                           |
| `updated_at`            | TIMESTAMP    | да           | Дата обновления                         |

**Связи:** `projects` 1:N → `documents`

---

### 3. documents — Документы

| Поле            | Тип          | Обязательное | Описание                                        |
|-----------------|--------------|:------------:|-------------------------------------------------|
| `id`            | INTEGER PK   | да           | Первичный ключ                                  |
| `project_id`    | INTEGER FK   | нет          | Проект (→ `projects.id`), CASCADE               |
| `filename`      | VARCHAR(255) | да           | Имя файла                                       |
| `file_path`     | TEXT         | да           | Путь к PDF на диске                             |
| `status`        | VARCHAR(50)  | да           | `pending`, `processing`, `completed`, `failed`  |
| `document_type` | VARCHAR(100) | нет          | Тип документа (из справочника)                  |
| `total_pages`   | INTEGER      | нет          | Общее кол-во страниц                            |
| `model_used`    | VARCHAR(100) | нет          | Какая ИИ-модель использовалась                  |
| `uploaded_at`   | TIMESTAMP    | да           | Дата загрузки                                   |
| `processed_at`  | TIMESTAMP    | нет          | Дата завершения обработки                       |

**Связи:** `documents` 1:N → `sections`, `requirements`, `document_pages`; 1:1 → `coverage_metrics`

---

### 4. sections — Разделы документа

| Поле            | Тип          | Обязательное | Описание                                |
|-----------------|--------------|:------------:|-----------------------------------------|
| `id`            | INTEGER PK   | да           | Первичный ключ                          |
| `document_id`   | INTEGER FK   | да           | Документ (→ `documents.id`), CASCADE    |
| `section_number`| VARCHAR(50)  | нет          | Номер раздела (напр. «1.2.3»)          |
| `title`         | TEXT         | нет          | Заголовок раздела                       |
| `page_start`    | INTEGER      | нет          | Начальная страница                      |
| `page_end`      | INTEGER      | нет          | Конечная страница                       |

**Связи:** `sections` 1:N → `requirements`

---

### 5. requirements — Требования

| Поле                | Тип          | Обязательное | Описание                                              |
|---------------------|--------------|:------------:|-------------------------------------------------------|
| `id`                | INTEGER PK   | да           | Первичный ключ                                        |
| `document_id`       | INTEGER FK   | да           | Документ (→ `documents.id`), CASCADE                  |
| `section_id`        | INTEGER FK   | нет          | Раздел (→ `sections.id`), SET NULL                    |
| `parent_id`         | INTEGER FK   | нет          | Родительское требование (→ `requirements.id`), иерархия|
| `requirement_id`    | VARCHAR(50)  | да           | Идентификатор (напр. «REQ-1-015»)                     |
| `text`              | TEXT         | да           | Текст требования (актуальный)                         |
| `type`              | VARCHAR(50)  | нет          | Тип (из справочника `requirement_types`)              |
| `priority`          | VARCHAR(50)  | нет          | Приоритет (из справочника `priorities`)                |
| `page_number`       | INTEGER      | нет          | Страница исходного документа                          |
| `bbox`              | JSON         | нет          | Координаты на странице                                |
| `subitems`          | JSON         | нет          | Подпункты (если требование содержит список)           |
| `assignee_id`       | INTEGER FK   | нет          | Ответственный исполнитель (→ `users.id`)              |
| `discipline`        | VARCHAR(100) | нет          | Дисциплина (из справочника `disciplines`)             |
| `deadline`          | DATE         | нет          | Срок исполнения                                       |
| `verification_method`| VARCHAR(100)| нет          | Метод подтверждения (из справочника)                  |
| `lifecycle_status`  | VARCHAR(100) | нет          | Статус жизненного цикла (см. ниже)                    |
| `status`            | VARCHAR(50)  | да           | Статус верификации: `pending`, `accepted`, `rejected`, `modified` |
| `ai_suggested`      | TEXT         | да           | Исходный текст, предложенный ИИ                       |
| `human_edited`      | TEXT         | нет          | Текст после правки человеком                          |
| `edit_reason`       | TEXT         | нет          | Причина редактирования                                |
| `source_quote`      | TEXT         | нет          | Дословная цитата из документа                         |
| `edited_by`         | VARCHAR(255) | нет          | Кто отредактировал                                    |
| `edited_at`         | TIMESTAMP    | нет          | Дата редактирования                                   |
| `created_at`        | TIMESTAMP    | да           | Дата создания                                         |

**Жизненный цикл (поле `lifecycle_status`):**

```
Извлечено → На верификации → Принято → Назначено → В работе → Выполнено → Закрыто
extracted  → verification   → accepted → assigned  → in_progress → completed → closed
```

**Связи:**
- Иерархия: `parent_id` → `requirements.id` (самореференция)
- `requirements` 1:N → `assignments`, `comments`, `requirement_history`, `requirement_links`

---

### 6. assignments — Назначения

| Поле             | Тип          | Обязательное | Описание                                          |
|------------------|--------------|:------------:|---------------------------------------------------|
| `id`             | INTEGER PK   | да           | Первичный ключ                                    |
| `requirement_id` | INTEGER FK   | да           | Требование (→ `requirements.id`), CASCADE         |
| `assignee_id`    | INTEGER FK   | да           | Ответственный (→ `users.id`), CASCADE             |
| `assigned_by_id` | INTEGER FK   | нет          | Кто назначил (→ `users.id`), SET NULL             |
| `assigned_at`    | TIMESTAMP    | да           | Когда назначено                                   |
| `deadline`       | DATE         | нет          | Срок исполнения                                   |
| `is_active`      | BOOLEAN      | да           | Текущее назначение (`true`) или историческое       |

При переназначении предыдущая запись получает `is_active = false`, создаётся новая с `is_active = true`.

---

### 7. coverage_metrics — Метрики покрытия

| Поле                  | Тип          | Обязательное | Описание                                     |
|-----------------------|--------------|:------------:|----------------------------------------------|
| `id`                  | INTEGER PK   | да           | Первичный ключ                               |
| `document_id`         | INTEGER FK   | да           | Документ (→ `documents.id`), UNIQUE, CASCADE |
| `total_pages`         | INTEGER      | да           | Всего страниц                                |
| `processed_pages`     | INTEGER      | да           | Обработано страниц                           |
| `skipped_pages`       | INTEGER[]    | нет          | Массив номеров пропущенных страниц           |
| `coverage_percent`    | FLOAT        | да           | Процент покрытия (0–100)                     |
| `requirements_count`  | INTEGER      | да           | Общее количество извлечённых требований      |
| `requirements_by_type`| JSON         | нет          | Количество по типам `{"Technical": 34, ...}` |
| `calculated_at`       | TIMESTAMP    | да           | Дата расчёта                                 |

---

### 8. dictionary_items — Управляемые справочники

| Поле         | Тип          | Обязательное | Описание                                |
|--------------|--------------|:------------:|-----------------------------------------|
| `id`         | INTEGER PK   | да           | Первичный ключ                          |
| `dict_type`  | VARCHAR(50)  | да           | Тип справочника (см. ниже)              |
| `code`       | VARCHAR(100) | нет          | Код записи (машиночитаемый)             |
| `name`       | VARCHAR(255) | да           | Отображаемое название                   |
| `description`| TEXT         | нет          | Описание                                |
| `color`      | VARCHAR(50)  | нет          | Цвет для UI (Vuetify)                   |
| `sort_order` | INTEGER      | да           | Порядок сортировки                      |
| `is_active`  | BOOLEAN      | да           | Активна ли запись                       |
| `created_at` | TIMESTAMP    | да           | Дата создания                           |

**Типы справочников (`dict_type`):**

| Код                    | Описание по ТЗ                                           | Примеры значений                                                 |
|------------------------|----------------------------------------------------------|------------------------------------------------------------------|
| `requirement_types`    | Типы требований                                           | Supply, Technical, Functional, Performance, Safety, Documentation, Interface, Constraint, Process |
| `priorities`           | Приоритеты                                                | Critical, High, Medium, Low                                      |
| `statuses`             | Статусы верификации                                       | pending, accepted, rejected, modified, in_progress, done, blocked|
| `lifecycle_statuses`   | Жизненный цикл требования                                | extracted, verification, accepted, assigned, in_progress, completed, closed |
| `disciplines`          | Инженерные дисциплины                                     | Mechanical, Electrical, I&C, Process, Civil, HVAC, Piping, Software |
| `verification_methods` | Методы подтверждения                                      | Analysis, Test, Inspection, Demonstration                        |
| `link_types`           | Типы связей между требованиями                            | depends_on, conflicts_with, derived_from, parent_child           |
| `document_types`       | Типы документов                                           | Technical Specification, Requirements Document, Design Document  |

Все справочники редактируются администратором через UI (`/admin` → CRUD `/api/dictionaries/{dict_type}`).

---

### 9. requirement_history — Аудит изменений

| Поле             | Тип          | Обязательное | Описание                                          |
|------------------|--------------|:------------:|---------------------------------------------------|
| `id`             | INTEGER PK   | да           | Первичный ключ                                    |
| `requirement_id` | INTEGER FK   | да           | Требование (→ `requirements.id`), CASCADE         |
| `user_id`        | INTEGER FK   | нет          | Кто внёс изменение (→ `users.id`)                 |
| `action`         | VARCHAR(50)  | да           | Действие: `accepted`, `rejected`, `edited`, `assigned`, `status_changed`, `lifecycle_status_changed`, `comment_added` |
| `field_name`     | VARCHAR(100) | нет          | Имя изменённого поля                              |
| `old_value`      | TEXT         | нет          | Предыдущее значение                               |
| `new_value`      | TEXT         | нет          | Новое значение                                    |
| `comment`        | TEXT         | нет          | Комментарий к изменению                           |
| `created_at`     | TIMESTAMP    | да           | Дата изменения                                    |

Обеспечивает полную прослеживаемость: исходный текст ИИ → правки человека → автор → дата.

---

### 10. comments — Комментарии

| Поле             | Тип          | Обязательное | Описание                                |
|------------------|--------------|:------------:|-----------------------------------------|
| `id`             | INTEGER PK   | да           | Первичный ключ                          |
| `requirement_id` | INTEGER FK   | да           | Требование (→ `requirements.id`), CASCADE|
| `user_id`        | INTEGER FK   | да           | Автор (→ `users.id`), CASCADE           |
| `text`           | TEXT         | да           | Текст комментария                       |
| `created_at`     | TIMESTAMP    | да           | Дата создания                           |

---

### 11. requirement_links — Связи между требованиями

| Поле                     | Тип          | Обязательное | Описание                                |
|--------------------------|--------------|:------------:|-----------------------------------------|
| `id`                     | INTEGER PK   | да           | Первичный ключ                          |
| `source_requirement_id`  | INTEGER FK   | да           | Исходное требование (→ `requirements.id`)|
| `target_requirement_id`  | INTEGER FK   | да           | Целевое требование (→ `requirements.id`) |
| `link_type`              | VARCHAR(50)  | да           | Тип связи (из справочника `link_types`)  |
| `created_at`             | TIMESTAMP    | да           | Дата создания                           |

---

### 12. document_pages — Страницы документа

| Поле           | Тип          | Обязательное | Описание                                                    |
|----------------|--------------|:------------:|-------------------------------------------------------------|
| `id`           | INTEGER PK   | да           | Первичный ключ                                              |
| `document_id`  | INTEGER FK   | да           | Документ (→ `documents.id`), CASCADE                        |
| `page_number`  | INTEGER      | да           | Номер страницы (1-based)                                    |
| `raw_text`     | TEXT         | нет          | Полный текст страницы                                       |
| `text_blocks`  | JSON         | нет          | Массив блоков с координатами: `[{text, x0, y0, x1, y1}]`   |
| `is_ocr`       | BOOLEAN      | да           | Страница обработана OCR (нет текстового слоя)               |
| `created_at`   | TIMESTAMP    | да           | Дата создания                                               |

Используется для подсветки текста требований в PDF-просмотрщике на фронтенде.

---

### 13. prompts — Шаблоны ИИ-промптов

| Поле              | Тип          | Обязательное | Описание                                         |
|-------------------|--------------|:------------:|--------------------------------------------------|
| `id`              | INTEGER PK   | да           | Первичный ключ                                   |
| `key`             | VARCHAR(100) | да           | Уникальный ключ промпта                          |
| `name`            | VARCHAR(200) | нет          | Отображаемое название                            |
| `version`         | VARCHAR(50)  | нет          | Версия промпта                                   |
| `instruction`     | TEXT         | нет          | Системная инструкция (редактируемая)             |
| `response_format` | TEXT         | нет          | JSON-схема ожидаемого ответа (read-only)         |
| `user_template`   | TEXT         | нет          | Шаблон пользовательского сообщения с {variables} |
| `temperature`     | FLOAT        | нет          | Температура генерации                            |
| `max_tokens`      | INTEGER      | нет          | Лимит токенов                                    |
| `updated_at`      | TIMESTAMP    | нет          | Дата последнего обновления                       |

---

## Индексы

| Таблица         | Индекс                               | Поля                           |
|-----------------|---------------------------------------|--------------------------------|
| `users`         | `ix_users_email`                      | `email` (UNIQUE)               |
| `requirements`  | `ix_requirements_document_id`         | `document_id`                  |
| `requirements`  | `ix_requirements_section_id`          | `section_id`                   |
| `requirements`  | `ix_requirements_parent_id`           | `parent_id`                    |
| `requirements`  | `ix_requirements_requirement_id`      | `requirement_id`               |
| `requirements`  | `ix_requirements_status`              | `status`                       |
| `requirements`  | `ix_requirements_discipline`          | `discipline`                   |
| `documents`     | `ix_documents_project_id`             | `project_id`                   |
| `sections`      | `ix_sections_document_id`             | `document_id`                  |
| `assignments`   | `ix_assignments_requirement_id`       | `requirement_id`               |
| `assignments`   | `ix_assignments_assignee_id`          | `assignee_id`                  |
| `document_pages`| `ix_document_pages_document_id`       | `document_id`                  |
| `dictionary_items`| `ix_dictionary_items_dict_type`     | `dict_type`                    |

---

## Миграции (Alembic)

Управление схемой выполняется через Alembic. Все миграции хранятся в `alembic/versions/`.

При запуске через Docker Compose (`entrypoint.sh`):
```bash
alembic upgrade head   # автоматически применяет все непримененные миграции
python api_server.py   # запуск API
```

Текущая цепочка: `001_initial_schema` → ... → `018_add_assignments_and_update_lifecycle`
