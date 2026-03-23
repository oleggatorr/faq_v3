from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AttachmentBase(BaseModel):
    message_id: int
    original_filename: str
    stored_filename: str
    file_path: str
    file_size: int
    mime_type: str
    file_hash: str | None = None
    uploaded_by_agent_id: int | None = None
    download_count: int = 0


class AttachmentCreate(AttachmentBase):
    pass


class AttachmentUpdate(BaseModel):
    original_filename: str | None = None
    stored_filename: str | None = None
    file_path: str | None = None
    file_size: int | None = None
    mime_type: str | None = None
    file_hash: str | None = None
    uploaded_by_agent_id: int | None = None
    download_count: int | None = None


class AttachmentRead(AttachmentBase):
    id: int
    uploaded_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)
