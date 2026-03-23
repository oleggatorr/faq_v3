from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.ticket_event import EventType, TicketEvent


class TicketEventService:
    """
    Service responsible for creating `ticket_events` records.
    """

    def __init__(self, session: Session):
        self.session = session

    def add_event(
        self,
        *,
        ticket_id: int,
        agent_id: int | None,
        action_type: EventType,
        field_name: str | None = None,
        old_value: str | None = None,
        new_value: str | None = None,
        comment: str | None = None,
    ) -> TicketEvent:
        event = TicketEvent(
            ticket_id=ticket_id,
            agent_id=agent_id,
            action_type=action_type,
            field_name=field_name,
            old_value=old_value,
            new_value=new_value,
            comment=comment,
        )
        self.session.add(event)
        return event

