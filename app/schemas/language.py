from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class LanguageBase(BaseModel):
    code: str
    name: str
    native_name: str | None = None
    locale: str | None = None
    is_active: bool = True
    is_default: bool = False
    sort_order: int = 0


class LanguageCreate(LanguageBase):
    pass


class LanguageUpdate(BaseModel):
    code: str | None = None
    name: str | None = None
    native_name: str | None = None
    locale: str | None = None
    is_active: bool | None = None
    is_default: bool | None = None
    sort_order: int | None = None


class LanguageRead(LanguageBase):
    id: int
    created_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)
