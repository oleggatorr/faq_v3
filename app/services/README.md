# Service Layer

This folder contains the service layer (business logic) of the application.

All services are designed to:
- keep HTTP/ORM details out of business logic;
- expose explicit domain operations (create/update/delete/list);
- use `ticket_events` as an audit log for key ticket-related actions.

## Common “list” contract

Most CRUD services implement the same list signature:
- `list(filters: dict[str, Any] | None, sort_by: str, sort_desc: bool, limit: int, offset: int) -> list[ReadSchema]`

Implementation details:
- `filters` is an equality filter set (string fields can be `ILIKE` if included in `text_like_fields`);
- `sort_by` is a whitelist (safe only);
- `limit/offset` are applied at SQL level.

## Implemented services

### `TicketService` (`app/services/ticket_service.py`)

Ticket CRUD + ticket mutations. Also provides audit logging by writing to `ticket_events` through `TicketEventService`.

CRUD / reads:
- `create_ticket(ticket_data: TicketCreate, commit: bool = True) -> Ticket`
- `get(ticket_id: int) -> TicketRead`
- `get_by_track_id(track_id: str) -> TicketRead`
- `list(filters, sort_by, sort_desc, limit, offset) -> list[TicketRead]`
- `update_ticket(ticket_id: int, ticket_data: TicketUpdate, agent_id: int | None, commit: bool = True) -> Ticket`
- `delete_ticket(ticket_id: int, agent_id: int | None, commit: bool = True) -> DeleteResponse` (soft-delete via `is_archived = true`)

Domain mutations (each may create `ticket_events`):
- `change_status(ticket_id, new_status_id, agent_id, commit) -> Ticket`
  - logs `status_changed` and `closed`/`reopened` depending on status closure flag
- `assign_owner(ticket_id, new_owner_id, agent_id, commit) -> Ticket`
  - logs `assigned`/`unassigned`
- `change_category(ticket_id, new_category_id, agent_id, commit) -> Ticket`
  - logs `category_changed`
- `merge_tickets(source_ticket_id, target_ticket_id, agent_id, commit) -> Ticket`
  - logs `merged`
- `set_locked(ticket_id, is_locked, agent_id, commit) -> Ticket`
  - logs `locked`/`unlocked`
- `anonymize_ticket(ticket_id, agent_id, commit) -> Ticket`
  - logs `anonymized`

Ticket creation with first message:
- `create_ticket_with_first_message(ticket_data: TicketCreate, first_message_body: str, commit: bool = True) -> (Ticket, Message)`
- `preview_message` rules: `<= 200` unchanged, `> 200` truncated to `[:200] + "..."`.

### `TicketEventService` (`app/services/ticket_event_service.py`)

Audit event persistence for `ticket_events`.

- `add_event(..., commit: bool = False) -> TicketEvent` (low-level)
- `create(event_data: TicketEventCreate, commit: bool = True) -> TicketEvent`
- `get(event_id: int) -> TicketEventRead`
- `list_by_ticket(ticket_id: int, filters, sort_by, sort_desc, limit, offset) -> list[TicketEventRead]`
- `update(event_id: int, event_data: TicketEventUpdate, commit: bool = True) -> TicketEvent`
- `delete(event_id: int, commit: bool = True) -> DeleteResponse`

### `MessageService` (`app/services/message_service.py`)

Message CRUD and ticket audit logging for message changes.

CRUD / reads:
- `add_message(message_data: MessageCreate, agent_id: int | None, commit: bool = True) -> Message`
- `edit_internal_note(message_id: int, new_body: str, agent_id: int | None, commit: bool = True) -> Message`
- `delete_internal_note(message_id: int, agent_id: int | None, commit: bool = True) -> None`
- `get(message_id: int) -> MessageRead`
- `list(filters, sort_by, sort_desc, limit, offset) -> list[MessageRead]`
- `update(message_id: int, message_data: MessageUpdate, agent_id: int | None, commit: bool = True) -> Message`
- `delete(message_id: int, agent_id: int | None, commit: bool = True) -> DeleteResponse`

Audit logging:
- internal notes (`is_internal = true`): `note_added` for add/edit/delete
- customer/operator messages:
  - `customer_replied` when `agent_id is None`
  - `replied` when `agent_id is not None`

Additionally:
- `tickets.messages_count` is incremented/decremented on create/delete.

### `AttachmentService` (`app/services/attachment_service.py`)

Attachment CRUD and ticket audit logging for attachment changes.

CRUD / reads:
- `add_attachments(message: Message, uploaded_by_agent_id: int | None, files: list[dict], commit: bool = True) -> list[Attachment]`
- `get(attachment_id: int) -> AttachmentRead`
- `list(filters, sort_by, sort_desc, limit, offset) -> list[AttachmentRead]`
- `create(attachment_data: AttachmentCreate, commit: bool = True) -> Attachment`
- `update(attachment_id: int, attachment_data: AttachmentUpdate, commit: bool = True) -> Attachment`
- `delete(attachment_id: int, commit: bool = True) -> DeleteResponse`

Audit logging:
- on add/create/delete it writes `ticket_events` with `action_type = attachment_added` when `TicketEventService` is provided.

Additionally:
- `tickets.attachments_count` is incremented/decremented.

### CRUD reference services

- `AgentService` (`app/services/agent_service.py`)
  - `create(agent_data, commit)`, `get(agent_id)`, `list(...)`, `update(agent_id, agent_data, commit)`, `delete(agent_id, commit)`
- `DepartmentService` (`app/services/department_service.py`)
  - `create`, `get`, `list`, `update`, `delete`
- `LanguageService` (`app/services/language_service.py`)
  - `create`, `get`, `list`, `update`, `delete`
- `TicketStatusService` (`app/services/ticket_status_service.py`)
  - `create`, `get`, `list`, `update`, `delete`
- `QuestionCategoryService` (`app/services/question_category_service.py`)
  - `create`, `get`, `list`, `update`, `delete`

