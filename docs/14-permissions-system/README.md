# Система прав доступа (Permissions)

## 📋 Обзор

Система прав доступа в проекте реализована на **трёх уровнях**:

1. **Уровень 1: Зависимости FastAPI** (роуты) — быстрая блокировка неавторизованных запросов
2. **Уровень 2: Сервисы** (бизнес-логика) — защита бизнес-логики
3. **Уровень 3: Шаблоны** (UI) — скрытие элементов интерфейса

---

## 🏗️ Архитектура

```
┌─────────────────────────────────────────────────────────────────┐
│                    HTTP Request                                 │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  Уровень 1: FastAPI Dependencies (app/core/auth.py)            │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │ Depends(check_agent_view)                                 │ │
│  │ ├─ get_current_agent() → агент из cookie                  │ │
│  │ ├─ is_admin(agent) → True? → ✅ Пропустить                │ │
│  │ └─ has_permission(agent, Permission) → True? → ✅         │ │
│  └───────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  Уровень 2: Сервисы (app/services/)                            │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │ TicketService.list(agent_id=agent.id)                     │ │
│  │ ├─ self._get_current_agent()                              │ │
│  │ ├─ self._check_permission(can_view_tickets)               │ │
│  │ │   ├─ is_admin(agent) → True? → ✅                       │ │
│  │ │   └─ has_permission(agent, Permission) → True? → ✅     │ │
│  │ └─ Выборка из БД                                          │ │
│  └───────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  Уровень 3: Шаблоны (app/web/jinja/templates/)                 │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │ {% if agent.has_permission('agent_view') %}               │ │
│  │   <a href="/agents">Операторы</a>                         │ │
│  │ {% endif %}                                               │ │
│  └───────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📁 Структура файлов

```
app/
├── core/
│   ├── auth.py              # Зависимости FastAPI для проверок прав
│   └── permissions.py       # Базовые функции проверок (has_permission, is_admin)
├── schemas/
│   └── agent.py             # AgentRead с методами has_permission(), get_permissions_dict()
└── services/
    ├── agent/               # Сервисы агентов с проверками прав
    │   ├── agent_base_service.py
    │   ├── agent_query_service.py
    │   └── ...
    └── ticket/              # Сервисы тикетов с проверками прав
        ├── ticket_base_service.py
        ├── ticket_service.py
        └── ...
```

---

## 🔑 Уровень 1: Зависимости FastAPI (Роуты)

### Файл: `app/core/auth.py`

**Назначение:** Быстрая проверка прав до входа в бизнес-логику.

### Готовые зависимости

| Зависимость | Право | Описание |
|-------------|-------|----------|
| `check_agent_view` | `agent_view` | Просмотр агентов |
| `check_agent_create` | `agent_create` | Создание агентов |
| `check_agent_edit` | `agent_edit` | Редактирование агентов |
| `check_agent_delete` | `agent_delete` | Удаление агентов |
| `check_can_view_tickets` | `can_view_tickets` | Просмотр деталей тикета |
| `check_can_view_own_tickets` | `can_view_own_tickets` | Просмотр списка своих тикетов |
| `check_can_view_unassigned` | `can_view_unassigned` | Просмотр неназначенных тикетов |
| `check_can_view_ass_others` | `can_view_ass_others` | Просмотр чужих тикетов |
| `check_can_reply_tickets` | `can_reply_tickets` | Ответ на тикеты |
| `check_can_edit_tickets` | `can_edit_tickets` | Редактирование тикетов |
| `check_can_del_tickets` | `can_del_tickets` | Удаление тикетов (архив) |
| `check_can_hard_del_tickets` | `can_hard_del_tickets` | Полное удаление |
| `check_audit_logs_view` | `audit_logs_view` | Просмотр логов |

### Пример использования

```python
# app/web/jinja/routes/agents/routes.py

from fastapi import APIRouter, Depends
from app.core.auth import check_agent_view, check_agent_create

router = APIRouter()

@router.get("/agents")
def agents_list(
    agent: AgentRead = Depends(check_agent_view),  # ← Проверка здесь
    db: Session = Depends(get_db),
):
    # Если дошли сюда — право есть
    query_service = AgentQueryService(db, current_agent_id=agent.id)
    return query_service.list()

