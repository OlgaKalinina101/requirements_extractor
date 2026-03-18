# Авторизация и регистрация пользователей

Документ описывает, как устроена аутентификация и управление пользователями в проекте.

---

## Обзор

- **Регистрация:** отсутствует публичная регистрация. Пользователей создаёт только администратор.
- **Вход:** по email и паролю. Возвращается JWT-токен.
- **Хранение паролей:** хеш bcrypt в БД. Пароли в открытом виде не хранятся.
- **Передача:** пароль передаётся в теле запроса (JSON) по HTTPS. Токен — в заголовке `Authorization: Bearer <token>`.

---

## Хранение паролей

### Где хранятся

- **Таблица:** `users`
- **Поле:** `hashed_password` (VARCHAR 255)
- **Формат:** bcrypt-хеш (строка вида `$2b$12$...`)

### Как хешируются

- **Библиотека:** `bcrypt`
- **Файл:** `src/auth/password.py`
- **Функции:**
  - `hash_password(plain: str) -> str` — хеширует пароль с `bcrypt.gensalt(rounds=12)`
  - `verify_password(plain: str, hashed: str) -> bool` — проверяет пароль через `bcrypt.checkpw`

Пароли в открытом виде **никогда** не сохраняются в БД.

---

## Передача паролей и токенов

### При входе (POST /api/auth/login)

1. Клиент отправляет JSON: `{ "email": "...", "password": "..." }`
2. Передача по HTTPS — пароль шифруется на уровне TLS
3. Сервер проверяет email, получает пользователя из БД, сравнивает пароль через `verify_password`
4. При успехе возвращает:
   ```json
   {
     "access_token": "<JWT>",
     "token_type": "bearer",
     "user": { "id", "email", "full_name", "role" }
   }
   ```

### При создании пользователя (POST /api/users)

1. Только администратор. Запрос: `{ "email", "password", "full_name", "role" }`
2. Пароль хешируется через `hash_password()` и сохраняется в `hashed_password`
3. В ответе пользователь возвращается **без** поля пароля (сериализатор его не отдаёт)

### При смене пароля (PUT /api/users/{id})

1. Только администратор. В теле может быть `"password": "новый_пароль"`
2. Если поле передано — пароль хешируется и обновляется в БД

### Использование токена

- Клиент сохраняет токен в `localStorage` (ключ `token`)
- Каждый запрос к API: заголовок `Authorization: Bearer <token>`
- Сервер извлекает токен, проверяет подпись и срок действия, получает `user_id` из payload

---

## JWT-токены

### Конфигурация

- **Файл:** `src/auth/jwt.py`
- **Алгоритм:** HS256
- **Секрет:** `SECRET_KEY` из переменной окружения (по умолчанию `dev-secret-change-in-production`)
- **Время жизни:** `ACCESS_TOKEN_EXPIRE_MINUTES` из env (по умолчанию 60 минут)

### Содержимое токена

- `sub` — ID пользователя (строка)
- `exp` — время истечения
- `iat` — время создания

### Проверка

- `verify_token(token) -> dict | None` — декодирует и проверяет подпись
- При невалидном или истёкшем токене возвращает `None` → 401 Unauthorized

---

## Зависимости авторизации (Backend)

- **Файл:** `src/auth/dependencies.py`
- **`get_current_user`** — извлекает токен из `Authorization`, проверяет, загружает пользователя из БД, проверяет `is_active`
- **`require_role(allowed_roles)`** — проверяет, что `current_user.role` входит в список
- **`require_admin`** — `require_role(["admin"])`
- **`require_manager`** — `require_role(["admin", "manager", "department_head"])`

---

## Хранение на клиенте (Frontend)

- **Store:** `frontend-vue/src/stores/auth.js` (Pinia)
- **localStorage:**
  - `token` — JWT
  - `user` — JSON с `{ id, email, full_name, role }`
- При 401 ответе API: очистка `token` и `user`, редирект на `/login`

---

## Создание администратора по умолчанию

При старте приложения (`src/api/app.py`, `_seed_admin_if_needed`):

1. Читаются переменные окружения:
   - `ADMIN_EMAIL` (по умолчанию `admin@example.com`)
   - `ADMIN_PASSWORD` (по умолчанию `changeme`)
   - `ADMIN_NAME` (по умолчанию `Администратор`)
2. Если пользователь с таким email уже есть — обновляется пароль
3. Если нет — создаётся новый пользователь с ролью `admin`

> **Важно:** В production обязательно задать `ADMIN_PASSWORD` и `SECRET_KEY` через переменные окружения.

---

## Схема потока входа

```
[Клиент]                    [API]
   |                           |
   |  POST /api/auth/login     |
   |  { email, password }     |
   |------------------------->|
   |                           |  get_user_by_email()
   |                           |  verify_password()
   |                           |  create_access_token()
   |  { access_token, user }   |
   |<-------------------------|
   |                           |
   |  localStorage.setItem     |
   |  (token, user)            |
   |                           |
   |  GET /api/...             |
   |  Authorization: Bearer X  |
   |------------------------->|
   |                           |  verify_token()
   |                           |  get_current_user()
   |  { data }                 |
   |<-------------------------|
```

---

## Безопасность

| Аспект | Реализация |
|--------|------------|
| Хранение паролей | bcrypt, 12 раундов |
| Передача пароля | HTTPS (TLS) |
| Токены | JWT, HS256, ограниченный срок жизни |
| Секрет JWT | Переменная окружения `SECRET_KEY` |
| Деактивация | Поле `is_active`; при `false` вход запрещён |

### Рекомендации для production

1. Использовать HTTPS
2. Задать `SECRET_KEY` — длинная случайная строка
3. Задать `ADMIN_PASSWORD` — надёжный пароль
4. Уменьшить `ACCESS_TOKEN_EXPIRE_MINUTES` при необходимости
5. Рассмотреть добавление refresh-токенов для длительных сессий
