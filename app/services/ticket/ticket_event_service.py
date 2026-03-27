from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.ticket_event import EventType, TicketEvent
from app.schemas.deletion import DeleteResponse
from app.schemas.ticket_event import TicketEventCreate, TicketEventRead, TicketEventUpdate
from app.services.errors import NotFound


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
        commit: bool = False,
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
        if commit:
            self.session.commit()
        return event

    def get(self, *, event_id: int) -> TicketEventRead:
        event = (
            self.session.query(TicketEvent)
            .filter(TicketEvent.id == event_id)
            .one_or_none()
        )
        if event is None:
            raise NotFound("Ticket event not found")
        return TicketEventRead.model_validate(event)

    def list_by_ticket(
        self,
        *,
        ticket_id: int,
        filters: dict[str, object] | None = None,
        sort_by: str = "occurred_at",
        sort_desc: bool = True,
        limit: int = 100,
        offset: int = 0,
    ) -> list[TicketEventRead]:
        query = self.session.query(TicketEvent).filter(TicketEvent.ticket_id == ticket_id)

        if filters:
            # Allow filtering by a subset of columns.
            allowed = {"agent_id", "action_type", "field_name"}
            for k in filters.keys():
                if k not in allowed:
                    raise ValueError(f"Unknown filter field: {k}")

            if "agent_id" in filters and filters["agent_id"] is not None:
                query = query.filter(TicketEvent.agent_id == filters["agent_id"])
            if "action_type" in filters and filters["action_type"] is not None:
                query = query.filter(TicketEvent.action_type == filters["action_type"])
            if "field_name" in filters and filters["field_name"] is not None:
                query = query.filter(TicketEvent.field_name == filters["field_name"])

        allowed_sort = {"id", "occurred_at", "action_type", "field_name", "agent_id"}
        if sort_by not in allowed_sort:
            raise ValueError(f"Sort field is not allowed: {sort_by}")

        column = getattr(TicketEvent, sort_by)
        query = query.order_by(column.desc() if sort_desc else column.asc())

        events = query.offset(offset).limit(limit).all()
        return [TicketEventRead.model_validate(e) for e in events]

    def create(
        self,
        *,
        event_data: TicketEventCreate,
        commit: bool = True,
    ) -> TicketEvent:
        return self.add_event(
            ticket_id=event_data.ticket_id,
            agent_id=event_data.agent_id,
            action_type=event_data.action_type,
            field_name=event_data.field_name,
            old_value=event_data.old_value,
            new_value=event_data.new_value,
            comment=event_data.comment,
            commit=commit,
        )

    def update(
        self,
        *,
        event_id: int,
        event_data: TicketEventUpdate,
        commit: bool = True,
    ) -> TicketEvent:
        event = self.session.query(TicketEvent).filter(TicketEvent.id == event_id).one_or_none()
        if event is None:
            raise NotFound("Ticket event not found")

        updates = event_data.model_dump(exclude_none=True)
        for k, v in updates.items():
            setattr(event, k, v)

        if commit:
            self.session.commit()
        else:
            self.session.flush()

        return event

    def delete(
        self,
        *,
        event_id: int,
        commit: bool = True,
    ) -> DeleteResponse:
        event = self.session.query(TicketEvent).filter(TicketEvent.id == event_id).one_or_none()
        if event is None:
            return DeleteResponse(success=False, deleted_id=None, detail="Ticket event not found")

        self.session.delete(event)
        if commit:
            self.session.commit()
        else:
            self.session.flush()
        return DeleteResponse(success=True, deleted_id=event_id)

