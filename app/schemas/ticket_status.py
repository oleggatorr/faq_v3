from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class TicketStatusBase(BaseModel):
    code: str
    name: str
    color: str = "#999999"
    is_closed: bool = False
    is_default: bool = False
    sort_order: int = 0


class TicketStatusCreate(TicketStatusBase):
    pass


class TicketStatusUpdate(BaseModel):
    code: str | None = None
    name: str | None = None
    color: str | None = None
    is_closed: bool | None = None
    is_default: bool | None = None
    sort_order: int | None = None


class TicketStatusRead(TicketStatusBase):
    id: int

    model_config = ConfigDict(from_attributes=True)
