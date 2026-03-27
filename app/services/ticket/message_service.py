from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.models.ticket import Ticket
from app.models.message import Message
from app.schemas.deletion import DeleteResponse
from app.schemas.message import MessageCreate, MessageRead, MessageUpdate

from app.services.ticket.ticket_event_service import TicketEventService
from app.services.errors import NotFound
from app.services.utils import apply_filters, apply_sort
from app.models.ticket_event import EventType


class MessageService:
    """
    Message domain operations.

    Notes:
    - User/operator messages are stored in `messages`.
    - Operator "notes" are implemented as messages with `is_internal = true`.
    """

    def __init__(
        self,
        session: Session,
        *,
        ticket_event_service: TicketEventService | None = None,
    ):
        self.session = session
        self.ticket_event_service = ticket_event_service

    def add_message(
        self,
        *,
        message_data: MessageCreate,
        agent_id: int | None,
        commit: bool = True,
    ) -> Message:
        """
        Add a message to a ticket.

        This method will be implemented with:
        - permission checks (via `OperatorPermissionsService`)
        - ticket state checks
        - update of `tickets.messages_count`
        - creation of audit events (via `TicketEventService`)
        """
        ticket = self.session.query(Ticket).filter(Ticket.id == message_data.ticket_id).one_or_none()
        if ticket is None:
            raise NotFound("Ticket not found")

        if agent_id is None:
            # Сообщение от клиента
            customer_name = ticket.customer_name
            customer_email = ticket.customer_email
            sender_name = ticket.customer_name  # ФИО отправителя = имя клиента
            print(f"DEBUG: Client message - ticket.customer_name={repr(ticket.customer_name)}, sender_name={repr(sender_name)}")
        else:
            # Сообщение от агента
            from app.models.agent import Agent
            agent = self.session.query(Agent).filter(Agent.id == agent_id).one_or_none()
            customer_name = None
            customer_email = None
            sender_name = agent.full_name if agent else None  # ФИО отправителя = ФИО агента

        message = Message(
            ticket_id=message_data.ticket_id,
            agent_id=agent_id,
            sender_name=sender_name,  # Заполняем ФИО отправителя
            customer_name=customer_name,
            customer_email=customer_email,
            subject=message_data.subject,
            body=message_data.body,
            is_internal=message_data.is_internal,
            is_automatic=message_data.is_automatic,
            ip_address=message_data.ip_address,
        )
        self.session.add(message)
        self.session.flush()  # message.id

        ticket.messages_count = (ticket.messages_count or 0) + 1

        now = datetime.now(timezone.utc)
        if not message.is_internal and ticket.first_responded_at is None:
            ticket.first_responded_at = now

        if self.ticket_event_service is not None:
            if message.is_internal:
                action_type = EventType.note_added
            else:
                action_type = EventType.customer_replied if agent_id is None else EventType.replied

            self.ticket_event_service.add_event(
                ticket_id=ticket.id,
                agent_id=agent_id,
                action_type=action_type,
                field_name="body",
                old_value=None,
                new_value=message.body[:500] if message.body is not None else None,
                comment=f"message_id={message.id}",
            )

        if commit:
            self.session.commit()
        else:
            self.session.flush()

        return message

    def edit_internal_note(
        self,
        *,
        message_id: int,
        new_body: str,
        agent_id: int | None,
        commit: bool = True,
    ) -> Message:
        msg = self.session.query(Message).filter(Message.id == message_id).one_or_none()
        if msg is None:
            raise NotFound("Message not found")
        if not msg.is_internal:
            raise NotFound("Message is not an internal note")

        ticket_id = msg.ticket_id
        old_body = msg.body
        msg.body = new_body

        if self.ticket_event_service is not None:
            self.ticket_event_service.add_event(
                ticket_id=ticket_id,
                agent_id=agent_id,
                action_type=EventType.note_added,
                field_name="body",
                old_value=(old_body or "")[:500],
                new_value=(new_body or "")[:500],
                comment=f"note_edit message_id={msg.id}",
            )

        if commit:
            self.session.commit()
        else:
            self.session.flush()

        return msg

    def delete_internal_note(
        self,
        *,
        message_id: int,
        agent_id: int | None,
        commit: bool = True,
    ) -> None:
        msg = self.session.query(Message).filter(Message.id == message_id).one_or_none()
        if msg is None:
            return None
        if not msg.is_internal:
            raise NotFound("Message is not an internal note")

        ticket = self.session.query(Ticket).filter(Ticket.id == msg.ticket_id).one_or_none()
        if ticket is not None:
            ticket.messages_count = max((ticket.messages_count or 0) - 1, 0)

        if self.ticket_event_service is not None:
            self.ticket_event_service.add_event(
                ticket_id=msg.ticket_id,
                agent_id=agent_id,
                action_type=EventType.note_added,
                field_name="body",
                old_value=(msg.body or "")[:500],
                new_value=None,
                comment=f"note_delete message_id={msg.id}",
            )

        self.session.delete(msg)
        if commit:
            self.session.commit()
        else:
            self.session.flush()
        return None

    def get(self, *, message_id: int) -> MessageRead:
        msg = self.session.query(Message).filter(Message.id == message_id).one_or_none()
        if msg is None:
            raise NotFound("Message not found")
        return MessageRead.model_validate(msg)

    def list(
        self,
        *,
        filters: dict[str, Any] | None = None,
        sort_by: str = "id",
        sort_desc: bool = False,
        limit: int = 100,
        offset: int = 0,
    ) -> list[MessageRead]:
        allowed_filters = {
            "id",
            "ticket_id",
            "agent_id",
            "customer_name",
            "customer_email",
            "subject",
            "is_internal",
            "is_automatic",
            "ip_address",
        }
        allowed_sort = {
            "id",
            "ticket_id",
            "agent_id",
            "created_at",
            "is_internal",
            "is_automatic",
        }

        if filters:
            unknown = set(filters.keys()) - allowed_filters
            if unknown:
                raise ValueError(f"Unknown filter fields: {', '.join(sorted(unknown))}")

        query = self.session.query(Message)
        query = apply_filters(
            query,
            Message,
            filters=filters,
            text_like_fields={"customer_name", "customer_email", "subject"},
        )
        query = apply_sort(
            query,
            Message,
            sort_by=sort_by,
            sort_desc=sort_desc,
            allowed_sort_fields=allowed_sort,
        )
        msgs = query.offset(offset).limit(limit).all()
        return [MessageRead.model_validate(m) for m in msgs]

    def update(
        self,
        *,
        message_id: int,
        message_data: MessageUpdate,
        agent_id: int | None,
        commit: bool = True,
    ) -> Message:
        msg = self.session.query(Message).filter(Message.id == message_id).one_or_none()
        if msg is None:
            raise NotFound("Message not found")

        old_body = msg.body
        updates = message_data.model_dump(exclude_none=True)
        for k, v in updates.items():
            setattr(msg, k, v)

        if self.ticket_event_service is not None and "body" in updates:
            if msg.is_internal:
                action_type = EventType.note_added
            else:
                action_type = EventType.customer_replied if agent_id is None else EventType.replied

            self.ticket_event_service.add_event(
                ticket_id=msg.ticket_id,
                agent_id=agent_id,
                action_type=action_type,
                field_name="body",
                old_value=(old_body or "")[:500],
                new_value=(msg.body or "")[:500] if msg.body is not None else None,
                comment=f"message_update message_id={msg.id}",
            )

        if commit:
            self.session.commit()
        else:
            self.session.flush()
        return msg

    def delete(
        self,
        *,
        message_id: int,
        agent_id: int | None,
        commit: bool = True,
    ) -> DeleteResponse:
        msg = self.session.query(Message).filter(Message.id == message_id).one_or_none()
        if msg is None:
            return DeleteResponse(success=False, deleted_id=None, detail="Message not found")

        old_body = msg.body
        ticket = self.session.query(Ticket).filter(Ticket.id == msg.ticket_id).one_or_none()
        if ticket is not None:
            ticket.messages_count = max((ticket.messages_count or 0) - 1, 0)

        if self.ticket_event_service is not None:
            if msg.is_internal:
                action_type = EventType.note_added
            else:
                action_type = EventType.customer_replied if agent_id is None else EventType.replied

            self.ticket_event_service.add_event(
                ticket_id=msg.ticket_id,
                agent_id=agent_id,
                action_type=action_type,
                field_name="body",
                old_value=(old_body or "")[:500],
                new_value=None,
                comment=f"message_delete message_id={msg.id}",
            )

        self.session.delete(msg)
        if commit:
            self.session.commit()
        else:
            self.session.flush()

        return DeleteResponse(success=True, deleted_id=message_id)

