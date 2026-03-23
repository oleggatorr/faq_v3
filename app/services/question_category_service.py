from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.models.question_category import QuestionCategory
from app.schemas.deletion import DeleteResponse
from app.schemas.question_category import (
    QuestionCategoryCreate,
    QuestionCategoryRead,
    QuestionCategoryUpdate,
)

from .errors import NotFound
from .utils import apply_filters, apply_sort


class QuestionCategoryService:
    """
    QuestionCategory CRUD and list with filtering/sorting.
    """

    def __init__(self, session: Session):
        self.session = session

    def create(self, *, category_data: QuestionCategoryCreate, commit: bool = True) -> QuestionCategory:
        cat = QuestionCategory(
            name=category_data.name,
            description=category_data.description,
            department_id=category_data.department_id,
            parent_id=category_data.parent_id,
            icon=category_data.icon,
            color=category_data.color,
            is_active=category_data.is_active,
            sort_order=category_data.sort_order,
        )
        self.session.add(cat)
        if commit:
            self.session.commit()
        else:
            self.session.flush()
        return cat

    def get(self, *, category_id: int) -> QuestionCategoryRead:
        cat = (
            self.session.query(QuestionCategory)
            .filter(QuestionCategory.id == category_id)
            .one_or_none()
        )
        if cat is None:
            raise NotFound("Question category not found")
        return QuestionCategoryRead.model_validate(cat)

    def list(
        self,
        *,
        filters: dict[str, Any] | None = None,
        sort_by: str = "id",
        sort_desc: bool = False,
        limit: int = 100,
        offset: int = 0,
    ) -> list[QuestionCategoryRead]:
        allowed_filters = {
            "id",
            "name",
            "department_id",
            "parent_id",
            "icon",
            "color",
            "is_active",
            "sort_order",
        }
        allowed_sort = {
            "id",
            "name",
            "department_id",
            "parent_id",
            "is_active",
            "sort_order",
            "created_at",
            "updated_at",
        }

        if filters:
            unknown = set(filters.keys()) - allowed_filters
            if unknown:
                raise ValueError(f"Unknown filter fields: {', '.join(sorted(unknown))}")

        query = self.session.query(QuestionCategory)
        query = apply_filters(
            query,
            QuestionCategory,
            filters=filters,
            text_like_fields={"name", "icon", "color"},
        )
        query = apply_sort(
            query,
            QuestionCategory,
            sort_by=sort_by,
            sort_desc=sort_desc,
            allowed_sort_fields=allowed_sort,
        )
        items = query.offset(offset).limit(limit).all()
        return [QuestionCategoryRead.model_validate(x) for x in items]

    def update(
        self,
        *,
        category_id: int,
        category_data: QuestionCategoryUpdate,
        commit: bool = True,
    ) -> QuestionCategory:
        cat = self.session.query(QuestionCategory).filter(QuestionCategory.id == category_id).one_or_none()
        if cat is None:
            raise NotFound("Question category not found")

        updates = category_data.model_dump(exclude_none=True)
        for k, v in updates.items():
            setattr(cat, k, v)

        if commit:
            self.session.commit()
        else:
            self.session.flush()
        return cat

    def delete(
        self,
        *,
        category_id: int,
        commit: bool = True,
    ) -> DeleteResponse:
        cat = self.session.query(QuestionCategory).filter(QuestionCategory.id == category_id).one_or_none()
        if cat is None:
            return DeleteResponse(success=False, deleted_id=None, detail="Question category not found")

        self.session.delete(cat)
        if commit:
            self.session.commit()
        else:
            self.session.flush()
        return DeleteResponse(success=True, deleted_id=category_id)

