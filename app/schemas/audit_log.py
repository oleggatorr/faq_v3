from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class AuditLogBase(BaseModel):
    action: str
    entity_type: str
    entity_id: Optional[int] = None
    details: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None


class AuditLogCreate(AuditLogBase):
    agent_id: Optional[int] = None


class AuditLogRead(AuditLogBase):
    id: int
    agent_id: Optional[int] = None
    timestamp: datetime

    model_config = ConfigDict(from_attributes=True)
