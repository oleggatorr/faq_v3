# Модель Ticket

## Назначение

`Ticket` - основная сущность обращения пользователя (жалоба/предложение/вопрос).
Создается без регистрации пользователя и доступна по публичному `track_id`.

Файл модели: `app/models/ticket.py`.

## Таблица

- Таблица: `tickets`
- Первичный ключ: `id`
- Публичный идентификатор: `track_id` (`unique`)

## Поля

### Идентификаторы и контакт клиента

- `id` (`Integer`, PK, autoincrement)
- `track_id` (`String(20)`, `nullable=False`, `unique=True`, `index=True`)
- `customer_name` (`String(200)`, `nullable=False`)
- `customer_email` (`String(255)`, `nullable=False`, `index=True`)
- `customer_ip` (`String(45)`, `nullable=False`)

### Классификация и маршрутизация

- `department_id` (`Integer`, FK -> `departments.id`, `nullable=False`, `index=True`)
- `language_id` (`Integer`, FK -> `languages.id`, `nullable=True`, `index=True`)
- `category_id` (`Integer`, FK -> `question_categories.id`, `nullable=True`, `index=True`)
- `status_id` (`Integer`, FK -> `ticket_statuses.id`, `nullable=False`, `default=1`, `index=True`)
- `priority` (`Enum[low|normal|high|urgent]`, `nullable=False`, default `normal`, `index=True`)

### Контент и назначение

- `subject` (`String(255)`, `nullable=False`)
- `preview_message` (`Text`, `nullable=True`)
- `owner_id` (`Integer`, FK -> `agents.id`, `nullable=True`, `index=True`)
- `opened_by_id` (`Integer`, FK -> `agents.id`, `nullable=True`, `index=True`)

### Временные поля и завершение

- `created_at` (`DateTime`, server default `now()`, `index=True`)
- `updated_at` (`DateTime`, auto update, `index=True`)
- `first_responded_at` (`DateTime`, `nullable=True`)
- `closed_at` (`DateTime`, `nullable=True`)
- `closed_by_id` (`Integer`, FK -> `agents.id`, `nullable=True`)

### Системные флаги и счетчики

- `is_archived` (`Boolean`, default `False`, `nullable=False`, `index=True`)
- `is_locked` (`Boolean`, default `False`, `nullable=False`)
- `merged_into_id` (`Integer`, FK -> `tickets.id`, `nullable=True`, `index=True`)
- `messages_count` (`Integer`, default `0`, `nullable=False`)
- `attachments_count` (`Integer`, default `0`, `nullable=False`)

## Связи

- `department` -> `Department`
- `language` -> `Language`
- `category` -> `QuestionCategory`
- `status` -> `TicketStatus`
- `owner` / `opened_by` / `closed_by` -> `Agent`
- `messages` -> `Message[]`
- `events` -> `TicketEvent[]`
- `merged_into` -> `Ticket` (self reference)

## Бизнес-правила

- `track_id` используется как внешний ключ доступа пользователя к чату.
- При создании тикета обычно сразу создается первое сообщение.
- Пользователь должен видеть только публичные сообщения (`is_internal = false`).
- Архивированные тикеты не должны участвовать в активной очереди.
- Заблокированный тикет (`is_locked`) ограничивает добавление новых сообщений.

## Примеры

### Новый тикет

- `track_id`: `TKT-9X3A7K2Q`
- `status_id`: `1` (новый)
- `priority`: `normal`
- `owner_id`: `null`

### Тикет в работе

- `status_id`: `2` (в работе)
- `owner_id`: `7`
- `first_responded_at`: заполнено

## Риски и рекомендации

- Для `track_id` рекомендуется достаточно случайный формат, чтобы избежать угадывания.
- `messages_count` и `attachments_count` нужно обновлять транзакционно вместе с созданием/удалением связанных сущностей.
- Переходы статусов должны валидироваться в сервисном слое, а не только UI.
