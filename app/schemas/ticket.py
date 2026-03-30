from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.ticket import Priority


class TicketBase(BaseModel):
    track_id: str
    customer_name: str
    customer_email: str
    customer_ip: str
    department_id: int
    language_id: int | None = None
    category_id: int | None = None
    status_id: int = 1
    priority: Priority = Priority.normal
    subject: str
    preview_message: str | None = None
    owner_id: int | None = None
    opened_by_id: int | None = None
    first_responded_at: datetime | None = None
    closed_at: datetime | None = None
    closed_by_id: int | None = None
    is_archived: bool = False
    is_locked: bool = False
    merged_into_id: int | None = None
    messages_count: int = 0
    attachments_count: int = 0


class TicketCreate(TicketBase):
    pass


class TicketUpdate(BaseModel):
    customer_name: str | None = None
    customer_email: str | None = None
    customer_ip: str | None = None
    department_id: int | None = None
    language_id: int | None = None
    category_id: int | None = None
    status_id: int | None = None
    priority: Priority | None = None
    subject: str | None = None
    preview_message: str | None = None
    owner_id: int | None = None
    opened_by_id: int | None = None
    first_responded_at: datetime | None = None
    closed_at: datetime | None = None
    closed_by_id: int | None = None
    is_archived: bool | None = None
    is_locked: bool | None = None
    merged_into_id: int | None = None
    messages_count: int | None = None
    attachments_count: int | None = None


class TicketRead(TicketBase):
    id: int
    created_at: datetime | None = None
    updated_at: datetime | None = None
    unread_count: int | None = None

    model_config = ConfigDict(from_attributes=True)