@router.post("/agents/add")
def add_agent(
    agent: AgentRead = Depends(check_agent_create),  # ← Проверка здесь
    ...
):
    create_service = AgentCreateService(db, current_agent_id=agent.id)
    create_service.create(agent_data)
```

### Механизм работы

```python
# app/core/auth.py

def check_agent_view(request: Request, db: Session = Depends(get_db)) -> AgentRead:
    """
    Проверка права agent_view.
    Администратор всегда проходит проверку.
    """
    # 1. Получить агента из cookie
    agent = get_current_agent(request, db)
    
    # 2. Проверить на админа (универсальная функция)
    if is_admin(agent):
        return agent
    
    # 3. Проверить право (универсальная функция)
    if not has_permission(agent, Permission.agent_view):
        raise AccessDeniedError(
            "Нет прав доступа",
            required_permission="agent_view",
        )
    
    return agent
```

### Обработка ошибок

```python
# app/main.py

@app.exception_handler(AccessDeniedError)
async def access_denied_handler(request: Request, exc: AccessDeniedError):
    """Обработка отказа в доступе."""
    if request.url.path.startswith("/api"):
        # Для API — JSON 403
        return JSONResponse(status_code=403, content={"detail": exc.detail})
    
    # Для HTML — страница 403
    return templates.TemplateResponse(
        "error/access_denied.html",
        {
            "request": request,
            "agent": await get_current_agent_optional(request),
            "required_permission": exc.required_permission,
        },
        status_code=403,
    )
```

---

## ⚙️ Уровень 2: Сервисы (Бизнес-логика)

### Файл: `app/services/agent/agent_base_service.py`

**Назначение:** Защита бизнес-логики на уровне сервисов.

### Базовый класс для сервисов

```python
class AgentBaseService(ABC):
    """Базовый класс для всех сервисов агентов."""
    
    def __init__(self, db: Session, current_agent_id: int | None = None):
        self.db = db
        self.current_agent_id = current_agent_id
        self._current_agent: Agent | None = None
    
    def _get_current_agent(self) -> Agent:
        """Получить текущего агента."""
        if self._current_agent is None:
            self._current_agent = (
                self.db.query(Agent)
                .filter(Agent.id == self.current_agent_id, Agent.is_active == True)
                .one_or_none()
            )
            if not self._current_agent:
                raise ValueError(f"Агент {self.current_agent_id} не найден")
        return self._current_agent
    
    def _check_permission(self, permission: Permission) -> None:
        """
        Проверить право доступа.
        Бросает AccessDeniedError если нет прав.
        """
        agent = self._get_current_agent()
        if not has_permission(agent, permission):
            raise AccessDeniedError(
                detail=f"Нет прав: {permission.value}",
                required_permission=permission.value,
            )
    
    def _has_permission(self, permission: Permission) -> bool:
        """Проверить право (возвращает bool)."""
        agent = self._get_current_agent()
        return has_permission(agent, permission)
```

### Пример использования в сервисе

```python
# app/services/agent/agent_query_service.py

class AgentQueryService(AgentBaseService):
    """Сервис для просмотра агентов (только чтение)."""
    
    def list(
        self,
        filters: dict | None = None,
        sort_by: str = "full_name",
        limit: int = 50,
    ) -> list[AgentRead]:
        """
        Список всех агентов.
        Требуется: agent_view.
        """
        # Проверка права внутри сервиса (двойная защита)
        self._check_permission(Permission.agent_view)
        
        # Бизнес-логика
        query = self.db.query(Agent)
        ...
        return [AgentRead.model_validate(a) for a in agents]
```

### Двойная защита

```python
# Роут (Уровень 1)
@router.get("/agents")
def agents_list(
    agent: AgentRead = Depends(check_agent_view),  # ← Проверка 1
    db: Session = Depends(get_db),
):
    query_service = AgentQueryService(db, current_agent_id=agent.id)
    return query_service.list()  # ← Проверка 2 (внутри сервиса)

# Сервис (Уровень 2)
class AgentQueryService(AgentBaseService):
    def list(self, ...):
        self._check_permission(Permission.agent_view)  # ← Проверка 2
        ...
