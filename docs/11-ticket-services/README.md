# Сервисы тикетов — полная структура

## 📁 Файловая структура

```
app/services/
├── ticket/                    # Модуль сервисов тикетов
│   ├── __init__.py            # Экспорт сервисов
│   ├── ticket_base_service.py # Базовый класс для сервисов
│   ├── ticket_query_service.py
│   ├── ticket_reply_service.py
│   ├── ticket_edit_service.py
│   ├── ticket_resolve_service.py
│   ├── ticket_category_service.py
│   ├── ticket_assignment_service.py
│   ├── ticket_merge_service.py
│   ├── ticket_delete_service.py
│   ├── ticket_lock_service.py
│   ├── message_service.py
│   ├── attachment_service.py
│   └── ticket_event_service.py
```

---

## 0. TicketBaseService

**Файл:** `app/services/ticket/ticket_base_service.py`

**Назначение:** Базовый класс для всех сервисов тикетов.

```python
from abc import ABC
from sqlalchemy.orm import Session
from app.models.agent import Agent
from app.models.ticket import Ticket
from app.core.errors import AccessDeniedError
from app.core.permissions import Permission, has_permission


class TicketBaseService(ABC):
    """Базовый класс для всех сервисов тикетов."""
    
    def __init__(self, db: Session, agent_id: int | None = None):
        self.db = db
        self.agent_id = agent_id
        self._current_agent: Agent | None = None
    
    def _get_current_agent(self) -> Agent:
        """Получить текущего агента."""
        if self._current_agent is None:
            if not self.agent_id:
                raise ValueError("agent_id не указан")
            
            self._current_agent = (
                self.db.query(Agent)
                .filter(Agent.id == self.agent_id, Agent.is_active == True)
                .one_or_none()
            )
            
            if not self._current_agent:
                raise ValueError(f"Агент {self.agent_id} не найден")
        
        return self._current_agent
    
    def _get_ticket(self, ticket_id: int) -> Ticket:
        """Получить тикет по ID."""
        ticket = self.db.query(Ticket).filter(Ticket.id == ticket_id).one_or_none()
        if not ticket:
            raise ValueError(f"Тикет {ticket_id} не найден")
        return ticket
    
    def _check_permission(self, permission: Permission) -> None:
        """Проверить право доступа."""
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
    
    def _log_event(
        self,
        ticket_id: int,
        action_type: EventType,
        field_name: str | None = None,
        old_value: str | None = None,
        new_value: str | None = None,
        comment: str | None = None,
    ) -> None:
        """Записать событие в аудит тикета."""
        if hasattr(self, 'event_service') and self.event_service:
            self.event_service.add_event(
                ticket_id=ticket_id,
                agent_id=self.agent_id,
                action_type=action_type,
                field_name=field_name,
                old_value=old_value,
                new_value=new_value,
                comment=comment,
            )
```

---

## 1. TicketQueryService

**Файл:** `app/services/ticket/ticket_query_service.py`

**Назначение:** Чтение и фильтрация тикетов (без изменений).

| Метод | Право | Описание |
|-------|-------|----------|
| `list(filters, sort_by, limit, offset)` | `can_view_tickets` | Список всех тикетов с фильтрами |
| `get(ticket_id)` | `can_view_tickets` | Детали конкретного тикета |
| `get_by_track_id(track_id)` | `can_view_tickets` | Поиск по трек-номеру |
| `list_unassigned(filters, limit)` | `can_view_unassigned` | Неназначенные тикеты |
| `list_assigned_to_me(filters, limit)` | `can_view_tickets` | Назначенные себе |
| `list_assigned_to_others(filters, limit)` | `can_view_ass_others` | Назначенные другим |
| `list_by_agent(agent_id, filters, limit)` | `can_view_ass_by` | Назначенные по конкретному агенту |
| `list_online_tickets()` | `can_view_online` | Тикеты онлайн-консультаций |

