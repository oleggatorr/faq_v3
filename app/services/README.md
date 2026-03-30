# Service Layer (Сервисный слой)

Папка содержит сервисный слой (бизнес-логика) приложения.

## Архитектура

```
app/services/
├── agent_service.py              # Агент (операторы, админы)
├── operator_category_service.py  # Доступ операторов к категориям
├── operator_permissions_service.py # Права операторов
├── department_service.py         # Департаменты
├── question_category_service.py  # Категории вопросов
├── ticket_status_service.py      # Статусы тикетов
├── language_service.py           # Языки
├── audit_log_service.py          # Аудит логи
├── email_service.py              # Email уведомления
├── file_storage_service.py       # Хранение файлов
├── errors.py                     # Исключения сервисного слоя
├── utils.py                      # Утилиты
└── ticket/                       # Сервисы тикетов
    ├── ticket_service.py         # Тикеты CRUD
    ├── ticket_event_service.py   # События тикетов (аудит)
    ├── message_service.py        # Сообщения
    ├── attachment_service.py     # Вложения
    ├── read_state_service.py     # Прочитанные сообщения
    ├── assignment_service.py     # Автоназначение
    └── ticket_base_service.py    # Базовый класс для тикетов
```

## Принципы проектирования

Все сервисы:
- ✅ Инкапсулируют бизнес-логику
- ✅ Не зависят от HTTP/ORM деталей
- ✅ Используют явные методы домена (create/update/delete/list)
- ✅ Возвращают схемы (Pydantic) или модели (SQLAlchemy)
- ✅ Пишут аудит-события в `ticket_events` для ключевых операций

## Общий контракт для `list()`

Большинство CRUD сервисов реализуют одинаковую сигнатуру:

```python
def list(
    self,
    *,
    filters: dict[str, Any] | None = None,
    sort_by: str = "id",
    sort_desc: bool = False,
    limit: int = 100,
    offset: int = 0,
) -> list[ReadSchema]
```

**Детали реализации:**
- `filters` — фильтрация по полям (equality, строки через `ILIKE`)
- `sort_by` — только из whitelist (безопасная сортировка)
- `limit/offset` — применяются на уровне SQL

---

# Сервисы тикетов (`app/services/ticket/`)

## `TicketService`

**Файл:** `ticket/ticket_service.py`

Ticket CRUD + мутации тикетов. Аудит-логирование через `TicketEventService`.

### CRUD операции

| Метод | Сигнатура | Описание |
|-------|-----------|----------|
| `create_ticket` | `(ticket_data: TicketCreate, commit: bool = True) -> Ticket` | Создать тикет |
| `get` | `(ticket_id: int) -> TicketRead` | Получить тикет по ID |
| `get_by_track_id` | `(track_id: str) -> TicketRead` | Получить по публичному track_id |
| `list` | `(filters, sort_by, sort_desc, limit, offset, include_unread, agent_id) -> list[TicketRead]` | Список тикетов |
| `update_ticket` | `(ticket_id, ticket_data, agent_id, commit) -> Ticket` | Обновить тикет |
| `delete_ticket` | `(ticket_id, agent_id, commit) -> DeleteResponse` | Soft-delete (архивирование) |
| `hard_delete_ticket` | `(ticket_id, agent_id, commit) -> DeleteResponse` | Полное удаление |

### Доменные мутации

| Метод | Сигнатура | События в `ticket_events` |
|-------|-----------|--------------------------|
| `change_status` | `(ticket_id, new_status_id, agent_id, commit) -> Ticket` | `status_changed`, `closed`/`reopened` |
| `assign_owner` | `(ticket_id, new_owner_id, agent_id, commit) -> Ticket` | `assigned`/`unassigned` |
| `change_category` | `(ticket_id, new_category_id, agent_id, commit) -> Ticket` | `category_changed` |
| `merge_tickets` | `(source_id, target_id, agent_id, commit) -> Ticket` | `merged` |
| `set_locked` | `(ticket_id, is_locked, agent_id, commit) -> Ticket` | `locked`/`unlocked` |
| `anonymize_ticket` | `(ticket_id, agent_id, commit) -> Ticket` | `anonymized` |

