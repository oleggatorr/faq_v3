# Система прав доступа (Permissions)

## Обзор

Система прав доступа позволяет гибко управлять возможностями операторов и администраторов в системе.

### Основные принципы

1. **Администратор имеет все права** — роль `admin` автоматически предоставляет доступ ко всем функциям
2. **Оператор имеет только назначенные права** — права выдаются через поле `permissions` (строка с разделителями)
3. **Проверка на уровне роутов** — доступ к функциям контролируется через зависимости FastAPI
4. **Проверка на уровне UI** — кнопки и ссылки скрываются, если нет прав

---

## Структура прав

### Список всех прав

Все права определены в `app/core/permissions.py`:

```python
class Permission(str, Enum):
    # Тикеты
    can_view_tickets = "can_view_tickets"          # Просмотр тикетов
    can_reply_tickets = "can_reply_tickets"        # Ответ на тикеты
    can_del_tickets = "can_del_tickets"            # Удаление тикетов
    can_edit_tickets = "can_edit_tickets"          # Редактирование тикетов
    can_merge_tickets = "can_merge_tickets"        # Объединение тикетов
    can_resolve = "can_resolve"                    # Закрытие тикетов
    can_submit_any_cat = "can_submit_any_cat"      # Создание в любых категориях
    
    # Назначение
    can_assign_self = "can_assign_self"            # Назначение себе
    can_assign_others = "can_assign_others"        # Назначение другим
    can_view_unassigned = "can_view_unassigned"    # Просмотр неназначенных
    can_view_ass_others = "can_view_ass_others"    # Просмотр чужих
    
    # Агенты
    agent_view = "agent_view"                      # Просмотр агентов
    agent_create = "agent_create"                  # Создание агентов
    agent_edit = "agent_edit"                      # Редактирование агентов
    agent_delete = "agent_delete"                  # Удаление агентов
    
    # Аудит
    audit_logs_view = "audit_logs_view"            # Просмотр логов
    
    # ... и другие
```

### Наборы прав по умолчанию

```python
# Права оператора по умолчанию
DEFAULT_OPERATOR_PERMISSIONS = [
    Permission.can_view_tickets,
    Permission.can_reply_tickets,
    Permission.can_edit_tickets,
    Permission.can_resolve,
    Permission.can_assign_self,
    Permission.can_view_ass_others,
    Permission.agent_view,
]

# Права только на просмотр
DEFAULT_READONLY_PERMISSIONS = [
    Permission.can_view_tickets,
    Permission.can_view_ass_others,
    Permission.agent_view,
]
```

---

## Проверка прав в коде

### 1. Методы в `AgentRead`

```python
from app.schemas.agent import AgentRead

agent: AgentRead = ...

# Проверка одного права
if agent.has_permission(Permission.can_del_tickets):
    # Удалить тикет

# Проверка любого из прав
if agent.has_any_permission(Permission.agent_edit, Permission.agent_create):
    # Может управлять агентами

# Проверка всех прав
if agent.has_all_permissions(Permission.can_view_tickets, Permission.can_reply_tickets):
    # Может смотреть и отвечать

# Получить все права как dict для шаблона
perms = agent.get_permissions_dict()
# {"can_view_tickets": True, "can_del_tickets": False, ...}
```

### 2. Зависимости в роутах

```python
from app.core.auth import (
    AgentWithTicketView,
    AgentWithTicketDelete,
    require_permission,
)

# Вариант A: Использовать готовый алиас
@router.get("/tickets")
def tickets_list(
    agent: AgentRead = Depends(AgentWithTicketView),
):
    ...

# Вариант B: Создать проверку на лету
@router.post("/tickets/{id}/delete")
def delete_ticket(
    agent: AgentRead = Depends(require_permission(Permission.can_del_tickets)),
):
    ...

# Вариант C: Проверка нескольких прав
@router.post("/complex")
def complex_action(
    agent: AgentRead = Depends(require_permission(
        Permission.can_edit_tickets,
        Permission.can_assign_others
    )),
):
    ...
```

### 3. В шаблонах (Jinja2)

```html
<!-- Кнопка видна только если есть право -->
{% if can_del_tickets %}
  <button type="submit" class="btn-danger">🗑️ Удалить тикет</button>
{% endif %}

<!-- Ссылка видна только если есть право -->
{% if can_agent_edit %}
  <a href="/agents/{{ a.id }}/edit">✏️ Редактировать</a>
{% endif %}

<!-- Форма видна только если есть право -->
{% if can_reply_tickets %}
  <form method="post" action="/tickets/{{ ticket.id }}/reply">
    <textarea name="body"></textarea>
    <button type="submit">Отправить</button>
  </form>
{% endif %}
```

---

## Таблица прав и соответствующих роутов