**Пример использования:**
```python
query_service = TicketQueryService(db, agent_id=agent.id)

# Все тикеты
tickets = query_service.list(
    filters={"status_id": 1, "priority": "high"},
    sort_by="created_at",
    limit=50,
)

# Неназначенные
unassigned = query_service.list_unassigned(limit=20)

# Назначенные мне
my_tickets = query_service.list_assigned_to_me()
```

**Пример реализации:**
```python
from sqlalchemy.orm import Session
from app.models.ticket import Ticket
from app.core.permissions import Permission
from app.schemas.ticket import TicketRead
from app.services.ticket.ticket_base_service import TicketBaseService
from app.services.utils import apply_filters


class TicketQueryService(TicketBaseService):
    """Сервис для чтения тикетов (только чтение)."""
    
    def list(
        self,
        filters: dict | None = None,
        sort_by: str = "created_at",
        sort_desc: bool = False,
        limit: int = 50,
        offset: int = 0,
    ) -> list[TicketRead]:
        """Список всех тикетов. Требуется: can_view_tickets."""
        self._check_permission(Permission.can_view_tickets)
        
        query = self.db.query(Ticket)
        
        if filters:
            query = apply_filters(query, filters, Ticket)
        
        # Сортировка
        column = getattr(Ticket, sort_by, Ticket.created_at)
        query = query.order_by(column.desc() if sort_desc else column.asc())
        
        # Пагинация
        tickets = query.offset(offset).limit(limit).all()
        return [TicketRead.model_validate(t) for t in tickets]
    
    def get(self, ticket_id: int) -> TicketRead:
        """Детали тикета. Требуется: can_view_tickets."""
        self._check_permission(Permission.can_view_tickets)
        ticket = self._get_ticket(ticket_id)
        return TicketRead.model_validate(ticket)
    
    def get_by_track_id(self, track_id: str) -> TicketRead:
        """Поиск по трек-номеру. Требуется: can_view_tickets."""
        self._check_permission(Permission.can_view_tickets)
        
        ticket = self.db.query(Ticket).filter(
            Ticket.track_id == track_id.upper()
        ).one_or_none()
        
        if not ticket:
            raise ValueError(f"Тикет с трек-номером {track_id} не найден")
        
        return TicketRead.model_validate(ticket)
    
    def list_unassigned(
        self,
        filters: dict | None = None,
        limit: int = 50,
    ) -> list[TicketRead]:
        """Неназначенные тикеты. Требуется: can_view_unassigned."""
        self._check_permission(Permission.can_view_unassigned)
        
        query = self.db.query(Ticket).filter(
            Ticket.owner_id.is_(None),
            Ticket.is_archived == False,
        )
        
        if filters:
            query = apply_filters(query, filters, Ticket)
        
        tickets = query.limit(limit).all()
        return [TicketRead.model_validate(t) for t in tickets]
    
    def list_assigned_to_me(
        self,
        filters: dict | None = None,
        limit: int = 50,
    ) -> list[TicketRead]:
        """Назначенные себе. Требуется: can_view_tickets."""
        self._check_permission(Permission.can_view_tickets)
        
        query = self.db.query(Ticket).filter(
            Ticket.owner_id == self.agent_id,
        )
        
        if filters:
            query = apply_filters(query, filters, Ticket)
        
        tickets = query.limit(limit).all()
        return [TicketRead.model_validate(t) for t in tickets]
    
    def list_assigned_to_others(
        self,
        filters: dict | None = None,
        limit: int = 50,
    ) -> list[TicketRead]:
        """Назначенные другим. Требуется: can_view_ass_others."""
        self._check_permission(Permission.can_view_ass_others)
        
        query = self.db.query(Ticket).filter(
            Ticket.owner_id != self.agent_id,
            Ticket.owner_id.isnot(None),
        )
        
        if filters:
            query = apply_filters(query, filters, Ticket)
        
        tickets = query.limit(limit).all()
        return [TicketRead.model_validate(t) for t in tickets]
```

---

## 2. TicketReplyService