### Создание тикета с первым сообщением

```python
create_ticket_with_first_message(
    ticket_data: TicketCreate,
    first_message_body: str,
    commit: bool = True,
) -> tuple[Ticket, Message]
```

**Правила для `preview_message`:**
- `len(body) <= 200` → `preview = body`
- `len(body) > 200` → `preview = body[:200] + "..."`

### Работа с прочитанными сообщениями

| Метод | Сигнатура | Описание |
|-------|-----------|----------|
| `get_unread_count` | `(ticket_id: int, exclude_internal: bool = True) -> int` | Количество непрочитанных |
| `mark_as_read` | `(ticket_id: int) -> None` | Отметить как прочитанное |

---

## `TicketEventService`

**Файл:** `ticket/ticket_event_service.py`

Сохранение аудит-событий для `ticket_events`.

| Метод | Сигнатура | Описание |
|-------|-----------|----------|
| `add_event` | `(ticket_id, agent_id, action_type, field_name, old_value, new_value, comment, commit) -> TicketEvent` | Добавить событие |
| `get` | `(event_id: int) -> TicketEventRead` | Получить событие по ID |
| `list_by_ticket` | `(ticket_id, filters, sort_by, sort_desc, limit, offset) -> list[TicketEventRead]` | События тикета |
| `create` | `(event_data: TicketEventCreate, commit) -> TicketEvent` | Создать событие |
| `update` | `(event_id, event_data, commit) -> TicketEvent` | Обновить событие |
| `delete` | `(event_id, commit) -> DeleteResponse` | Удалить событие |

**Типы событий (`EventType`):**
- `created`, `replied`, `customer_replied`
- `status_changed`, `closed`, `reopened`
- `assigned`, `unassigned`
- `category_changed`, `priority_changed`
- `merged`, `locked`, `unlocked`
- `note_added`, `attachment_added`
- `archived`, `unarchived`

---

## `MessageService`

**Файл:** `ticket/message_service.py`

Сообщения CRUD + аудит изменений.

| Метод | Сигнатура | Описание |
|-------|-----------|----------|
| `add_message` | `(message_data, agent_id, commit) -> Message` | Добавить сообщение |
| `edit_internal_note` | `(message_id, new_body, agent_id, commit) -> Message` | Редактировать заметку |
| `delete_internal_note` | `(message_id, agent_id, commit) -> None` | Удалить заметку |
| `get` | `(message_id: int) -> MessageRead` | Получить сообщение |
| `list` | `(filters, sort_by, sort_desc, limit, offset) -> list[MessageRead]` | Список сообщений |
| `update` | `(message_id, message_data, agent_id, commit) -> Message` | Обновить сообщение |
| `delete` | `(message_id, agent_id, commit) -> DeleteResponse` | Удалить сообщение |

**Аудит-логирование:**
- Внутренние заметки (`is_internal=true`): `note_added`
- Сообщения клиента: `customer_replied`
- Сообщения оператора: `replied`

**Дополнительно:**
- `tickets.messages_count` инкрементируется/декрементируется

---

## `AttachmentService`

**Файл:** `ticket/attachment_service.py`

Вложения CRUD + аудит.

| Метод | Сигнатура | Описание |
|-------|-----------|----------|
| `add_attachments` | `(message, uploaded_by_agent_id, files, commit) -> list[Attachment]` | Загрузить файлы |
| `get` | `(attachment_id: int) -> AttachmentRead` | Получить вложение |
| `list` | `(filters, sort_by, sort_desc, limit, offset) -> list[AttachmentRead]` | Список вложений |
| `create` | `(attachment_data, commit) -> Attachment` | Создать запись |
| `update` | `(attachment_id, attachment_data, commit) -> Attachment` | Обновить |
| `delete` | `(attachment_id, commit) -> DeleteResponse` | Удалить |

**Структура `files` для `add_attachments`:**
```python
{
    "original_filename": str,
    "stored_filename": str,
    "file_path": str,
    "file_size": int,
    "mime_type": str,
    "file_hash": str,  # опционально
}
```

