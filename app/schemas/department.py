from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class DepartmentBase(BaseModel):
    name: str
    description: str | None = None
    email: str | None = None
    is_active: bool = True
    sort_order: int = 0


class DepartmentCreate(DepartmentBase):
    pass


class DepartmentUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    email: str | None = None
    is_active: bool | None = None
    sort_order: int | None = None


class DepartmentRead(DepartmentBase):
    id: int
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)
