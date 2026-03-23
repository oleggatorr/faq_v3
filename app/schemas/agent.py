from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.agent import AgentRole


class AgentBase(BaseModel):
    full_name: str
    email: str
    role: AgentRole = AgentRole.operator
    category_access: str = ""
    permissions: str = ""
    department_id: int | None = None
    is_active: bool = True
    phone: str | None = None
    avatar_path: str | None = None


class AgentCreate(AgentBase):
    password_hash: str


class AgentUpdate(BaseModel):
    full_name: str | None = None
    email: str | None = None
    password_hash: str | None = None
    role: AgentRole | None = None
    category_access: str | None = None
    permissions: str | None = None
    department_id: int | None = None
    is_active: bool | None = None
    phone: str | None = None
    avatar_path: str | None = None
    last_login_at: datetime | None = None


class AgentRead(AgentBase):
    id: int
    last_login_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)
