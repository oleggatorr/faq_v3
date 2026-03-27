# Контракты сервисов — полная документация

## � Навигация по документации

### Сервисы агентов
- [`AgentQueryService`](#agentqueryservice) — просмотр агентов (списки, детали)
- [`AgentCreateService`](#agentcreateservice) — создание агентов
- [`AgentEditService`](#agenteditservice) — редактирование агентов
- [`AgentDeleteService`](#agentdeleteservice) — удаление агентов

### Сервисы тикетов
- [`TicketService`](#ticketservice) — CRUD тикетов + бизнес-логика
- [`TicketEventService`](#ticketeventservice) — события тикетов (audit log)
- [`MessageService`](#messageservice) — сообщения и примечания
- [`AttachmentService`](#attachmentservice) — вложения

### Система прав доступа
- [Права и зависимости](#права-и-зависимости)
- [Уровни проверок](#уровни-проверок)

---

## �📁 Модуль агентов (`app/services/agent_*`)

---

### AgentQueryService

**Файл:** `app/services/agent_query_service.py`

**Назначение:** Чтение данных агентов (списки, детали).

| Метод | Вход | Выход | Описание |
|-------|------|-------|----------|
| `list(filters, sort_by, sort_desc, limit, offset)` | `filters: dict \| None`<br>`sort_by: str` (default: `"full_name"`)<br>`sort_desc: bool` (default: `False`)<br>`limit: int` (default: `50`)<br>`offset: int` (default: `0`) | `list[AgentRead]` | Список агентов с фильтрами и пагинацией |
| `get(agent_id)` | `agent_id: int` | `AgentRead` | Детали конкретного агента |
| `get_current()` | — | `AgentRead` | Получить текущего агента |
| `list_by_department(department_id)` | `department_id: int` | `list[AgentRead]` | Агенты департамента |
| `list_active()` | — | `list[AgentRead]` | Только активные агенты |
| `search(query, limit)` | `query: str`<br>`limit: int` (default: `20`) | `list[AgentRead]` | Поиск по имени/email |

**Как вызвать:**
```python
from app.services import AgentQueryService

service = AgentQueryService(db, current_agent_id=agent.id)

# Список с фильтрами
agents = service.list(
    filters={"is_active": True, "department_id": 5},
    sort_by="full_name",
    limit=50,
)

# Детали
agent_details = service.get(agent_id=5)

# Поиск
results = service.search(query="Иванов")
```

**Требуемые права:** `agent_view` (для всех методов кроме `get_current()`)

---

### AgentCreateService

**Файл:** `app/services/agent_create_service.py`

**Назначение:** Создание новых агентов.

| Метод | Вход | Выход | Описание |
|-------|------|-------|----------|
| `create(agent_data, created_by_agent_id)` | `agent_data: AgentCreate`<br>`created_by_agent_id: int \| None` | `AgentRead` | Создать агента |
| `create_with_defaults(agent_data, created_by_agent_id)` | `agent_data: AgentCreate`<br>`created_by_agent_id: int \| None` | `AgentRead` | Создать с правами по умолчанию |

**Как вызвать:**
```python
from app.services import AgentCreateService
from app.schemas.agent import AgentCreate

service = AgentCreateService(db, current_agent_id=agent.id)

agent_data = AgentCreate(
    full_name="Иванов Иван",
    email="ivanov@example.com",
    password="SecurePass123",
    role="operator",
    department_id=5,
)

new_agent = service.create(agent_data)
```

**Требуемые права:** `agent_create`

---

### AgentEditService

**Файл:** `app/services/agent_edit_service.py`

**Назначение:** Редактирование данных агента.

| Метод | Вход | Выход | Описание |
|-------|------|-------|----------|
| `update(agent_id, agent_data, updated_by_agent_id)` | `agent_id: int`<br>`agent_data: AgentUpdate`<br>`updated_by_agent_id: int \| None` | `AgentRead` | Обновить все поля |
| `update_profile(agent_id, full_name, phone, updated_by_agent_id)` | `agent_id: int`<br>`full_name: str \| None`<br>`phone: str \| None`<br>`updated_by_agent_id: int \| None` | `AgentRead` | Обновить профиль |
| `update_email(agent_id, new_email, updated_by_agent_id)` | `agent_id: int`<br>`new_email: str`<br>`updated_by_agent_id: int \| None` | `AgentRead` | Сменить email |
| `change_password(agent_id, new_password, updated_by_agent_id)` | `agent_id: int`<br>`new_password: str`<br>`updated_by_agent_id: int \| None` | `bool` | Сменить пароль |

**Как вызвать:**
```python
from app.services import AgentEditService
from app.schemas.agent import AgentUpdate

service = AgentEditService(db, current_agent_id=agent.id)

# Обновление данных
update_data = AgentUpdate(
    full_name="Новое Имя",
    email="new@example.com",
    phone="+1234567890",
)
updated = service.update(agent_id=5, agent_data=update_data)

# Смена пароля
service.change_password(agent_id=5, new_password="NewPass123")
```

**Требуемые права:** `agent_edit`

---

### AgentDeleteService

**Файл:** `app/services/agent_delete_service.py`

**Назначение:** Удаление агентов.

| Метод | Вход | Выход | Описание |
|-------|------|-------|----------|
| `delete(agent_id, deleted_by_agent_id)` | `agent_id: int`<br>`deleted_by_agent_id: int \| None` | `bool` | Удалить агента |
| `bulk_delete(agent_ids, deleted_by_agent_id)` | `agent_ids: list[int]`<br>`deleted_by_agent_id: int \| None` | `dict` | Массовое удаление |
| `can_delete(agent_id)` | `agent_id: int` | `bool` | Проверка возможности удаления |

**Как вызвать:**
```python
from app.services import AgentDeleteService

service = AgentDeleteService(db, current_agent_id=agent.id)

# Удаление
deleted = service.delete(agent_id=5, deleted_by_agent_id=agent.id)

# Проверка
if service.can_delete(agent_id=5):
    service.delete(agent_id=5, deleted_by_agent_id=agent.id)

# Массовое
results = service.bulk_delete(
    agent_ids=[1, 2, 3],
    deleted_by_agent_id=agent.id,
)
# {"deleted": [1, 2], "failed": [{"id": 3, "reason": "..."}]}
```

**Требуемые права:** `agent_delete`

---

### AgentPrivacyService

**Файл:** `app/services/agent_privacy_service.py`

**Назначение:** Управление приватностью и доступом.

| Метод | Вход | Выход | Описание |
|-------|------|-------|----------|
| `update_privacy(agent_id, is_active, category_access, permissions, updated_by_agent_id)` | `agent_id: int`<br>`is_active: bool \| None`<br>`category_access: str \| None`<br>`permissions: str \| None`<br>`updated_by_agent_id: int \| None` | `AgentRead` | Обновить настройки |
| `activate(agent_id, updated_by_agent_id)` | `agent_id: int`<br>`updated_by_agent_id: int \| None` | `AgentRead` | Активировать |
| `deactivate(agent_id, updated_by_agent_id)` | `agent_id: int`<br>`updated_by_agent_id: int \| None` | `AgentRead` | Деактивировать |
| `update_category_access(agent_id, categories, updated_by_agent_id)` | `agent_id: int`<br>`categories: list[str] \| str`<br>`updated_by_agent_id: int \| None` | `AgentRead` | Изменить категории |
| `update_permissions(agent_id, permissions, updated_by_agent_id)` | `agent_id: int`<br>`permissions: list[Permission] \| str`<br>`updated_by_agent_id: int \| None` | `AgentRead` | Изменить права |

**Как вызвать:**
```python
from app.services import AgentPrivacyService
from app.core.permissions import Permission

service = AgentPrivacyService(db, current_agent_id=agent.id)

# Деактивировать
service.deactivate(agent_id=5)

# Изменить права
service.update_permissions(
    agent_id=5,
    permissions=[Permission.can_view_tickets, Permission.can_reply_tickets],
)
```

**Требуемые права:** `can_privacy`

---

### AgentRoleService

**Файл:** `app/services/agent_role_service.py`

**Назначение:** Изменение роли агента.

| Метод | Вход | Выход | Описание |
|-------|------|-------|----------|
| `change_role(agent_id, new_role, updated_by_agent_id)` | `agent_id: int`<br>`new_role: str \| AgentRole`<br>`updated_by_agent_id: int \| None` | `AgentRead` | Изменить роль |
| `promote_to_admin(agent_id, updated_by_agent_id)` | `agent_id: int`<br>`updated_by_agent_id: int \| None` | `AgentRead` | Повысить до админа |
| `demote_to_operator(agent_id, updated_by_agent_id)` | `agent_id: int`<br>`updated_by_agent_id: int \| None` | `AgentRead` | Понизить до оператора |

**Как вызвать:**
```python
from app.services import AgentRoleService
from app.models.agent import AgentRole

service = AgentRoleService(db, current_agent_id=agent.id)

# Изменить роль
service.change_role(agent_id=5, new_role="admin")

# Повысить
service.promote_to_admin(agent_id=5)
```

**Требуемые права:** `can_man_users`

---

### AgentPermissionService

**Файл:** `app/services/agent_permission_service.py`

**Назначение:** Управление правами агента.

| Метод | Вход | Выход | Описание |
|-------|------|-------|----------|
| `update_permissions(agent_id, permissions, updated_by_agent_id)` | `agent_id: int`<br>`permissions: list[Permission] \| str`<br>`updated_by_agent_id: int \| None` | `AgentRead` | Установить права |
| `add_permission(agent_id, permission, updated_by_agent_id)` | `agent_id: int`<br>`permission: Permission`<br>`updated_by_agent_id: int \| None` | `AgentRead` | Добавить право |
| `remove_permission(agent_id, permission, updated_by_agent_id)` | `agent_id: int`<br>`permission: Permission`<br>`updated_by_agent_id: int \| None` | `AgentRead` | Отозвать право |
| `reset_to_defaults(agent_id, updated_by_agent_id)` | `agent_id: int`<br>`updated_by_agent_id: int \| None` | `AgentRead` | Сбросить к умолчанию |

**Как вызвать:**
```python
from app.services import AgentPermissionService
from app.core.permissions import Permission

service = AgentPermissionService(db, current_agent_id=agent.id)

# Установить права
service.update_permissions(
    agent_id=5,
    permissions=[Permission.can_view_tickets, Permission.can_reply_tickets],
)

# Добавить право
service.add_permission(agent_id=5, permission=Permission.can_edit_tickets)
```

**Требуемые права:** `can_man_users`

---

## 📁 Модуль тикетов (`app/services/ticket/`)

### Навигация
- [`TicketService`](#ticketservice) — CRUD тикетов + бизнес-логика
- [`TicketEventService`](#ticketeventservice) — события тикетов (audit log)
- [`MessageService`](#messageservice) — сообщения и примечания
- [`AttachmentService`](#attachmentservice) — вложения

---

### TicketService

**Файл:** `app/services/ticket/ticket_service.py`

**Назначение:** CRUD тикетов + бизнес-логика (создание, редактирование, удаление, проверка прав).

| Метод | Вход | Выход | Описание |
|-------|------|-------|----------|
| `list(filters, sort_by, sort_desc, limit, offset)` | `filters: dict \| None`<br>`sort_by: str` (default: `"created_at"`)<br>`sort_desc: bool` (default: `False`)<br>`limit: int` (default: `50`)<br>`offset: int` (default: `0`) | `list[TicketRead]` | Список тикетов |
| `get(ticket_id)` | `ticket_id: int` | `TicketRead` | Детали тикета |
| `get_by_track_id(track_id)` | `track_id: str` | `TicketRead` | Поиск по трек-номеру |
| `list_unassigned(filters, limit)` | `filters: dict \| None`<br>`limit: int` (default: `50`) | `list[TicketRead]` | Неназначенные тикеты |
| `list_assigned_to_me(filters, limit)` | `filters: dict \| None`<br>`limit: int` (default: `50`) | `list[TicketRead]` | Назначенные себе |
| `list_assigned_to_others(filters, limit)` | `filters: dict \| None`<br>`limit: int` (default: `50`) | `list[TicketRead]` | Назначенные другим |
| `list_by_agent(agent_id, filters, limit)` | `agent_id: int`<br>`filters: dict \| None`<br>`limit: int` (default: `50`) | `list[TicketRead]` | Назначенные агенту |

**Как вызвать:**
```python
from app.services.ticket import TicketQueryService

service = TicketQueryService(db, agent_id=agent.id)

# Все тикеты
tickets = service.list(
    filters={"status_id": 1, "priority": "high"},
    sort_by="created_at",
    limit=50,
)

# Неназначенные
unassigned = service.list_unassigned(limit=20)

# Назначенные мне
my_tickets = service.list_assigned_to_me()
```

**Требуемые права:** `can_view_tickets` (или специфичные для каждого метода)

---

### TicketReplyService

**Файл:** `app/services/ticket/ticket_reply_service.py`

**Назначение:** Ответы на тикеты.

| Метод | Вход | Выход | Описание |
|-------|------|-------|----------|
| `reply(ticket_id, body, is_internal, attachments)` | `ticket_id: int`<br>`body: str`<br>`is_internal: bool` (default: `False`)<br>`attachments: list \| None` | `MessageRead` | Ответ на тикет |
| `add_internal_note(ticket_id, body)` | `ticket_id: int`<br>`body: str` | `MessageRead` | Внутренняя заметка |

**Как вызвать:**
```python
from app.services.ticket import TicketReplyService

service = TicketReplyService(db, agent_id=agent.id)

# Ответ клиенту
service.reply(
    ticket_id=123,
    body="Ваш вопрос решён...",
    is_internal=False,
)

# Внутренняя заметка
service.add_internal_note(
    ticket_id=123,
    body="Клиент звонил, уточнил...",
)
```

**Требуемые права:** `can_reply_tickets` (внешние), `can_view_tickets` (внутренние)

---

### TicketEditService

**Файл:** `app/services/ticket/ticket_edit_service.py`

**Назначение:** Редактирование полей тикета.

| Метод | Вход | Выход | Описание |
|-------|------|-------|----------|
| `update_subject(ticket_id, new_subject)` | `ticket_id: int`<br>`new_subject: str` | `Ticket` | Изменить тему |
| `update_customer_name(ticket_id, new_name)` | `ticket_id: int`<br>`new_name: str` | `Ticket` | Имя заявителя |
| `update_customer_email(ticket_id, new_email)` | `ticket_id: int`<br>`new_email: str` | `Ticket` | Email заявителя |
| `update_multiple(ticket_id, updates)` | `ticket_id: int`<br>`updates: dict` | `Ticket` | Массовое обновление |

**Как вызвать:**
```python
from app.services.ticket import TicketEditService

service = TicketEditService(db, agent_id=agent.id)

# Изменение темы
service.update_subject(ticket_id=123, new_subject="Новая тема")

# Массовое обновление
service.update_multiple(
    ticket_id=123,
    updates={"subject": "Новая тема", "customer_email": "new@example.com"},
)
```

**Требуемые права:** `can_edit_tickets`

---

### TicketResolveService

**Файл:** `app/services/ticket/ticket_resolve_service.py`

**Назначение:** Закрытие тикетов.

| Метод | Вход | Выход | Описание |
|-------|------|-------|----------|
| `resolve(ticket_id, resolution_comment)` | `ticket_id: int`<br>`resolution_comment: str \| None` | `Ticket` | Закрыть как решённый |
| `reopen(ticket_id)` | `ticket_id: int` | `Ticket` | Открыть заново |

**Как вызвать:**
```python
from app.services.ticket import TicketResolveService

service = TicketResolveService(db, agent_id=agent.id)

# Закрыть
service.resolve(
    ticket_id=123,
    resolution_comment="Проблема решена обновлением ПО",
)

# Открыть заново
service.reopen(ticket_id=123)
```

**Требуемые права:** `can_resolve`

---

### TicketCategoryService

**Файл:** `app/services/ticket/ticket_category_service.py`

**Назначение:** Изменение категории.

| Метод | Вход | Выход | Описание |
|-------|------|-------|----------|
| `change(ticket_id, new_category_id)` | `ticket_id: int`<br>`new_category_id: int` | `Ticket` | Изменить категорию |
| `change_own_category(ticket_id, new_category_id)` | `ticket_id: int`<br>`new_category_id: int` | `Ticket` | Изменить свою категорию |

**Как вызвать:**
```python
from app.services.ticket import TicketCategoryService

service = TicketCategoryService(db, agent_id=agent.id)

service.change(ticket_id=123, new_category_id=5)
```

**Требуемые права:** `can_change_cat` или `can_change_own_cat`

---

### TicketAssignmentService

**Файл:** `app/services/ticket/ticket_assignment_service.py`

**Назначение:** Назначение исполнителей.

| Метод | Вход | Выход | Описание |
|-------|------|-------|----------|
| `assign_to_self(ticket_id)` | `ticket_id: int` | `Ticket` | Назначить себе |
| `assign_to_others(ticket_id, new_owner_id)` | `ticket_id: int`<br>`new_owner_id: int` | `Ticket` | Назначить другому |
| `unassign(ticket_id)` | `ticket_id: int` | `Ticket` | Снять назначение |
| `reassign(ticket_id, from_agent_id, to_agent_id)` | `ticket_id: int`<br>`from_agent_id: int`<br>`to_agent_id: int` | `Ticket` | Переназначить |

**Как вызвать:**
```python
from app.services.ticket import TicketAssignmentService

service = TicketAssignmentService(db, agent_id=agent.id)

# Назначить себе
service.assign_to_self(ticket_id=123)

# Назначить другому
service.assign_to_others(ticket_id=123, new_owner_id=456)
```

**Требуемые права:** `can_assign_self` или `can_assign_others`

---

### TicketMergeService

**Файл:** `app/services/ticket/ticket_merge_service.py`

**Назначение:** Объединение тикетов.

| Метод | Вход | Выход | Описание |
|-------|------|-------|----------|
| `merge(source_ticket_id, target_ticket_id)` | `source_ticket_id: int`<br>`target_ticket_id: int` | `Ticket` | Объединить тикеты |
| `can_merge(source_id, target_id)` | `source_id: int`<br>`target_id: int` | `bool` | Проверка возможности |

**Как вызвать:**
```python
from app.services.ticket import TicketMergeService

service = TicketMergeService(db, agent_id=agent.id)

# Объединить (дубликат → основной)
service.merge(source_ticket_id=456, target_ticket_id=123)
```

**Требуемые права:** `can_merge_tickets`

---

### TicketDeleteService

**Файл:** `app/services/ticket/ticket_delete_service.py`

**Назначение:** Удаление тикетов.

| Метод | Вход | Выход | Описание |
|-------|------|-------|----------|
| `archive(ticket_id)` | `ticket_id: int` | `Ticket` | Архивировать |
| `restore(ticket_id)` | `ticket_id: int` | `Ticket` | Восстановить из архива |
| `hard_delete(ticket_id)` | `ticket_id: int` | `bool` | Полное удаление |
| `bulk_archive(ticket_ids)` | `ticket_ids: list[int]` | `dict` | Массовая архивация |
| `bulk_hard_delete(ticket_ids)` | `ticket_ids: list[int]` | `dict` | Массовое удаление |

**Как вызвать:**
```python
from app.services.ticket import TicketDeleteService

service = TicketDeleteService(db, agent_id=agent.id)

# Архивировать
service.archive(ticket_id=123)

# Восстановить
service.restore(ticket_id=123)

# Полное удаление
deleted = service.hard_delete(ticket_id=123)
```

**Требуемые права:** `can_del_tickets`, `can_add_archive`, `can_hard_del_tickets`

---

### TicketLockService

**Файл:** `app/services/ticket/ticket_lock_service.py`

**Назначение:** Блокировка тикетов.

| Метод | Вход | Выход | Описание |
|-------|------|-------|----------|
| `lock(ticket_id, reason)` | `ticket_id: int`<br>`reason: str \| None` | `Ticket` | Заблокировать |
| `unlock(ticket_id)` | `ticket_id: int` | `Ticket` | Разблокировать |

**Как вызвать:**
```python
from app.services.ticket import TicketLockService

service = TicketLockService(db, agent_id=agent.id)

service.lock(ticket_id=123, reason="Нарушение правил")
service.unlock(ticket_id=123)
```

**Требуемые права:** `can_edit_tickets`

---

### MessageService

**Файл:** `app/services/ticket/message_service.py`

**Назначение:** Управление сообщениями.

| Метод | Вход | Выход | Описание |
|-------|------|-------|----------|
| `add_message(ticket_id, body, is_internal)` | `ticket_id: int`<br>`body: str`<br>`is_internal: bool` | `Message` | Добавить сообщение |
| `edit_message(message_id, new_body)` | `message_id: int`<br>`new_body: str` | `Message` | Редактировать |
| `delete_message(message_id)` | `message_id: int` | `bool` | Удалить |
| `get_message(message_id)` | `message_id: int` | `MessageRead` | Получить |
| `list_by_ticket(ticket_id, filters, limit)` | `ticket_id: int`<br>`filters: dict \| None`<br>`limit: int` (default: `100`) | `list[MessageRead]` | Список сообщений |

**Как вызвать:**
```python
from app.services.ticket import MessageService

service = MessageService(db, agent_id=agent.id)

# Добавить сообщение
service.add_message(
    ticket_id=123,
    body="Ваш вопрос принят в работу",
    is_internal=False,
)

# Список сообщений тикета
messages = service.list_by_ticket(ticket_id=123, limit=50)
```

**Требуемые права:** `can_reply_tickets` или `can_view_tickets`

---

### AttachmentService

**Файл:** `app/services/ticket/attachment_service.py`

**Назначение:** Управление вложениями.

| Метод | Вход | Выход | Описание |
|-------|------|-------|----------|
| `add_attachments(message, files, uploaded_by_agent_id)` | `message: Message`<br>`files: list[dict]`<br>`uploaded_by_agent_id: int` | `list[Attachment]` | Добавить вложения |
| `get(attachment_id)` | `attachment_id: int` | `AttachmentRead` | Получить вложение |
| `list(filters, sort_by, limit)` | `filters: dict \| None`<br>`sort_by: str` (default: `"id"`)<br>`limit: int` (default: `50`) | `list[AttachmentRead]` | Список вложений |
| `delete(attachment_id)` | `attachment_id: int` | `bool` | Удалить вложение |

**Как вызвать:**
```python
from app.services.ticket import AttachmentService

service = AttachmentService(db, agent_id=agent.id)

# Получить вложение
attachment = service.get(attachment_id=456)

# Список вложений тикета
attachments = service.list(filters={"message_id": 123})
```

**Требуемые права:** `can_view_tickets` (чтение), `can_reply_tickets` (добавление)

---

### TicketEventService

**Файл:** `app/services/ticket/ticket_event_service.py`

**Назначение:** Логирование событий.

| Метод | Вход | Выход | Описание |
|-------|------|-------|----------|
| `add_event(ticket_id, action_type, agent_id, field_name, old_value, new_value, comment)` | `ticket_id: int`<br>`action_type: EventType`<br>`agent_id: int \| None`<br>`field_name: str \| None`<br>`old_value: str \| None`<br>`new_value: str \| None`<br>`comment: str \| None` | `TicketEvent` | Добавить событие |
| `list_by_ticket(ticket_id, filters, sort_by, sort_desc, limit, offset)` | `ticket_id: int`<br>`filters: dict \| None`<br>`sort_by: str` (default: `"occurred_at"`)<br>`sort_desc: bool` (default: `True`)<br>`limit: int` (default: `100`)<br>`offset: int` (default: `0`) | `list[TicketEventRead]` | История тикета |
| `get(event_id)` | `event_id: int` | `TicketEventRead` | Получить событие |

**Как вызвать:**
```python
from app.services.ticket import TicketEventService
from app.models.ticket_event import EventType

service = TicketEventService(db)

# Добавить событие
service.add_event(
    ticket_id=123,
    agent_id=agent.id,
    action_type=EventType.status_changed,
    field_name="status_id",
    old_value="1",
    new_value="5",
)

# История тикета
events = service.list_by_ticket(ticket_id=123, limit=50)
```

**Требуемые права:** `can_view_tickets` (чтение), (внутренний для записи)

---

## 📊 Сводная таблица прав

| Право | Сервисы |
|-------|---------|
| `agent_view` | AgentQueryService |
| `agent_create` | AgentCreateService |
| `agent_edit` | AgentEditService |
| `agent_delete` | AgentDeleteService |
| `can_privacy` | AgentPrivacyService |
| `can_man_users` | AgentRoleService, AgentPermissionService |
| `can_view_tickets` | TicketQueryService, MessageService, AttachmentService, TicketEventService |
| `can_view_unassigned` | TicketQueryService.list_unassigned() |
| `can_view_ass_others` | TicketQueryService.list_assigned_to_others() |
| `can_reply_tickets` | TicketReplyService, MessageService.add_message() |
| `can_edit_tickets` | TicketEditService, TicketLockService |
| `can_resolve` | TicketResolveService |
| `can_change_cat` | TicketCategoryService |
| `can_assign_self` | TicketAssignmentService.assign_to_self() |
| `can_assign_others` | TicketAssignmentService |
| `can_merge_tickets` | TicketMergeService |
| `can_del_tickets` | TicketDeleteService.archive() |
| `can_hard_del_tickets` | TicketDeleteService.hard_delete() |
| `can_add_archive` | TicketDeleteService.restore() |
| `can_del_notes` | MessageService.delete(), AttachmentService.delete() |

---

## 🚀 Общие паттерны использования

### 1. Создание сервиса

```python
from app.services.ticket import TicketQueryService

# Все сервисы принимают db и agent_id
service = TicketQueryService(db, agent_id=agent.id)
```

### 2. Обработка ошибок

```python
try:
    ticket = service.get(ticket_id=999)
except ValueError as e:
    # Тикет не найден
    print(f"Ошибка: {e}")
except AccessDeniedError as e:
    # Нет прав
    print(f"Нет прав: {e.detail}")
```

### 3. Транзакции

```python
# Сервисы не делают commit автоматически (кроме create/delete)
# Для массовых операций используйте транзакцию:

with db.begin():
    service.archive(ticket_id=1)
    service.archive(ticket_id=2)
    service.archive(ticket_id=3)
```

---

## 🔐 Права и зависимости

### Права для тикетов

| Право | Описание | Зависимость |
|-------|----------|-------------|
| `can_view_own_tickets` | Просмотр списка своих тикетов | `check_can_view_own_tickets` |
| `can_view_unassigned` | Просмотр неназначенных тикетов | `check_can_view_unassigned` |
| `can_view_ass_others` | Просмотр чужих тикетов | `check_can_view_ass_others` |
| `can_view_all_tickets` | Просмотр всех тикетов (требует все 3 выше) | `check_can_view_all_tickets` |
| `can_view_tickets` | Просмотр деталей тикета | `check_can_view_tickets` |
| `can_reply_tickets` | Ответ на тикеты | `check_can_reply_tickets` |
| `can_edit_tickets` | Редактирование тикетов | `check_can_edit_tickets` |
| `can_del_tickets` | Удаление тикетов (архив) | `check_can_del_tickets` |
| `can_hard_del_tickets` | Полное удаление | `check_can_hard_del_tickets` |

### Права для агентов

| Право | Описание | Зависимость |
|-------|----------|-------------|
| `agent_view` | Просмотр агентов | `check_agent_view` |
| `agent_create` | Создание агентов | `check_agent_create` |
| `agent_edit` | Редактирование агентов | `check_agent_edit` |
| `agent_delete` | Удаление агентов | `check_agent_delete` |

### Уровни проверок

```
┌─────────────────────────────────────────────────────────────┐
│  Уровень 1: Роуты (FastAPI Depends)                        │
│  ├─ check_can_view_own_tickets                             │
│  ├─ check_can_view_all_tickets                             │
│  └─ ...                                                    │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  Уровень 2: Сервисы (проверки внутри методов)              │
│  ├─ TicketService.list() → can_view_*                      │
│  ├─ TicketService.get() → can_view_tickets                 │
│  └─ TicketService.update_ticket() → can_edit_tickets       │
└─────────────────────────────────────────────────────────────┘
```

---

## Контакты

По вопросам обращайтесь к:
- Разработчик: команда разработки
- Дата последнего обновления: 2026-03-27
