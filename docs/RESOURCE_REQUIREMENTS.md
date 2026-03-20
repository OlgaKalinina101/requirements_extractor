# Требования к ресурсам (для DevOps)

## Сервисы

| Сервис | Описание |
|--------|----------|
| **postgres** | PostgreSQL 16, БД требований |
| **api** | FastAPI + uvicorn, обработка PDF, вызовы LLM (OpenRouter) |
| **frontend** | Nginx, статика Vue SPA |

---

## Рекомендуемые ресурсы

### Минимальная конфигурация (dev / демо)

| Сервис | CPU | RAM | Диск |
|--------|-----|-----|------|
| postgres | 0.25–0.5 | 256–512 MB | 2–5 GB |
| api | 0.5–1 | 512 MB – 1 GB | 500 MB |
| frontend | 0.1 | 64–128 MB | 100 MB |
| **Итого** | **1–2 vCPU** | **1–2 GB** | **5–10 GB** |

### Рекомендуемая конфигурация (prod, до ~10 одновременных пользователей)

| Сервис | CPU | RAM | Диск |
|--------|-----|-----|------|
| postgres | 0.5–1 | 512 MB – 1 GB | 10–20 GB |
| api | 1–2 | 1–2 GB | 1 GB |
| frontend | 0.25 | 128 MB | 100 MB |
| **Итого** | **2–3 vCPU** | **2–4 GB** | **15–25 GB** |

### Высокая нагрузка (много PDF, параллельная обработка)

| Сервис | CPU | RAM | Диск |
|--------|-----|-----|------|
| postgres | 1 | 1–2 GB | 50+ GB |
| api | 2–4 | 2–4 GB | 2 GB |
| frontend | 0.25 | 128 MB | 100 MB |
| **Итого** | **3–5 vCPU** | **4–6 GB** | **50+ GB** |

---

## Особенности нагрузки

- **API**: PDF-обработка (PyMuPDF) — CPU-bound, до ~36 потоков по умолчанию. Вызовы LLM идут во внешний OpenRouter, локально — в основном ожидание.
- **PostgreSQL**: Обычная OLTP-нагрузка, объём данных зависит от числа документов и требований.
- **Диск**: `data/uploads/` — PDF-файлы; `postgres_data` — данные БД. Рост зависит от объёма загружаемых документов.

---

## Пример для docker-compose (limits)

```yaml
services:
  postgres:
    deploy:
      resources:
        limits:
          memory: 1G
          cpus: '1'
        reservations:
          memory: 256M

  api:
    deploy:
      resources:
        limits:
          memory: 2G
          cpus: '2'
        reservations:
          memory: 512M

  frontend:
    deploy:
      resources:
        limits:
          memory: 128M
          cpus: '0.25'
```

---

## Порты

- **8000** — API
- **8080** — Frontend (nginx)
- **5433** — PostgreSQL (если пробрасывается на хост)