**Файл:** `app/services/ticket/ticket_reply_service.py`

**Назначение:** Ответы на тикеты (внешние и внутренние).

| Метод | Право | Описание |
|-------|-------|----------|
| `reply(ticket_id, body, is_internal, attachments)` | `can_reply_tickets` | Ответ клиенту |
| `add_internal_note(ticket_id, body)` | `can_view_tickets` | Внутренняя заметка |
| `edit_note(message_id, new_body)` | `can_del_notes` | Редактирование заметки |
| `delete_note(message_id)` | `can_del_notes` | Удаление заметки |

**Пример:**
```python
reply_service = TicketReplyService(db, agent_id=agent.id)

# Ответ клиенту
reply_service.reply(
    ticket_id=123,
    body="Ваш вопрос решён...",
    is_internal=False,
)

# Внутренняя заметка
reply_service.add_internal_note(
    ticket_id=123,
    body="Клиент звонил, уточнил...",
)
```

**Пример реализации:**
```python
from sqlalchemy.orm import Session
from app.models.ticket import Ticket
from app.models.ticket_event import EventType
from app.core.permissions import Permission
from app.schemas.message import MessageCreate
from app.services.ticket.ticket_base_service import TicketBaseService
from app.services.ticket.message_service import MessageService
from app.services.ticket.ticket_event_service import TicketEventService


class TicketReplyService(TicketBaseService):
    """Сервис для ответов на тикеты."""
    
    def __init__(
        self,
        db: Session,
        agent_id: int | None = None,
        event_service: TicketEventService | None = None,
    ):
        super().__init__(db, agent_id)
        self.event_service = event_service or TicketEventService(db)
    
    def reply(
        self,
        ticket_id: int,
        body: str,
        is_internal: bool = False,
        attachments: list | None = None,
    ) -> MessageRead:
        """
        Ответ на тикет.
        Требуется: can_reply_tickets (для внешних) или can_view_tickets (для внутренних).
        """
        # Проверка права
        required_perm = (
            Permission.can_reply_tickets if not is_internal
            else Permission.can_view_tickets
        )
        self._check_permission(required_perm)
        
        # Получение тикета
        ticket = self._get_ticket(ticket_id)
        
        # Проверка: не заблокирован ли тикет
        if ticket.is_locked and ticket.owner_id != self.agent_id:
            raise BusinessRuleError("Нельзя ответить на заблокированный тикет")
        
        # Создание сообщения
        message_service = MessageService(db, agent_id=self.agent_id)
        message_data = MessageCreate(
            ticket_id=ticket_id,
            agent_id=self.agent_id,
            body=body.strip(),
            is_internal=is_internal,
        )
        message = message_service.add_message(message_data, self.agent_id)
        
        # Событие в audit log
        self._log_event(
            ticket_id=ticket_id,
            action_type=EventType.replied if not is_internal else EventType.note_added,
        )
        
        return message
```

---

## 3. TicketEditService

**Файл:** `app/services/ticket/ticket_edit_service.py`

**Назначение:** Редактирование полей тикета.

| Метод | Право | Описание |
|-------|-------|----------|
| `update_subject(ticket_id, new_subject)` | `can_edit_tickets` | Изменение темы |
| `update_customer_name(ticket_id, new_name)` | `can_edit_tickets` | Имя заявителя |
| `update_customer_email(ticket_id, new_email)` | `can_edit_tickets` | Email заявителя |
| `update_preview(ticket_id, new_preview)` | `can_edit_tickets` | Краткое описание |
| `update_multiple(ticket_id, updates: dict)` | `can_edit_tickets` | Массовое обновление |

**Пример:**
```python
edit_service = TicketEditService(db, agent_id=agent.id)

# Изменение темы
edit_service.update_subject(ticket_id=123, new_subject="Новая тема")

# Массовое обновление
edit_service.update_multiple(
    ticket_id=123,
    updates={
        "subject": "Новая тема",
        "customer_email": "new@example.com",
    },
)
```

