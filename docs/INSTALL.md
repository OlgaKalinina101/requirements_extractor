# Установка зависимостей

## Быстрая установка

```bash
pip install -r requirements.txt
```

## Что установится

### Основные зависимости:
- **pymupdf** - обработка PDF файлов
- **pymupdf4llm** - извлечение текста и изображений из PDF
- **requests** - HTTP клиент для OpenRouter API
- **tenacity** - retry логика для надежных API вызовов
- **fastapi** - веб-фреймворк для API
- **uvicorn** - ASGI сервер
- **pydantic** - валидация данных
- **python-docx** - генерация Word документов
- **python-dotenv** - загрузка переменных окружения

## Настройка окружения

1. Скопируй `.env.example` в `.env`:
   ```bash
   cp .env.example .env
   ```

2. Добавь свой OpenRouter API ключ в `.env`:
   ```
   OPENROUTER_API_KEY=sk-or-v1-твой-ключ-здесь
   ```

3. Получи ключ на: https://openrouter.ai/keys

## Запуск

```bash
python api_server.py
```

Сервер запустится на `http://localhost:8000`

Frontend доступен в `frontend/index.html` (открой в браузере)