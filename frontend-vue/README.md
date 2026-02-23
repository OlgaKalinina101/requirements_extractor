# Frontend - Vue 3 Requirements Management System

Vue 3 frontend для системы управления требованиями.

## Установка

```bash
cd frontend-vue
npm install
```

## Запуск в режиме разработки

```bash
npm run dev
```

Приложение будет доступно на http://localhost:3000

## Сборка для production

```bash
npm run build
```

Собранные файлы будут в папке `dist/`

## Структура проекта

```
src/
├── components/          # Vue компоненты
│   ├── DocumentUpload.vue
│   ├── ProcessingStatus.vue
│   ├── RequirementsList.vue
│   └── RequirementCard.vue
├── views/              # Страницы
│   ├── HomeView.vue
│   └── ReviewView.vue
├── stores/             # Pinia stores
│   ├── documents.js
│   └── requirements.js
├── services/           # API клиенты
│   └── api.js
├── router/             # Vue Router
│   └── index.js
├── App.vue             # Root component
└── main.js             # Entry point
```

## API Endpoints

Frontend использует следующие endpoints:

- `GET /api/documents` - список документов
- `GET /api/documents/{id}` - получить документ
- `POST /api/extract` - загрузить и обработать PDF
- `GET /api/documents/{id}/requirements` - получить требования
- `POST /api/requirements/{id}/accept` - принять требование
- `POST /api/requirements/{id}/reject` - отклонить требование
- `POST /api/requirements/{id}/edit` - редактировать требование
- `WS /ws/logs` - WebSocket для real-time обновлений

## Переменные окружения

Создайте файл `.env`:

```
VITE_API_URL=http://localhost:8000
VITE_WS_URL=ws://localhost:8000/ws/logs
```
