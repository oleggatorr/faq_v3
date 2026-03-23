# Модель Message

## Назначение

`Message` хранит сообщения в рамках тикета: сообщения пользователя, ответы оператора и внутренние заметки.

Файл модели: `app/models/message.py`.

## Таблица

- Таблица: `messages`
- Первичный ключ: `id`

## Поля

### Базовые поля

- `id` (`Integer`, PK, autoincrement)
- `ticket_id` (`BigInteger`, FK -> `tickets.id`, `nullable=False`, `index=True`)
- `agent_id` (`BigInteger`, FK -> `agents.id`, `nullable=True`, `index=True`)

### Контент

- `subject` (`String(255)`, `nullable=True`)
- `body` (`Text`, `nullable=False`)

### Данные автора (если клиент)

- `customer_name` (`String(200)`, `nullable=True`)
- `customer_email` (`String(255)`, `nullable=True`)
- `ip_address` (`String(45)`, `nullable=True`)

### Системные флаги

- `is_internal` (`Boolean`, default `False`, `nullable=False`, `index=True`)
- `is_automatic` (`Boolean`, default `False`, `nullable=False`)
- `created_at` (`DateTime`, server default `now()`, `index=True`)

## Связи

- `ticket` -> `Ticket`
- `agent` -> `Agent`
- `attachments` -> `Attachment[]`

## Бизнес-правила

- Если `is_internal = true`, сообщение видно только сотрудникам.
- Для сообщения клиента обычно `agent_id = null`.
- Для сообщения оператора обычно `agent_id` заполнен.
- Сообщение не должно создаваться в заблокированном тикете, если логика блокировки это запрещает.

## Примеры

### Сообщение клиента

- `agent_id`: `null`
- `is_internal`: `false`
- `customer_email`: `user@example.com`

### Внутренняя заметка оператора

- `agent_id`: `12`
- `is_internal`: `true`
- `customer_email`: `null`

## Замечание о расширении

В `app/schemas/message.py` уже есть дополнительные поля (`message_type`, `status`), которых нет в модели.
Если эти функции планируются в API, поля стоит добавить в модель и миграции отдельным шагом.