**Аудит:** `attachment_added` при создании/удалении.

**Дополнительно:**
- `tickets.attachments_count` инкрементируется/декрементируется

---

## `TicketReadStateService`

**Файл:** `ticket/read_state_service.py`

Отслеживание прочитанных сообщений владельцем тикета.

| Метод | Сигнатура | Описание |
|-------|-----------|----------|
| `mark_as_read` | `(ticket_id: int) -> None` | Отметить все сообщения как прочитанные |
| `get_unread_count` | `(ticket_id: int, exclude_internal: bool = True) -> int` | Количество непрочитанных в тикете |
| `get_unread_counts_bulk` | `(ticket_ids: list[int], exclude_internal: bool = True) -> dict[int, int]` | Массовое получение счётчиков |
| `get_total_unread_for_agent` | `(agent_id: int, exclude_internal: bool = True) -> int` | **Общее кол-во непрочитанных по всем тикетам агента** |
| `get_tickets_with_unread` | `(agent_id: int, exclude_internal: bool = True, min_unread: int = 1) -> list[dict]` | **Список тикетов с непрочитанными** |
| `reset_on_reassign` | `(ticket_id: int) -> None` | Сброс при смене владельца |

**Логика:**
- Хранится в таблице `ticket_read_states`
- `last_read_message_id` — ID последнего прочитанного сообщения
- При смене владельца состояние сбрасывается

**Примеры использования:**

```python
# 1. Обновить непрочитанные (после написания сообщения)
service.mark_as_read(ticket_id=123)

# 2. Открыть чат и обнулить непрочитанные
service.mark_as_read(ticket_id=123)

# 3. Получить общее количество непрочитанных у оператора
total = service.get_total_unread_for_agent(agent_id=456)
# → 15 (всего непрочитанных сообщений)

# 4. Получить список тикетов с непрочитанными
tickets = service.get_tickets_with_unread(agent_id=456, min_unread=1)
# → [
#      {"ticket_id": 123, "unread_count": 5},
#      {"ticket_id": 456, "unread_count": 3},
#      {"ticket_id": 789, "unread_count": 1},
#    ]
```

---

## `AssignmentService`

**Файл:** `ticket/assignment_service.py`

Автоназначение тикетов на операторов.

| Метод | Сигнатура | Описание |
|-------|-----------|----------|
| `auto_assign` | `(ticket_id, strategy, department_id, category_id, commit) -> Ticket` | Назначить оператора |

**Стратегии:**
- `round_robin` — по очереди
- `load_balanced` — по наименьшей нагрузке
- `skills_based` — по навыкам (category_access)

---

## `TicketBaseService`

**Файл:** `ticket/ticket_base_service.py`

Базовый класс для всех сервисов тикетов.

| Метод | Сигнатура | Описание |
|-------|-----------|----------|
| `_get_current_agent` | `() -> Agent` | Получить текущего агента |
| `_get_ticket` | `(ticket_id: int) -> Ticket` | Получить тикет по ID |
| `_check_permission` | `(permission: Permission) -> None` | Проверить право (выбросить ошибку) |
| `_has_permission` | `(permission: Permission) -> bool` | Проверить право (вернуть bool) |

---

# Основные сервисы

## `AgentService`

**Файл:** `agent_service.py`

Агент (операторы, админы) CRUD.

| Метод | Сигнатура | Описание |
|-------|-----------|----------|
| `create` | `(agent_data: AgentCreate, commit: bool = True) -> Agent` | Создать агента |
| `get` | `(agent_id: int) -> AgentRead` | Получить агента |
| `list` | `(filters, sort_by, sort_desc, limit, offset) -> list[AgentRead]` | Список агентов |
| `update` | `(agent_id, agent_data: AgentUpdate, commit) -> Agent` | Обновить профиль |
| `delete` | `(agent_id: int, commit: bool = True) -> DeleteResponse` | Удалить агента |

