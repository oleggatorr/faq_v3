from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.ticket_event import EventType


class TicketEventBase(BaseModel):
    ticket_id: int
    agent_id: int | None = None
    action_type: EventType
    field_name: str | None = None
    old_value: str | None = None
    new_value: str | None = None
    comment: str | None = None


class TicketEventCreate(TicketEventBase):
    pass


class TicketEventUpdate(BaseModel):
    agent_id: int | None = None
    action_type: EventType | None = None
    field_name: str | None = None
    old_value: str | None = None
    new_value: str | None = None
    comment: str | None = None


class TicketEventRead(TicketEventBase):
    id: int
    occurred_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)
