# 🚀 Быстрый старт для тестирования

## Простой способ (Windows)

### 1. Запустить всё одной командой:
```bash
start_test.bat
```

Этот скрипт:
- ✅ Запустит PostgreSQL в Docker
- ✅ Применит миграции Alembic
- ✅ Запустит API сервер

### 2. Или вручную:

#### Шаг 1: Запустить PostgreSQL
```bash
docker-compose up -d postgres
```

#### Шаг 2: Применить миграции
```bash
# Установить переменную окружения
$env:DATABASE_URL="postgresql://requirements_user:requirements_pass@localhost:5433/requirements_db"

# Применить миграции
alembic upgrade head
```

**ИЛИ** использовать скрипт:
```bash
python init_db.py
```

#### Шаг 3: Запустить API
```bash
python api_server.py
```

## ✅ Проверка работы

### 1. Проверить, что PostgreSQL работает:
```bash
docker ps
# Должен быть контейнер requirements-extractor-db
```

### 2. Проверить API:
Откройте в браузере:
- **API**: http://localhost:8000
- **Документация**: http://localhost:8000/docs
- **Health check**: http://localhost:8000/health

### 3. Проверить БД endpoints:
```bash
# Получить список документов (должен быть пустым)
curl http://localhost:8000/api/documents

# Должен вернуть: {"documents": [], "total": 0}
```

### 4. Загрузить тестовый PDF:
```bash
curl -X POST http://localhost:8000/api/extract ^
  -F "file=@test.pdf" ^
  -F "generate_word=true"
```

После загрузки проверьте:
```bash
# Должен вернуть список с одним документом
curl http://localhost:8000/api/documents
```

## 🔍 Отладка

### Если PostgreSQL не запускается:
```bash
# Проверить логи
docker-compose logs postgres

# Пересоздать контейнер
docker-compose down postgres
docker-compose up -d postgres
```

### Если миграции не применяются:
```bash
# Проверить подключение к БД
docker exec -it requirements-extractor-db psql -U requirements_user -d requirements_db -c "\dt"

# Должны быть таблицы: documents, sections, requirements, coverage_metrics
```

### Если API не подключается к БД:
- Проверьте переменную окружения `DATABASE_URL`
- Убедитесь, что PostgreSQL запущен: `docker ps`
- Проверьте логи API на наличие ошибок подключения

## 📝 Важно

1. **Миграции нужно применить ОДИН РАЗ** после первого запуска PostgreSQL
2. **Если пересоздаете контейнер PostgreSQL** (docker-compose down), миграции нужно применить снова
3. **Данные в БД сохраняются** в Docker volume `postgres_data`, поэтому при `docker-compose down` данные не теряются

## 🎯 Что дальше?

После успешного тестирования можно:
- Загрузить PDF через API
- Проверить, что данные сохраняются в БД
- Протестировать новые endpoints для получения документов и требований