---

## 4. TicketResolveService

**Файл:** `app/services/ticket/ticket_resolve_service.py`

**Назначение:** Закрытие тикетов (отметка «Решено»).

| Метод | Право | Описание |
|-------|-------|----------|
| `resolve(ticket_id, resolution_comment)` | `can_resolve` | Закрыть как решённый |
| `reopen(ticket_id)` | `can_resolve` | Открыть заново |

**Пример:**
```python
resolve_service = TicketResolveService(db, agent_id=agent.id)

# Закрыть тикет
resolve_service.resolve(
    ticket_id=123,
    resolution_comment="Проблема решена обновлением ПО",
)

# Открыть заново
resolve_service.reopen(ticket_id=123)
```

---

## 5. TicketCategoryService

**Файл:** `app/services/ticket/ticket_category_service.py`

**Назначение:** Изменение категории тикета.

| Метод | Право | Описание |
|-------|-------|----------|
| `change(ticket_id, new_category_id)` | `can_change_cat` | Изменить категорию |
| `change_own_category(ticket_id, new_category_id)` | `can_change_own_cat` | Изменить свою категорию |

**Пример:**
```python
category_service = TicketCategoryService(db, agent_id=agent.id)

# Изменить категорию
category_service.change(
    ticket_id=123,
    new_category_id=5,
)
```

---

## 6. TicketAssignmentService

**Файл:** `app/services/ticket/ticket_assignment_service.py`

**Назначение:** Назначение исполнителей на тикеты.

| Метод | Право | Описание |
|-------|-------|----------|
| `assign_to_self(ticket_id)` | `can_assign_self` | Назначить себе |
| `assign_to_others(ticket_id, new_owner_id)` | `can_assign_others` | Назначить другому |
| `unassign(ticket_id)` | `can_assign_others` | Снять назначение |
| `reassign(ticket_id, from_agent_id, to_agent_id)` | `can_assign_others` | Переназначить |

**Пример:**
```python
assign_service = TicketAssignmentService(db, agent_id=agent.id)

# Назначить себе
assign_service.assign_to_self(ticket_id=123)

# Назначить другому
assign_service.assign_to_others(
    ticket_id=123,
    new_owner_id=456,
)
```

**Пример реализации:**
```python
from sqlalchemy.orm import Session
from app.models.ticket import Ticket
from app.models.ticket_event import EventType
from app.core.permissions import Permission
from app.core.errors import AccessDeniedError, BusinessRuleError
from app.services.ticket.ticket_base_service import TicketBaseService
from app.services.ticket.ticket_event_service import TicketEventService


class TicketAssignmentService(TicketBaseService):
    """Сервис для назначения исполнителей на тикеты."""
    
    def __init__(
        self,
        db: Session,
        agent_id: int | None = None,
        event_service: TicketEventService | None = None,
    ):
        super().__init__(db, agent_id)
        self.event_service = event_service or TicketEventService(db)
    
    def assign_to_self(self, ticket_id: int) -> Ticket:
        """
        Назначить тикет себе.
        Требуется: can_assign_self.
        """
        # Проверка права
        self._check_permission(Permission.can_assign_self)
        
        # Получение тикета
        ticket = self._get_ticket(ticket_id)
        old_owner = ticket.owner_id
        
        # Проверка: не назначен ли уже другому
        if old_owner and old_owner != self.agent_id:
            if not self._has_permission(Permission.can_assign_others):
                raise BusinessRuleError(
                    "Тикет назначен другому оператору. "
                    "Требуется право can_assign_others"
                )
        
        # Назначение
        ticket.owner_id = self.agent_id
        self.db.flush()
        
        # Событие
        self._log_event(
            ticket_id=ticket_id,
            action_type=EventType.assigned if not old_owner else EventType.unassigned,
            field_name="owner_id",
            old_value=str(old_owner),
            new_value=str(self.agent_id),
        )
        
        return ticket
    
    def assign_to_others(self, ticket_id: int, new_owner_id: int) -> Ticket:
        """
        Назначить тикет другому агенту.
        Требуется: can_assign_others.
        """
        # Проверка права
        self._check_permission(Permission.can_assign_others)
        
        ticket = self._get_ticket(ticket_id)
        old_owner = ticket.owner_id
        
        ticket.owner_id = new_owner_id
        self.db.flush()
        
        # Событие
        self._log_event(
            ticket_id=ticket_id,
            action_type=EventType.assigned,
            field_name="owner_id",
            old_value=str(old_owner),
            new_value=str(new_owner_id),
        )
        
        return ticket
    
    def unassign(self, ticket_id: int) -> Ticket:
        """
        Снять назначение с тикета.
        Требуется: can_assign_others.
        """
        self._check_permission(Permission.can_assign_others)
        
        ticket = self._get_ticket(ticket_id)
        old_owner = ticket.owner_id
        
        if not old_owner:
            raise BusinessRuleError("Тикет уже не назначен")
        
        ticket.owner_id = None
        self.db.flush()
        
        # Событие
        self._log_event(
            ticket_id=ticket_id,
            action_type=EventType.unassigned,
            field_name="owner_id",
            old_value=str(old_owner),
            new_value=None,
        )
        
        return ticket
```

