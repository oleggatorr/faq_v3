# Service Layer

This folder contains the service layer (business logic) of the application.

## Main services

- `TicketService`
  - `create_ticket_with_first_message`: create `Ticket` and the first customer `Message`.
  - ticket mutations (status/assign/category/merge/lock/anonymize) are defined as interfaces for future implementation.

- `MessageService`
  - add/edit/delete internal/operator notes (messages with `is_internal = true`) - interface placeholders for now.

- `AttachmentService`
  - upload/persist attachments for a `Message` - interface placeholder for now.

- `TicketEventService`
  - write audit records to `ticket_events`.

- `OperatorPermissionsService`
  - checks `Agent.category_access` and `Agent.permissions` before executing protected operations.

## Preview message rules

`TicketService.create_ticket_with_first_message` computes:

- `preview_message = body` when `len(body) <= 200`
- `preview_message = body[:200] + "..."` when `len(body) > 200`