**Фильтры для `list()`:**
- `search` — поиск по `login` + `full_name` (ILIKE)
- `category_id` — вхождение в `category_access`
- `auto_assign` — фильтр по автоназначению
- Стандартные: `id`, `login`, `email`, `role`, `department_id`, `is_active`, `phone`, `last_login_at`

**Сортировка:**
- Доступные поля: `id`, `login`, `full_name`, `email`, `role`, `department_id`, `is_active`, `last_login_at`, `created_at`, `updated_at`, `auto_assign`

---

## `OperatorCategoryService`

**Файл:** `operator_category_service.py`

Доступ операторов к категориям вопросов.

| Метод | Сигнатура | Описание |
|-------|-----------|----------|
| `get_operators_for_category` | `(category_id, include_inactive, only_auto_assign, department_id, limit) -> list[OperatorWithScore]` | Все операторы со score |
| `get_best_operators_for_category` | `(category_id, limit, department_id) -> list[OperatorWithScore]` | Топ операторов |
| `has_access_to_category` | `(agent_id, category_id) -> bool` | Проверка доступа |
| `get_category_access_list` | `(agent_id: int) -> list[int]` | Список категорий оператора |
| `add_category_access` | `(agent_id, category_id, commit) -> bool` | Добавить категорию |
| `remove_category_access` | `(agent_id, category_id, commit) -> bool` | Удалить категорию |

**Система score:**

| Роль | Доступ | Score |
|------|--------|-------|
| Admin | Всегда | 100 |
| Operator | Явный (в `category_access`) | 10 |
| Operator | Нет доступа | 0 |

**Структура `OperatorWithScore`:**
```python
{
    "agent": AgentRead,
    "score": int,
    "has_explicit_access": bool,
    "is_admin": bool,
    "department_name": str | None,
}
```

**Формат `category_access`:** строка с ID через запятую: `"1,3,5"`

---

## `OperatorPermissionsService`

**Файл:** `operator_permissions_service.py`

Проверка прав операторов.

| Метод | Сигнатура | Описание |
|-------|-----------|----------|
| `assert_can` | `(agent, action, context) -> None` | Проверить право (выбросить ошибку) |

**Структура `PermissionContext`:**
```python
{
    "ticket_category_id": int | None,
}
```

**Источники прав:**
- `agents.category_access` — список категорий
- `agents.permissions` — список прав (через запятую)

**Ошибки:**
- `PermissionDenied` — нет прав доступа

---

## `DepartmentService`

**Файл:** `department_service.py`

Департаменты CRUD.

| Метод | Сигнатура | Описание |
|-------|-----------|----------|
| `create` | `(department_data: DepartmentCreate, commit) -> Department` | Создать департамент |
| `get` | `(department_id: int) -> DepartmentRead` | Получить |
| `list` | `(filters, sort_by, sort_desc, limit, offset) -> list[DepartmentRead]` | Список |
| `update` | `(department_id, department_data: DepartmentUpdate, commit) -> Department` | Обновить |
| `delete` | `(department_id: int, commit) -> DeleteResponse` | Удалить |

**Фильтры:** `id`, `name`, `email`, `is_active`, `sort_order`

**Сортировка:** `id`, `name`, `email`, `is_active`, `sort_order`, `created_at`, `updated_at`

---

## `QuestionCategoryService`

**Файл:** `question_category_service.py`

Категории вопросов CRUD.

| Метод | Сигнатура | Описание |
|-------|-----------|----------|
| `create` | `(category_data: QuestionCategoryCreate, commit) -> QuestionCategory` | Создать категорию |
| `get` | `(category_id: int) -> QuestionCategoryRead` | Получить |
| `list` | `(filters, sort_by, sort_desc, limit, offset) -> list[QuestionCategoryRead]` | Список |
| `update` | `(category_id, category_data: QuestionCategoryUpdate, commit) -> QuestionCategory` | Обновить |
| `delete` | `(category_id: int, commit) -> DeleteResponse` | Удалить |

**Фильтры:** `id`, `name`, `department_id`, `parent_id`, `icon`, `color`, `is_active`, `sort_order`

**Сортировка:** `id`, `name`, `department_id`, `parent_id`, `is_active`, `sort_order`, `created_at`, `updated_at`