---

## 7. TicketMergeService

**Файл:** `app/services/ticket/ticket_merge_service.py`

**Назначение:** Объединение дублирующихся тикетов.

| Метод | Право | Описание |
|-------|-------|----------|
| `merge(source_ticket_id, target_ticket_id)` | `can_merge_tickets` | Объединить тикеты |
| `can_merge(source_id, target_id)` | `can_merge_tickets` | Проверка возможности |

**Пример:**
```python
merge_service = TicketMergeService(db, agent_id=agent.id)

# Объединить тикеты (дубликат → основной)
merge_service.merge(
    source_ticket_id=456,  # Дубликат
    target_ticket_id=123,  # Основной
)
```

---

## 8. TicketDeleteService

**Файл:** `app/services/ticket/ticket_delete_service.py`

**Назначение:** Удаление тикетов (мягкое и полное).

| Метод | Право | Описание |
|-------|-------|----------|
| `archive(ticket_id)` | `can_del_tickets` | Мягкое удаление (архив) |
| `restore(ticket_id)` | `can_add_archive` | Восстановление из архива |
| `hard_delete(ticket_id)` | `can_hard_del_tickets` | Полное удаление |
| `bulk_archive(ticket_ids)` | `can_del_tickets` | Массовая архивация |
| `bulk_hard_delete(ticket_ids)` | `can_hard_del_tickets` | Массовое удаление |

**Пример:**
```python
delete_service = TicketDeleteService(db, agent_id=agent.id)

# Архивировать
delete_service.archive(ticket_id=123)

# Восстановить
delete_service.restore(ticket_id=123)

# Полное удаление
delete_service.hard_delete(ticket_id=123)
```

---

## 9. TicketLockService

**Файл:** `app/services/ticket/ticket_lock_service.py`

**Назначение:** Блокировка / разблокировка тикетов.

| Метод | Право | Описание |
|-------|-------|----------|
| `lock(ticket_id, reason)` | `can_edit_tickets` | Заблокировать тикет |
| `unlock(ticket_id)` | `can_edit_tickets` | Разблокировать |

**Пример:**
```python
lock_service = TicketLockService(db, agent_id=agent.id)

# Заблокировать
lock_service.lock(
    ticket_id=123,
    reason="Нарушение правил общения",
)

# Разблокировать
lock_service.unlock(ticket_id=123)
```

---

## 10. MessageService

**Файл:** `app/services/ticket/message_service.py`

**Назначение:** Управление сообщениями и примечаниями.