| Право | Роуты | Шаблоны |
|-------|-------|---------|
| `can_view_tickets` | `GET /tickets`, `GET /tickets/{id}` | Ссылки на тикеты |
| `can_reply_tickets` | `POST /tickets/{id}/reply` | Форма ответа |
| `can_edit_tickets` | `POST /tickets/{id}/update`, `POST /tickets/{id}/restore` | Форма изменения параметров |
| `can_del_tickets` | `POST /tickets/{id}/delete` | Кнопка удаления |
| `agent_view` | `GET /agents` | Список агентов |
| `agent_create` | `GET /agents/add`, `POST /agents/add` | Кнопка "Добавить" |
| `agent_edit` | `GET /agents/{id}/edit`, `POST /agents/{id}/edit` | Кнопка "Редактировать" |
| `agent_delete` | `POST /agents/{id}/delete` | Кнопка "Удалить" |
| `audit_logs_view` | `GET /logs` | Ссылка в меню (только админ) |

---

## Добавление нового права

### Шаг 1: Добавить в `Permission`

```python
# app/core/permissions.py
class Permission(str, Enum):
    # ...
    my_new_permission = "my_new_permission"
```

### Шаг 2: Добавить название

```python
PERMISSION_LABELS = {
    # ...
    Permission.my_new_permission: "Человеко-читаемое название",
}
```

### Шаг 3: Добавить в группу (опционально)

```python
PERMISSION_GROUPS = {
    "Группа": [
        # ...
        Permission.my_new_permission,
    ],
}
```

### Шаг 4: Использовать в роуте

```python
@router.post("/my-action")
def my_action(
    agent: AgentRead = Depends(require_permission(Permission.my_new_permission)),
):
    ...
```

### Шаг 5: Скрыть кнопку в шаблоне

```html
{% if can_my_new_permission %}
  <button>Моё действие</button>
{% endif %}
```

---

## Выдача прав оператору

### Через базу данных

```sql
UPDATE agents 
SET permissions = 'can_view_tickets,can_reply_tickets,can_edit_tickets'
WHERE id = 123;
```

### Через интерфейс редактирования агента

1. Открыть `/agents/{agent_id}/edit`
2. Отметить нужные права в чекбоксах
3. Сохранить

### Через код

```python
from app.core.permissions import DEFAULT_OPERATOR_PERMISSIONS

agent.permissions = ",".join(p.value for p in DEFAULT_OPERATOR_PERMISSIONS)
db.commit()
```

---

## Безопасность

### Что важно помнить

1. **Всегда проверяйте права на уровне роута** — UI можно обойти
2. **Админ всегда проходит проверку** — это заложено в `has_permission()`
3. **Пустое поле `permissions` = нет прав** (кроме админа)
4. **Логируйте отказы в доступе** — для аудита безопасности

### Логирование отказов

```python
from app.services.audit_log_service import AuditLogService
from app.core.audit import get_client_info

# В обработчике 403
@router.post("/secure-action")
def secure_action(
    request: Request,
    agent: AgentRead = Depends(require_permission(Permission.secure_action)),
    db: Session = Depends(get_db),
):
    # Если код здесь, значит право есть
    ...

# Или вручную для сложной логики
@router.post("/complex-action")
def complex_action(request: Request, agent: CurrentAgent, db: Session):
    if not agent.has_permission(Permission.secure_action):
        # Логировать попытку
        log_service = AuditLogService(db)
        log_service.log_action(
            action="permission_denied",
            entity_type="agent",
            entity_id=agent.id,
            details={"required_permission": "secure_action"},
            **get_client_info(request),
        )
        raise HTTPException(403, "Нет прав")
```

---

## Тестирование

### Создать тестовых агентов

```python
# Админ (все права автоматически)
admin = Agent(
    full_name="Admin User",
    login="admin",
    email="admin@example.com",
    role=AgentRole.admin,
    permissions="",  # Не важно для админа
)

# Оператор с правами
operator = Agent(
    full_name="Operator User",
    login="operator",
    email="operator@example.com",
    role=AgentRole.operator,
    permissions="can_view_tickets,can_reply_tickets,can_edit_tickets",
)

# ReadOnly оператор
readonly = Agent(
    full_name="Readonly User",
    login="readonly",
    email="readonly@example.com",
    role=AgentRole.readonly,
    permissions="can_view_tickets",
)
```

### Проверить в браузере

1. Войти как оператор без права `can_del_tickets`
2. Убедиться, что кнопка "Удалить" не отображается
3. Попробовать отправить `POST /tickets/{id}/delete` → должен быть `403`

---

## Структура файлов

```
app/
├── core/
│   ├── auth.py              # require_permission(), алиасы
│   └── permissions.py       # Permission enum, ALL_PERMISSIONS, наборы
├── schemas/
│   └── agent.py             # AgentRead.has_permission(), get_permissions_dict()
└── web/jinja/
    └── routes/
        ├── tickets/
        │   └── admin.py     # AgentWithTicketView, etc.
        ├── agents/
        │   └── routes.py    # AgentWithAgentView, etc.
        └── logs.py          # AgentWithAuditLogsView
```

---

## Контакты

По вопросам добавления прав и настройки доступа:
- Разработчик: команда разработки
- Дата последнего обновления: 2026-03-25
- Статус: ✅ Реализовано
