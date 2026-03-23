# Модель Agent

## Назначение

`Agent` описывает сотрудника (оператора/админа), который работает с тикетами, отвечает пользователям и выполняет служебные действия в системе.

Файл модели: `app/models/agent.py`.

## Таблица

- Таблица: `agents`
- Первичный ключ: `id`

## Поля

### Идентификация и учетные данные

- `id` (`Integer`, PK, autoincrement) - идентификатор агента.
- `full_name` (`String(200)`, `nullable=False`) - ФИО/имя агента.
- `email` (`String(255)`, `nullable=False`, `unique=True`, `index=True`) - логин и контакт.
- `password_hash` (`String(255)`, `nullable=False`) - хеш пароля.
- `role` (`Enum[admin|operator|readonly]`, `nullable=False`, default `operator`) - роль в системе.

### Доступность и профиль

- `department_id` (`Integer`, FK -> `departments.id`, `nullable=True`, `index=True`) - отдел агента.
- `is_active` (`Boolean`, `nullable=False`, default `True`, `index=True`) - активность учетной записи.
- `phone` (`String(50)`, `nullable=True`) - телефон.
- `avatar_path` (`String(500)`, `nullable=True`) - путь к аватару.
- `last_login_at` (`DateTime`, `nullable=True`) - время последнего входа.

### Доступы и права (новые поля)

- `category_access` (`Text`, `nullable=False`, default `""`) - список категорий, к которым оператор имеет доступ.
- `permissions` (`Text`, `nullable=False`, default `""`) - список разрешенных действий оператора.

## Рекомендованный формат хранения для новых полей

Сейчас по требованию поля хранятся как текст. Чтобы уменьшить ошибки парсинга, рекомендуется фиксировать один формат.

Вариант A (предпочтительно): JSON-строка.

- `category_access`: `"[1,2,5]"`
- `permissions`: `"[\"ticket_read\",\"ticket_update\",\"message_delete\"]"`

Вариант B: CSV-строка.

- `category_access`: `"1,2,5"`
- `permissions`: `"ticket_read,ticket_update,message_delete"`

Важно: один формат должен использоваться везде одинаково (API, сервисы, админка).

## Связи

- `department` -> `Department`
- `owned_tickets` -> `Ticket.owner_id`
- `opened_tickets` -> `Ticket.opened_by_id`
- `closed_tickets` -> `Ticket.closed_by_id`
- `messages` -> `Message.agent_id`
- `attachments` -> `Attachment.uploaded_by_agent_id`
- `events` -> `TicketEvent.agent_id`

## Бизнес-правила

- `role = admin`: обычно полный доступ ко всем категориям и действиям.
- `role = operator`: доступ ограничивается `category_access` и `permissions`.
- `role = readonly`: просмотр без модифицирующих действий.
- Если `is_active = false`, агент не должен иметь доступ к операциям в системе.

## Примеры

### Оператор по сварке

- `category_access`: `"[3,7,8]"`
- `permissions`: `"[\"ticket_read\",\"message_reply\",\"ticket_update_status\"]"`

### Оператор по экономике

- `category_access`: `"[10,11]"`
- `permissions`: `"[\"ticket_read\",\"message_reply\"]"`

## Миграции и совместимость

При применении изменений в проде нужны колонки в БД:

- `category_access` (`TEXT NOT NULL DEFAULT ''`)
- `permissions` (`TEXT NOT NULL DEFAULT ''`)

Если схема БД не обновлена, ORM-модель будет расходиться с реальной таблицей, и операции чтения/записи могут падать с SQL-ошибками.