| Метод | Право | Описание |
|-------|-------|----------|
| `add_message(ticket_id, body, is_internal)` | `can_reply_tickets` | Добавить сообщение |
| `edit_message(message_id, new_body)` | `can_edit_tickets` | Редактировать сообщение |
| `delete_message(message_id)` | `can_del_notes` | Удалить сообщение |
| `delete_internal_note(message_id)` | `can_del_notes` | Удалить внутреннюю заметку |
| `get_message(message_id)` | `can_view_tickets` | Получить сообщение |
| `list_by_ticket(ticket_id, filters)` | `can_view_tickets` | Список сообщений |

**Пример:**
```python
message_service = MessageService(db, agent_id=agent.id)

# Добавить сообщение
message_service.add_message(
    ticket_id=123,
    body="Ваш вопрос принят в работу",
    is_internal=False,
)

# Удалить заметку
message_service.delete_internal_note(message_id=456)
```

---

## 11. AttachmentService

**Файл:** `app/services/ticket/attachment_service.py`

**Назначение:** Управление вложениями.

| Метод | Право | Описание |
|-------|-------|----------|
| `add_attachments(message, files, uploaded_by_agent_id)` | `can_reply_tickets` | Добавить вложения |
| `get(attachment_id)` | `can_view_tickets` | Получить вложение |
| `list(filters, sort_by, limit)` | `can_view_tickets` | Список вложений |
| `delete(attachment_id)` | `can_del_notes` | Удалить вложение |

**Пример:**
```python
attachment_service = AttachmentService(db, agent_id=agent.id)

# Добавить вложения
attachment_service.add_attachments(
    message=message,
    files=[{"path": "/path/to/file.pdf", "original_filename": "doc.pdf"}],
    uploaded_by_agent_id=agent.id,
)
```

---

## 12. TicketEventService

**Файл:** `app/services/ticket/ticket_event_service.py`

**Назначение:** Логирование событий тикетов (audit log).

| Метод | Право | Описание |
|-------|-------|----------|
| `add_event(ticket_id, action_type, ...)` | (внутренний) | Добавить событие |
| `list_by_ticket(ticket_id, filters)` | `can_view_tickets` | История событий |
| `get(event_id)` | `can_view_tickets` | Получить событие |

**Пример:**
```python
event_service = TicketEventService(db)

# Добавить событие
event_service.add_event(
    ticket_id=123,
    agent_id=agent.id,
    action_type=EventType.status_changed,
    field_name="status_id",
    old_value="1",
    new_value="5",
)

# История тикета
events = event_service.list_by_ticket(ticket_id=123)
```

---

## 📊 Сводная таблица прав

| Право | Сервисы используют |
|-------|-------------------|
| `can_view_tickets` | TicketQueryService, MessageService, AttachmentService, TicketEventService |
| `can_view_unassigned` | TicketQueryService.list_unassigned() |
| `can_view_ass_others` | TicketQueryService.list_assigned_to_others() |
| `can_view_ass_by` | TicketQueryService.list_by_agent() |
| `can_view_online` | TicketQueryService.list_online_tickets() |
| `can_reply_tickets` | TicketReplyService.reply(), MessageService.add_message(), AttachmentService.add_attachments() |
| `can_edit_tickets` | TicketEditService.*, TicketLockService.* |
| `can_resolve` | TicketResolveService.resolve(), reopen() |
| `can_change_cat` | TicketCategoryService.change() |
| `can_change_own_cat` | TicketCategoryService.change_own_category() |
| `can_assign_self` | TicketAssignmentService.assign_to_self() |
| `can_assign_others` | TicketAssignmentService.assign_to_others(), unassign(), reassign() |
| `can_merge_tickets` | TicketMergeService.merge() |
| `can_del_tickets` | TicketDeleteService.archive(), bulk_archive() |
| `can_hard_del_tickets` | TicketDeleteService.hard_delete(), bulk_hard_delete() |
| `can_add_archive` | TicketDeleteService.restore() |
| `can_del_notes` | MessageService.delete_message(), delete_internal_note(), AttachmentService.delete() |

---

## 🚀 Использование в роутах