```

**Зачем двойная защита?**

1. **Защита от забывчивости** — если забудешь `Depends()` в роуте, сервис всё равно проверит
2. **Защита бизнес-логики** — сервисы можно вызывать из CLI/задач, и права всё равно проверятся
3. **Явные ошибки** — `AccessDeniedError` с понятным сообщением

---

## 🎨 Уровень 3: Шаблоны (UI)

### Файл: `app/schemas/agent.py`

**Назначение:** Методы для проверок прав в шаблонах.

### Методы AgentRead

```python
class AgentRead(AgentBase):
    id: int
    full_name: str
    email: str
    role: AgentRole | str  # Поддержка и enum, и строки
    permissions: str = ""  # "perm1,perm2,perm3"
    
    def has_permission(self, permission: Permission) -> bool:
        """
        Проверить наличие права у агента.
        Администратор всегда имеет все права.
        """
        # Админ всегда имеет все права (проверяем и строку, и AgentRole)
        if self.role == AgentRole.admin or str(self.role) == "admin":
            return True
        return permission.value in self._get_permissions_set()
    
    def get_permissions_dict(self) -> dict[str, bool]:
        """
        Вернуть dict {can_permission_name: bool} для всех прав.
        Используется для передачи в шаблоны.
        """
        # Админ всегда имеет все права
        is_admin = self.role == AgentRole.admin or str(self.role) == "admin"
        
        if is_admin:
            return {perm.value: True for perm in Permission}
        
        user_perms = self._get_permissions_set()
        return {perm.value: perm.value in user_perms for perm in Permission}