---

## `TicketStatusService`

**Файл:** `ticket_status_service.py`

Статусы тикетов CRUD.

| Метод | Сигнатура | Описание |
|-------|-----------|----------|
| `create` | `(status_data: TicketStatusCreate, commit) -> TicketStatus` | Создать статус |
| `get` | `(status_id: int) -> TicketStatusRead` | Получить |
| `list` | `(filters, sort_by, sort_desc, limit, offset) -> list[TicketStatusRead]` | Список |
| `update` | `(status_id, status_data: TicketStatusUpdate, commit) -> TicketStatus` | Обновить |
| `delete` | `(status_id: int, commit) -> DeleteResponse` | Удалить |

**Фильтры:** `id`, `code`, `name`, `is_closed`, `is_default`, `sort_order`, `color`

**Сортировка:** `id`, `code`, `name`, `is_closed`, `is_default`, `sort_order`, `color`

---

## `LanguageService`

**Файл:** `language_service.py`

Языки CRUD.

| Метод | Сигнатура | Описание |
|-------|-----------|----------|
| `create` | `(language_data: LanguageCreate, commit) -> Language` | Создать язык |
| `get` | `(language_id: int) -> LanguageRead` | Получить |
| `list` | `(filters, sort_by, sort_desc, limit, offset) -> list[LanguageRead]` | Список |
| `update` | `(language_id, language_data: LanguageUpdate, commit) -> Language` | Обновить |
| `delete` | `(language_id: int, commit) -> DeleteResponse` | Удалить |

**Фильтры:** `id`, `code`, `name`, `is_active`, `is_default`, `sort_order`, `locale`

**Сортировка:** `id`, `code`, `name`, `is_active`, `is_default`, `sort_order`, `created_at`

---

# Вспомогательные сервисы

## `AuditLogService`

**Файл:** `audit_log_service.py`

Работа с аудит-логами.

| Метод | Сигнатура | Описание |
|-------|-----------|----------|
| `create` | `(log_data: AuditLogCreate) -> AuditLog` | Создать запись |
| `log_action` | `(action, entity_type, entity_id, agent_id, details, ip_address, user_agent) -> AuditLog` | Быстрое логирование |
| `get_list` | `(agent_id, action, entity_type, limit, offset) -> list[AuditLog]` | Список логов |
| `get_count` | `(agent_id, action, entity_type) -> int` | Количество логов |

**Параметры `log_action`:**
- `action` — тип действия (`create`, `update`, `delete`, `login`, `logout`)
- `entity_type` — тип объекта (`ticket`, `agent`, `department`)
- `entity_id` — ID объекта
- `agent_id` — ID агента, выполнившего действие
- `details` — дополнительные данные (JSON)
- `ip_address` — IP-адрес
- `user_agent` — User-Agent

---

## `EmailService`

**Файл:** `email_service.py`

Отправка email-уведомлений.

| Функция | Сигнатура | Описание |
|---------|-----------|----------|
| `send_email` | `(to, subject, body, reply_to) -> None` | Отправить email |
| `notify_ticket_created` | `(to_email, track_id, subject, customer_name, body_preview) -> None` | Уведомление о создании тикета |
| `notify_new_message` | `(to_email, track_id, subject, message_preview, from_name) -> None` | Уведомление о новом сообщении |
| `notify_status_changed` | `(to_email, track_id, subject, new_status, customer_name) -> None` | Уведомление о смене статуса |

**Конфигурация:**
- SMTP: `smtp.gmail.com:587`
- Временно: все письма идут на фиксированный адрес

---

## `FileStorageService`

**Файл:** `file_storage_service.py`

Сохранение файлов на диск.

| Метод | Сигнатура | Описание |
|-------|-----------|----------|
| `save` | `(content, original_filename, mime_type, max_size) -> dict` | Сохранить файл |
| `get_path` | `(file_path: str) -> Path` | Получить путь к файлу |
| `exists` | `(file_path: str) -> bool` | Проверить существование |