```python
# app/web/jinja/routes/tickets/admin.py

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from app.core.auth import CurrentAgent
from app.models import get_db
from app.services.ticket import (
    TicketQueryService,
    TicketReplyService,
    TicketAssignmentService,
    TicketDeleteService,
)

router = APIRouter(prefix="/tickets", tags=["tickets-admin"])


@router.get("", response_class=HTMLResponse)
def tickets_list(
    request: Request,
    agent: CurrentAgent,
    db: Session = Depends(get_db),
):
    """Список тикетов."""
    query_service = TicketQueryService(db, agent_id=agent.id)
    tickets = query_service.list(
        filters=_ticket_filters(request),
        sort_by=request.query_params.get("sort_by", "created_at"),
        limit=50,
    )
    return templates.TemplateResponse("tickets/list.html", {
        "tickets": tickets,
        "agent": agent,
    })


@router.post("/{ticket_id}/reply", response_class=RedirectResponse)
def reply(
    ticket_id: int,
    request: Request,
    agent: CurrentAgent,
    db: Session = Depends(get_db),
    body: str = Form(...),
):
    """Ответ на тикет."""
    reply_service = TicketReplyService(db, agent_id=agent.id)
    reply_service.reply(ticket_id, body.strip(), is_internal=False)
    return RedirectResponse(url=f"/tickets/{ticket_id}")


@router.post("/{ticket_id}/assign-to-me", response_class=RedirectResponse)
def assign_to_me(
    ticket_id: int,
    agent: CurrentAgent,
    db: Session = Depends(get_db),
):
    """Назначить тикет себе."""
    assign_service = TicketAssignmentService(db, agent_id=agent.id)
    assign_service.assign_to_self(ticket_id)
    return RedirectResponse(url=f"/tickets/{ticket_id}")


@router.post("/{ticket_id}/archive", response_class=RedirectResponse)
def archive_ticket(
    ticket_id: int,
    agent: CurrentAgent,
    db: Session = Depends(get_db),
):
    """Архивировать тикет."""
    delete_service = TicketDeleteService(db, agent_id=agent.id)
    delete_service.archive(ticket_id)
    return RedirectResponse(url="/tickets")
```

---

## 📁 Структура файлов

```
app/
├── core/
│   └── permissions.py          # Permission enum, PERMISSION_LABELS
├── models/
│   ├── ticket.py               # Ticket модель
│   ├── message.py              # Message модель
│   ├── attachment.py           # Attachment модель
│   └── ticket_event.py         # TicketEvent модель
├── schemas/
│   ├── ticket.py               # TicketCreate, TicketUpdate, TicketRead
│   ├── message.py              # MessageCreate, MessageUpdate, MessageRead
│   └── attachment.py           # AttachmentCreate, AttachmentRead
├── services/
│   └── ticket/
│       ├── __init__.py
│       ├── ticket_base_service.py
│       ├── ticket_query_service.py
│       ├── ticket_reply_service.py
│       ├── ticket_edit_service.py
│       ├── ticket_resolve_service.py
│       ├── ticket_category_service.py
│       ├── ticket_assignment_service.py
│       ├── ticket_merge_service.py
│       ├── ticket_delete_service.py
│       ├── ticket_lock_service.py
│       ├── message_service.py
│       ├── attachment_service.py
│       └── ticket_event_service.py
└── web/jinja/
    └── routes/
        └── tickets/
            ├── public.py       # Публичные роуты
            └── admin.py        # Админские роуты
```

---

## 🚀 Следующие шаги

1. **Создать базовый класс** `TicketBaseService` ✅ (существует)
2. **Реализовать сервисы по одному** (начать с `TicketQueryService`)
3. **Обновить роуты** для использования новых сервисов
4. **Написать тесты** на проверку прав доступа
5. **Добавить аудит** всех операций через `TicketEventService`

---

## Контакты

По вопросам расширения системы сервисов тикетов обращайтесь к:
- Разработчик: команда разработки
- Дата последнего обновления: 2026-03-27
