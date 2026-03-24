# Аутентификация

## Структура

- **`app/core/config.py`** — настройки (SECRET_KEY, время жизни cookie и т.п.)
- **`app/core/security.py`** — хэширование паролей, JWT (создание/проверка токена)
- **`app/core/auth.py`** — зависимости FastAPI для проверки авторизации

## Публичные маршруты (без входа)

- `/` — главная
- `/login` — страница входа
- `POST /login` — отправка формы входа
- `POST /logout` — выход

## Защищённые маршруты (требуют авторизации)

- `/tickets`, `/tickets/{id}`
- `/agents`, `/departments`, `/lookups/languages`

При обращении без авторизации: для HTML — редирект на `/login?next=...`, для API (`/api/*`) — JSON 401.

## Использование в роутах

```python
from app.core.auth import CurrentAgent, CurrentAgentOptional, require_roles
from app.models.agent import AgentRole

# Обязательная авторизация
@router.get("/tickets")
def tickets_list(agent: CurrentAgent, ...):
    ...

# Опционально (есть agent, если залогинен)
@router.get("/")
def index(agent: CurrentAgentOptional):
    ...

# С проверкой роли
@router.get("/admin")
def admin_only(agent: CurrentAgent = Depends(require_roles(AgentRole.admin))):
    ...
```

## Переменные окружения

| Переменная | Описание | По умолчанию |
|------------|----------|--------------|
| `SECRET_KEY` | Ключ для JWT | `change-me-in-production-use-env` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Время жизни токена (минуты) | `60` |
| `AUTH_COOKIE_NAME` | Имя cookie сессии | `session` |
| `AUTH_COOKIE_MAX_AGE` | Время жизни cookie (секунды) | `86400` (24ч) |

## Создание первого оператора

Пароль хранится как bcrypt-хэш. Пример создания пользователя в Python:

```python
from app.core.security import hash_password
from app.models import SessionLocal
from app.models.agent import Agent, AgentRole

db = SessionLocal()
agent = Agent(
    full_name="Администратор",
    email="admin@example.com",
    password_hash=hash_password("your-password"),
    role=AgentRole.admin,
)
db.add(agent)
db.commit()
```
