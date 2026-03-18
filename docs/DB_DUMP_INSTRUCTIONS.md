# Дамп и восстановление БД

## Создание дампа (у вас)

### Вариант 1: Docker (рекомендуется)

```bash
docker exec requirements-extractor-db pg_dump -U requirements_user -d requirements_db \
  --no-owner --no-acl --clean --if-exists \
  > dump_requirements.sql
```

Или через скрипт (если контейнер называется `requirements-extractor-db`):

```bash
# Linux/Mac
./scripts/dump_db.sh

# Windows PowerShell
.\scripts\dump_db.ps1
```

### Вариант 2: Локальный pg_dump

Если PostgreSQL установлен локально и порт 5433 доступен:

```bash
pg_dump -h localhost -p 5433 -U requirements_user -d requirements_db \
  --no-owner --no-acl --clean --if-exists \
  -f dump_requirements.sql
```
(пароль: `requirements_pass`)

---

## Восстановление (у заказчика)

### Вариант 1: Docker

1. Запустить контейнеры: `docker compose up -d postgres`
2. Дождаться готовности БД (10–20 сек)
3. Загрузить дамп:

```bash
# Скопировать файл в контейнер
docker cp dump_requirements.sql requirements-extractor-db:/tmp/dump.sql

# Выполнить восстановление
docker exec -i requirements-extractor-db psql -U requirements_user -d requirements_db -f /tmp/dump.sql
```

### Вариант 2: Локальный PostgreSQL

```bash
psql -h localhost -p 5432 -U requirements_user -d requirements_db -f dump_requirements.sql
```

(Создать БД, если её нет: `createdb -U postgres requirements_db`)

---

## Файлы документов (data/uploads)

Дамп БД содержит только метаданные. Сами PDF-файлы лежат в `./data/uploads/`.

Чтобы передать полный бэкап:

1. Сделать дамп БД (см. выше)
2. Архивировать папку `data/`:

```bash
# Linux/Mac
tar -czvf data_backup.tar.gz data/

# Windows PowerShell
Compress-Archive -Path data -DestinationPath data_backup.zip
```

3. Сам дамп лежит в: `dump_requirements.sql` + `data_backup.tar.gz` (или `.zip`)

4. Как загрузить: распаковать `data/` в корень проекта, затем загрузить дамп БД.
