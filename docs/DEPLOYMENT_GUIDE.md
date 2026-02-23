# 🚀 Deployment Guide

## Быстрый старт

### Вариант 1: Локальный запуск (Windows)

```bash
start_server.bat
```

Скрипт автоматически:
- ✅ Проверит Python
- ✅ Проверит .env файл
- ✅ Установит зависимости
- ✅ Создаст нужные директории
- ✅ Запустит сервер на порту 8000

### Вариант 2: Локальный запуск (Linux/Mac)

```bash
# Дайте права
chmod +x start_server.sh

# Запустите
./start_server.sh
```

### Вариант 3: Docker (Рекомендуется для продакшена)

```bash
# 1. Создайте .env файл
echo "DEEPSEEK_API_KEY=your-key-here" > .env

# 2. Запустите через Docker Compose
docker-compose up -d

# Готово! Приложение доступно:
# - Frontend: http://localhost:8080
# - API: http://localhost:8000
```

---

## 📋 Требования

### Минимальные:
- Python 3.11+
- 2 GB RAM
- 500 MB свободного места

### Рекомендуемые:
- Python 3.11+
- 4 GB RAM
- 2 GB свободного места
- Docker (для production)

---

## 🔧 Локальная разработка

### 1. Клонируйте репозиторий

```bash
git clone <repository-url>
cd test2
```

### 2. Создайте виртуальное окружение

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# Linux/Mac
source .venv/bin/activate
```

### 3. Установите зависимости

```bash
pip install -r requirements.txt
```

### 4. Настройте .env

```bash
# Создайте .env файл
echo "DEEPSEEK_API_KEY=your-api-key-here" > .env
```

### 5. Запустите сервер

```bash
python api_server.py
```

### 6. Откройте frontend

Откройте `frontend/index.html` в браузере или:

```bash
cd frontend
python -m http.server 8080
```

Перейдите на: `http://localhost:8080`

---

## 🐳 Docker Deployment

### Быстрый старт

```bash
# Создайте .env
echo "DEEPSEEK_API_KEY=your-key" > .env

# Запустите
docker-compose up -d

# Проверьте статус
docker-compose ps

# Логи
docker-compose logs -f

# Остановите
docker-compose down
```

### Что включено в Docker:

1. **API сервер** (port 8000)
   - FastAPI приложение
   - WebSocket для логов
   - Автоматический restart

2. **Frontend** (port 8080)
   - Nginx для статики
   - Proxy для API
   - WebSocket поддержка

3. **Volumes**
   - `./data` - сохраняются результаты
   - `./logs` - логи приложения

### Архитектура Docker:

```
┌──────────────────────────────────┐
│  Browser (localhost:8080)         │
└────────────┬─────────────────────┘
             │
             ↓
┌──────────────────────────────────┐
│  Nginx Frontend Container         │
│  - Serves index.html              │
│  - Proxies /api/ → API            │
│  - Proxies /ws/ → WebSocket       │
└────────────┬─────────────────────┘
             │
             ↓
┌──────────────────────────────────┐
│  FastAPI Backend Container        │
│  - Processes PDF files            │
│  - Calls DeepSeek API             │
│  - Generates Word documents       │
└──────────────────────────────────┘
```