**Возвращаемое значение `save()`:**
```python
{
    "original_filename": str,
    "stored_filename": str,  # uuid4.hex + расширение
    "file_path": str,
    "file_size": int,
    "mime_type": str,
    "file_hash": str,  # sha256
}
```

**Валидация:**
- Размер: до `settings.UPLOAD_MAX_SIZE`
- Расширение: до 20 символов

---

## Исключения

**Файл:** `errors.py`

| Исключение | Описание |
|------------|----------|
| `NotFound` | Объект не найден |
| `Conflict` | Конфликт (дубликат, например track_id) |
| `ValidationFailed` | Ошибка валидации данных |
| `PermissionDenied` | Нет прав доступа |

---

## Утилиты

**Файл:** `utils.py`

| Функция | Сигнатура | Описание |
|---------|-----------|----------|
| `apply_filters` | `(query, model, filters, text_like_fields) -> Query` | Применить фильтры |
| `apply_sort` | `(query, model, sort_by, sort_desc, allowed_sort_fields) -> Query` | Применить сортировку |
| `format_preview` | `(body: str, max_length: int = 200) -> str` | Обрезать текст для preview |
| `parse_text_list` | `(text: str) -> list[str]` | Разобрать строку в список (запятые) |

---

## Тестирование

Тесты находятся в `test/`:

```bash
# Запустить все тесты сервисов
pytest test/ -v

# Только тесты для TicketReadStateService
pytest test/test_read_state_service.py -v

# Только тесты для OperatorCategoryService
pytest test/test_operator_category_service.py -v

# Только интеграционные тесты
pytest test/test_ticket_read_integration.py -v

# С покрытием
pytest test/ --cov=app/services --cov-report=html
```

**Фикстуры:**
- `db_session` — сессия БД с откатом транзакции
- `test_agent`, `test_agent2` — тестовые агенты
- `test_department` — тестовый департамент
- `test_status` — тестовый статус
- `test_ticket` — тестовый тикет
- `test_messages` — набор сообщений (5 шт)
- `test_category` — тестовая категория
- `service` — экземпляр сервиса

---

## Диаграмма зависимостей

```
┌─────────────────────────────────────────────────────────┐
│                    TicketService                        │
│  ┌─────────────┐  ┌──────────────────┐  ┌────────────┐ │
│  │TicketEvent  │  │TicketReadState   │  │Message     │ │
│  │Service      │  │Service           │  │Service     │ │
│  └─────────────┘  └──────────────────┘  └────────────┘ │
│                        │                                │
│                        ▼                                │
│              ┌──────────────────┐                       │
│              │AssignmentService │                       │
│              └──────────────────┘                       │
│                        │                                │
│                        ▼                                │
│         ┌──────────────────────────────┐                │
│         │OperatorCategoryService       │                │
│         │(доступ операторов к категориям)│               │
│         └──────────────────────────────┘                │
└─────────────────────────────────────────────────────────┘
```

---

## Changelog

### v2.1 (2026-03-30)
- ✅ Добавлен `get_total_unread_for_agent()` — общее количество непрочитанных по всем тикетам
- ✅ Добавлен `get_tickets_with_unread()` — список тикетов с непрочитанными сообщениями
- ✅ API endpoints:
  - `GET /tickets/unread/total` — получить общее количество непрочитанных
  - `GET /tickets/unread/list` — получить список тикетов с непрочитанными

### v2.0 (2026-03-30)
- ✅ Добавлен `TicketReadStateService` — отслеживание прочитанных сообщений
- ✅ Добавлен `OperatorCategoryService` — доступ операторов к категориям
- ✅ Обновлён `TicketService.list()` — опция `include_unread`
- ✅ `assign_owner()` — сброс состояния прочтения при смене владельца
- ✅ API endpoints: `POST /tickets/{id}/mark-as-read`, `GET /tickets/{id}/unread-count`
- ✅ Тесты: 14 тестов для read state + 13 тестов для operator category

### v1.0 (baseline)
- ✅ Базовые CRUD сервисы
- ✅ Аудит-логирование через `ticket_events`
- ✅ Email уведомления
- ✅ Хранение файлов
