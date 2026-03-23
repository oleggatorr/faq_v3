# API-схемы (Pydantic)

## Назначение раздела

Раздел описывает Pydantic-схемы, которые используются в API-слое для валидации входных данных и формирования ответов.

## Структура схем

Для каждой модели определены отдельные схемы:

- `Base` - общие поля сущности.
- `Create` - данные для создания записи.
- `Update` - частичное обновление (`PATCH`-подход, поля опциональны).
- `Read` - структура ответа API.

`Read`-схемы поддерживают создание из ORM-объектов через `from_attributes=True`.

## Схемы по файлам

### Agent (`app/schemas/agent.py`)

- `AgentBase`
- `AgentCreate`
- `AgentUpdate`
- `AgentRead`

### Department (`app/schemas/department.py`)

- `DepartmentBase`
- `DepartmentCreate`
- `DepartmentUpdate`
- `DepartmentRead`

### Language (`app/schemas/language.py`)

- `LanguageBase`
- `LanguageCreate`
- `LanguageUpdate`
- `LanguageRead`

### TicketStatus (`app/schemas/ticket_status.py`)

- `TicketStatusBase`
- `TicketStatusCreate`
- `TicketStatusUpdate`
- `TicketStatusRead`

### QuestionCategory (`app/schemas/question_category.py`)

- `QuestionCategoryBase`
- `QuestionCategoryCreate`
- `QuestionCategoryUpdate`
- `QuestionCategoryRead`

### Ticket (`app/schemas/ticket.py`)

- `TicketBase`
- `TicketCreate`
- `TicketUpdate`
- `TicketRead`

### Message (`app/schemas/message.py`)

- `MessageBase`
- `MessageCreate`
- `MessageUpdate`
- `MessageRead`

### Attachment (`app/schemas/attachment.py`)

- `AttachmentBase`
- `AttachmentCreate`
- `AttachmentUpdate`
- `AttachmentRead`

### TicketEvent (`app/schemas/ticket_event.py`)

- `TicketEventBase`
- `TicketEventCreate`
- `TicketEventUpdate`
- `TicketEventRead`

### DELETE (универсально) (`app/schemas/deletion.py`)

- `DeleteResponse`
