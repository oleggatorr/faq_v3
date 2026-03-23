from __future__ import annotations

from typing import Optional

from sqlalchemy.orm import Session

from app.models.message import Message
from app.models.ticket import Ticket
from app.models.ticket_event import EventType
from app.schemas.ticket import TicketCreate, TicketRead
from app.services.errors import Conflict, NotFound
from app.services.ticket_event_service import TicketEventService
from app.services.utils import format_preview


class TicketService:
    """
    Ticket domain operations.

    Contract recap (based on `docs/06-services/index.md`):
    - `create_ticket_with_first_message`: create a ticket + first customer message
      in one workflow, including `preview_message` computed from the first body.
    """

    def __init__(
        self,
        session: Session,
        *,
        ticket_event_service: TicketEventService | None = None,
    ):
        self.session = session
        self.ticket_event_service = ticket_event_service

    def _get_by_track_id(self, track_id: str) -> Optional[Ticket]:
        return (
            self.session.query(Ticket)
            .filter(Ticket.track_id == track_id)
            .one_or_none()
        )

    def create_ticket_with_first_message(
        self,
        *,
        ticket_data: TicketCreate,
        first_message_body: str,
        commit: bool = True,
    ) -> tuple[Ticket, Message]:
        """
        Create `Ticket` and immediately create the first `Message`.

        preview rules:
        - if len(body) <= 200 -> preview = body
        - else preview = body[:200] + "..."
        """

        existing = self._get_by_track_id(ticket_data.track_id)
        if existing is not None:
            raise Conflict("track_id already exists")

        preview = format_preview(first_message_body, 200)

        # 1) create ticket
        ticket = Ticket(
            track_id=ticket_data.track_id,
            customer_name=ticket_data.customer_name,
            customer_email=ticket_data.customer_email,
            customer_ip=ticket_data.customer_ip,
            department_id=ticket_data.department_id,
            language_id=ticket_data.language_id,
            category_id=ticket_data.category_id,
            status_id=ticket_data.status_id,
            priority=ticket_data.priority,
            subject=ticket_data.subject,
            preview_message=preview,
            owner_id=ticket_data.owner_id,
            opened_by_id=ticket_data.opened_by_id,
            first_responded_at=ticket_data.first_responded_at,
            closed_at=ticket_data.closed_at,
            closed_by_id=ticket_data.closed_by_id,
            is_archived=ticket_data.is_archived,
            is_locked=ticket_data.is_locked,
            merged_into_id=ticket_data.merged_into_id,
            messages_count=1,
            attachments_count=ticket_data.attachments_count,
        )

        self.session.add(ticket)
        self.session.flush()  # populate ticket.id

        # 2) create first message
        message = Message(
            ticket_id=ticket.id,
            agent_id=None,
            customer_name=ticket.customer_name,
            customer_email=ticket.customer_email,
            subject=ticket.subject,
            body=first_message_body,
            is_internal=False,
            is_automatic=False,
            ip_address=ticket.customer_ip,
        )
        self.session.add(message)

        # 3) optionally create audit event
        if self.ticket_event_service is not None:
            self.ticket_event_service.add_event(
                ticket_id=ticket.id,
                agent_id=ticket_data.opened_by_id,
                action_type=EventType.created,
                field_name=None,
                old_value=None,
                new_value=None,
                comment=None,
            )

        if commit:
            self.session.commit()
        else:
            self.session.flush()

        return ticket, message

    # --- Other operations (interfaces for future implementation) ---

    def get_by_track_id(self, track_id: str) -> TicketRead:
        ticket = self._get_by_track_id(track_id)
        if ticket is None:
            raise NotFound("Ticket not found")
        return TicketRead.model_validate(ticket)

    def change_status(
        self,
        *,
        ticket_id: int,
        new_status_id: int,
        agent_id: int | None,
        commit: bool = True,
    ) -> Ticket:
        raise NotImplementedError

    def assign_owner(
        self,
        *,
        ticket_id: int,
        new_owner_id: int | None,
        agent_id: int | None,
        commit: bool = True,
    ) -> Ticket:
        raise NotImplementedError

    def change_category(
        self,
        *,
        ticket_id: int,
        new_category_id: int | None,
        agent_id: int | None,
        commit: bool = True,
    ) -> Ticket:
        raise NotImplementedError

    def merge_tickets(
        self,
        *,
        source_ticket_id: int,
        target_ticket_id: int,
        agent_id: int | None,
        commit: bool = True,
    ) -> Ticket:
        raise NotImplementedError

    def set_locked(
        self,
        *,
        ticket_id: int,
        is_locked: bool,
        agent_id: int | None,
        commit: bool = True,
    ) -> Ticket:
        raise NotImplementedError

    def anonymize_ticket(
        self,
        *,
        ticket_id: int,
        agent_id: int | None,
        commit: bool = True,
    ) -> Ticket:
        raise NotImplementedError

