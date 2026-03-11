# План: Аутентификация и роли

## Фаза 0 — Подготовка (миграции, модели)

1. **Модель User в БД**
   - Таблица `users`: id, email (unique), hashed_password, full_name, role, is_active, created_at
   - Роли: `admin`, `manager`, `user`
   - Alembic миграция 006

2. **Расширение Requirement**
   - Поле `assignee_id` (FK → users.id, nullable)
   - Alembic миграция 007

3. **Таблица comments**
   - id, requirement_id, user_id, text, created_at
   - Alembic миграция 008

4. **Расширение статусов requirement**
   - Добавить: `in_progress`, `done`, `blocked` (или отдельная таблица execution_status — решим по ходу)

---

## Фаза 1 — Backend: JWT и базовый auth

5. **JWT-модуль**
   - `src/auth/jwt.py`: create_access_token, verify_token, get_current_user
   - Зависимость от env: SECRET_KEY, ACCESS_TOKEN_EXPIRE_MINUTES

6. **Эндпоинты auth**
   - `POST /api/auth/login` — email + password → JWT
   - `GET /api/auth/me` — текущий пользователь (для проверки токена)
   - `POST /api/auth/logout` — опционально (клиент просто удаляет токен)

7. **Password hashing**
   - passlib + bcrypt в requirements.txt
   - Функция hash_password / verify_password

8. **CRUD для User**
   - create_user, get_user_by_email, get_user_by_id, list_users, update_user
   - Только admin может создавать/редактировать пользователей

---

## Фаза 2 — Backend: RBAC и защита эндпоинтов

9. **Dependencies по ролям**
   - `require_role(["admin", "manager"])` — для эндпоинтов менеджера
   - `require_role(["admin"])` — для админских эндпоинтов
   - `get_current_user` — базовый, возвращает User или 401

10. **Защита существующих эндпоинтов**
    - POST /api/projects, POST /api/extract, PUT/DELETE проектов — manager+
    - GET /api/projects, GET /api/documents, GET /api/requirements — любой авторизованный
    - AdminView-эндпоинты (если появятся) — admin only

11. **Эндпоинты управления пользователями (admin)**
    - POST /api/users — создание (admin)
    - GET /api/users — список (admin)
    - PUT /api/users/{id} — редактирование роли/активности (admin)

---

## Фаза 3 — Backend: Assignee, статусы, комментарии

12. **Assignee**
    - POST /api/requirements/{id}/assign — body: { assignee_id }
    - GET /api/documents/{id}/requirements?assignee_id=me — фильтр "мои"

13. **Статусы выполнения**
    - PATCH /api/requirements/{id}/status — body: { status: "in_progress" | "done" | "blocked" }
    - Проверка: только assignee или manager может менять

14. **Комментарии**
    - POST /api/requirements/{id}/comments — body: { text }
    - GET /api/requirements/{id}/comments — список
    - Модель Comment, CRUD

---

## Фаза 4 — Frontend: Login и хранение токена

15. **LoginView**
    - Страница /login с формой email + password
    - Вызов POST /api/auth/login
    - Сохранение token в localStorage
    - Редирект на / после успеха

16. **Axios interceptor**
    - Добавить Authorization: Bearer {token} ко всем запросам
    - При 401 — редирект на /login и очистка токена

17. **Route guard**
    - Если нет токена и маршрут защищён — редирект на /login
    - Исключение: /login доступен без токена

18. **Кнопка Logout**
    - В AppBar: если авторизован — показать имя + "Выйти"
    - Очистка localStorage, редирект на /login

---

## Фаза 5 — Frontend: Роли и UI

19. **Store auth**
    - Pinia store: user, token, login(), logout(), fetchMe()
    - При загрузке приложения — проверка токена, fetchMe()

20. **Скрытие по ролям**
    - "Создать проект", "Загрузить документ" — только manager/admin
    - Admin в меню — только admin
    - Accept/Reject/Edit в Review — только manager/admin

21. **Assignee в карточке требования**
    - Дропдаун выбора исполнителя (RequirementCard, RequirementDetailView)
    - Показывать аватар/имя назначенного

22. **Фильтр "Мои требования"**
    - Чекбокс в ReviewView
    - Передаёт assignee_id=me в API

23. **Смена статуса (исполнитель)**
    - Кнопки или селект: В работе / Готово / Заблокировано
    - Видно только назначенному

24. **Комментарии**
    - Секция в RequirementDetailView
    - Список комментариев + форма добавления

---

## Фаза 6 — DevOps и первый admin

25. **Seed admin**
    - Скрипт scripts/create_admin.py или env ADMIN_EMAIL/ADMIN_PASSWORD
    - При первом запуске создать admin если users пуст

26. **Env переменные**
    - SECRET_KEY, ACCESS_TOKEN_EXPIRE_MINUTES в .env.example
    - Обновить docker-compose

---

## Порядок выполнения (рекомендуемый)

```
Фаза 0 (модели) → Фаза 1 (JWT, login API) → Фаза 4 (Login UI, interceptor)
    → Фаза 2 (RBAC) → Фаза 5 (роли в UI)
    → Фаза 3 (assignee, статусы, комментарии) → Фаза 5 (остальное)
    → Фаза 6 (seed admin)
```

Можно начинать с Фазы 0.
