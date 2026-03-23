# Модель TicketEvent

## Назначение

`TicketEvent` хранит аудит действий и изменений по тикету: создание, ответы, смену статуса, назначение и другие события.

Файл модели: `app/models/ticket_event.py`.

## Таблица

- Таблица: `ticket_events`
- Первичный ключ: `id`

## Поля

### Идентификаторы

- `id` (`BigInteger`, PK, autoincrement)
- `ticket_id` (`BigInteger`, FK -> `tickets.id`, `nullable=False`, `index=True`)
- `agent_id` (`BigInteger`, FK -> `agents.id`, `nullable=True`, `index=True`)

### Данные события

- `action_type` (`Enum[EventType]`, `nullable=False`, `index=True`)
- `field_name` (`String(100)`, `nullable=True`) - какое поле изменялось.
- `old_value` (`Text`, `nullable=True`) - старое значение.
- `new_value` (`Text`, `nullable=True`) - новое значение.
- `comment` (`Text`, `nullable=True`) - пояснение.
- `occurred_at` (`DateTime`, server default `now()`, `index=True`)

## Текущие типы `EventType` в модели

- `created`
- `replied`
- `status_changed`
- `priority_changed`
- `assigned`
- `unassigned`
- `category_changed`
- `merged`
- `closed`
- `reopened`
- `locked`
- `unlocked`
- `note_added`
- `attachment_added`
- `customer_replied`

## Связи

- `ticket` -> `Ticket`
- `agent` -> `Agent`

## Бизнес-правила

- Каждое ключевое действие по тикету должно оставлять запись в `ticket_events`.
- Если событие инициировано системой, `agent_id` может быть `null`.
- Для полей `old_value/new_value` допустимо хранить и простые значения, и сериализованные структуры.

## Примеры

### Назначение оператора

- `action_type`: `assigned`
- `field_name`: `owner_id`
- `old_value`: `null`
- `new_value`: `7`

### Изменение статуса

- `action_type`: `status_changed`
- `field_name`: `status_id`
- `old_value`: `1`
- `new_value`: `2`

## Замечание о расширении

В `app/schemas/ticket_event.py` предусмотрены дополнительные поля (`ip_address`, `metadata`, `is_system`) и расширенный набор `EventType`.
Если эти сценарии уже нужны, их стоит добавить в модель и миграции отдельным шагом.
