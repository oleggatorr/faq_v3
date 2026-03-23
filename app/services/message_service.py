from __future__ import annotations

from typing import Optional

from sqlalchemy.orm import Session

from app.models.message import Message
from app.schemas.message import MessageCreate

from .ticket_event_service import TicketEventService


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
        raise NotImplementedError

    def edit_internal_note(
        self,
        *,
        message_id: int,
        new_body: str,
        agent_id: int | None,
        commit: bool = True,
    ) -> Message:
        raise NotImplementedError

    def delete_internal_note(
        self,
        *,
        message_id: int,
        agent_id: int | None,
        commit: bool = True,
    ) -> None:
        raise NotImplementedError

