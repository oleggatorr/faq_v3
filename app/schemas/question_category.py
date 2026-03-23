from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class QuestionCategoryBase(BaseModel):
    name: str
    description: str | None = None
    department_id: int | None = None
    parent_id: int | None = None
    icon: str | None = None
    color: str = "#999999"
    is_active: bool = True
    sort_order: int = 0


class QuestionCategoryCreate(QuestionCategoryBase):
    pass


class QuestionCategoryUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    department_id: int | None = None
    parent_id: int | None = None
    icon: str | None = None
    color: str | None = None
    is_active: bool | None = None
    sort_order: int | None = None


class QuestionCategoryRead(QuestionCategoryBase):
    id: int
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)