```

### Пример использования в шаблонах

```html
{# app/web/jinja/templates/base.html #}

<nav>
    {# Показываем ссылку только если есть право #}
    {% if agent.has_permission('agent_view') %}
        <a href="/agents">👥 Операторы</a>
    {% endif %}
    
    {% if agent.has_permission('can_view_tickets') %}
        <a href="/tickets">📋 Тикеты</a>
    {% endif %}
    
    {% if agent.has_permission('audit_logs_view') %}
        <a href="/logs">📊 Логи</a>
    {% endif %}
</nav>
```

### Передача прав в шаблон

```python
# app/web/jinja/routes/agents/routes.py

@router.get("/agents")
def agents_list(
    agent: AgentRead = Depends(check_agent_view),
    db: Session = Depends(get_db),
):
    query_service = AgentQueryService(db, current_agent_id=agent.id)
    agents = query_service.list()
    
    return templates.TemplateResponse(
        "agents/list.html",
        {
            "agent": agent,
            "agents": agents,
            **agent.get_permissions_dict(),  # ← Передаём все права
        },
    )
```

```html
{# app/web/jinja/templates/agents/list.html #}

{% if agent_view %}
  {# Показываем список #}
{% endif %}

{% if agent_create %}
  <a href="/agents/add">➕ Добавить агента</a>
{% endif %}
```

---

## 🔐 Утилиты проверок

### Файл: `app/core/permissions.py`

**Назначение:** Базовые функции для проверок прав.

### Функции

```python
# app/core/permissions.py

def has_permission(agent, permission: Permission) -> bool:
    """
    Проверить наличие права у агента.
    Администратор всегда имеет все права.
    """
    # Админ имеет всё (проверяем и строку, и AgentRole)
    role = getattr(agent, "role", None)
    if role == "admin" or str(role) == "admin":
        return True
    
    if not agent.permissions:
        return False

    user_perms = set(agent.permissions.split(","))
    return permission.value in user_perms


def is_admin(agent) -> bool:
    """Проверить, является ли агент администратором."""
    role = getattr(agent, "role", None)
    return role == "admin" or str(role) == "admin"


def get_agent_permissions(agent) -> set[str]:
    """Получить набор прав агента."""
    if not agent.permissions:
        return set()
    return set(agent.permissions.split(","))
```

---

## 📊 Список всех прав

### Файл: `app/core/permissions.py`

```python
class Permission(str, Enum):
    # Тикеты
    can_view_tickets = "can_view_tickets"
    can_reply_tickets = "can_reply_tickets"
    can_edit_tickets = "can_edit_tickets"
    can_del_tickets = "can_del_tickets"
    can_hard_del_tickets = "can_hard_del_tickets"
    can_merge_tickets = "can_merge_tickets"
    can_resolve = "can_resolve"
    can_change_cat = "can_change_cat"
    can_change_own_cat = "can_change_own_cat"
    can_assign_self = "can_assign_self"
    can_assign_others = "can_assign_others"
    can_view_unassigned = "can_view_unassigned"
    can_view_ass_others = "can_view_ass_others"
    
    # Агенты
    agent_view = "agent_view"
    agent_create = "agent_create"
    agent_edit = "agent_edit"
    agent_delete = "agent_delete"
    
    # Администрирование
    can_man_users = "can_man_users"
    can_man_cat = "can_man_cat"
    can_man_kb = "can_man_kb"
    can_man_settings = "can_man_settings"
    
    # Отчёты
    can_run_reports = "can_run_reports"
    can_run_reports_full = "can_run_reports_full"
    can_export = "can_export"
    
    # Логи
    audit_logs_view = "audit_logs_view"
    
    # ... и другие
```

---

## 🚀 Примеры использования

### Пример 1: Проверка в роуте

```python
from app.core.auth import check_can_view_own_tickets, check_can_view_tickets

# Список своих тикетов (требуется can_view_own_tickets)
@router.get("/tickets/my")
def tickets_my(
    agent: AgentRead = Depends(check_can_view_own_tickets),
    db: Session = Depends(get_db),
):
    # Если дошли сюда — право есть
    ticket_service = TicketService(db, agent_id=agent.id)
    tickets = ticket_service.list(filters={"owner_id": agent.id})
    return ...

# Детали тикета (требуется can_view_tickets)
@router.get("/tickets/{ticket_id}")
def ticket_detail(
    agent: AgentRead = Depends(check_can_view_tickets),
    db: Session = Depends(get_db),
):
    ticket_service = TicketService(db, agent_id=agent.id)
    ticket = ticket_service.get(ticket_id=ticket_id)
    return ...
```

### Пример 2: Проверка в сервисе

```python
from app.services.agent.agent_base_service import AgentBaseService

class AgentQueryService(AgentBaseService):
    def list(self, ...):
        # Проверка права внутри сервиса
        self._check_permission(Permission.agent_view)
        
        # Бизнес-логика
        ...
```

### Пример 3: Проверка в шаблоне

```html
{% if agent.has_permission('agent_create') %}
  <a href="/agents/add" class="btn btn-primary">➕ Добавить агента</a>
{% endif %}
```

### Пример 4: Универсальная проверка

```python
from app.core.permissions import has_permission, is_admin

# В любом месте кода
if is_admin(agent):
    # Админ — можно всё
    ...
elif has_permission(agent, Permission.can_edit_tickets):
    # Есть право на редактирование
    ...
else:
    # Нет прав
    raise AccessDeniedError(...)
```

---

## ⚠️ Важные моменты

### 1. Админ всегда имеет все права

```python
# Проверка работает и для enum, и для строки
if agent.role == AgentRole.admin or str(agent.role) == "admin":
    return True  # Все права есть
```

### 2. Права хранятся как строка

```python
# В БД: agent.permissions = "can_view_tickets,can_reply_tickets"
# Проверка:
user_perms = set(agent.permissions.split(","))
# {"can_view_tickets", "can_reply_tickets"}
```

### 3. AccessDeniedError → HTTP 403

```python
# app/main.py

@app.exception_handler(AccessDeniedError)
async def access_denied_handler(request: Request, exc: AccessDeniedError):
    if request.url.path.startswith("/api"):
        return JSONResponse(status_code=403, content={"detail": exc.detail})
    
    return templates.TemplateResponse("error/access_denied.html", {...}, status_code=403)
```

---

## 📈 Расширение системы

### Добавление нового права

1. **Добавить в Enum:**
   ```python
   # app/core/permissions.py
   class Permission(str, Enum):
       new_permission = "new_permission"
   ```

2. **Добавить зависимость:**
   ```python
   # app/core/auth.py
   def check_new_permission(request: Request, db: Session) -> AgentRead:
       agent = get_current_agent(request, db)
       if is_admin(agent):
           return agent
       if not has_permission(agent, Permission.new_permission):
           raise AccessDeniedError("Нет прав доступа", required_permission="new_permission")
       return agent
   ```

3. **Использовать в роуте:**
   ```python
   @router.get("/new-feature")
   def new_feature(
       agent: AgentRead = Depends(check_new_permission),
       ...
   ):
       ...
   ```

---

## Контакты

По вопросам расширения системы прав доступа обращайтесь к:
- Разработчик: команда разработки
- Дата последнего обновления: 2026-03-27
