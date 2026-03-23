from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class MessageBase(BaseModel):
    ticket_id: int
    agent_id: int | None = None
    customer_name: str | None = None
    customer_email: str | None = None
    subject: str | None = None
    body: str
    is_internal: bool = False
    is_automatic: bool = False
    ip_address: str | None = None


class MessageCreate(MessageBase):
    pass


class MessageUpdate(BaseModel):
    agent_id: int | None = None
    customer_name: str | None = None
    customer_email: str | None = None
    subject: str | None = None
    body: str | None = None
    is_internal: bool | None = None
    is_automatic: bool | None = None
    ip_address: str | None = None


class MessageRead(MessageBase):
    id: int
    created_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)
