from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.models.language import Language
from app.schemas.deletion import DeleteResponse
from app.schemas.language import LanguageCreate, LanguageRead, LanguageUpdate

from .errors import NotFound
from .utils import apply_filters, apply_sort


class LanguageService:
    """
    Language CRUD and list with filtering/sorting.
    """

    def __init__(self, session: Session):
        self.session = session

    def create(self, *, language_data: LanguageCreate, commit: bool = True) -> Language:
        lang = Language(
            code=language_data.code,
            name=language_data.name,
            native_name=language_data.native_name,
            locale=language_data.locale,
            is_active=language_data.is_active,
            is_default=language_data.is_default,
            sort_order=language_data.sort_order,
        )
        self.session.add(lang)
        if commit:
            self.session.commit()
        else:
            self.session.flush()
        return lang

    def get(self, *, language_id: int) -> LanguageRead:
        lang = self.session.query(Language).filter(Language.id == language_id).one_or_none()
        if lang is None:
            raise NotFound("Language not found")
        return LanguageRead.model_validate(lang)

    def list(
        self,
        *,
        filters: dict[str, Any] | None = None,
        sort_by: str = "id",
        sort_desc: bool = False,
        limit: int = 100,
        offset: int = 0,
    ) -> list[LanguageRead]:
        allowed_filters = {"id", "code", "name", "is_active", "is_default", "sort_order", "locale"}
        allowed_sort = {"id", "code", "name", "is_active", "is_default", "sort_order", "created_at"}

        if filters:
            unknown = set(filters.keys()) - allowed_filters
            if unknown:
                raise ValueError(f"Unknown filter fields: {', '.join(sorted(unknown))}")

        query = self.session.query(Language)
        query = apply_filters(
            query,
            Language,
            filters=filters,
            text_like_fields={"code", "name", "locale", "native_name"},
        )
        query = apply_sort(query, Language, sort_by=sort_by, sort_desc=sort_desc, allowed_sort_fields=allowed_sort)
        items = query.offset(offset).limit(limit).all()
        return [LanguageRead.model_validate(x) for x in items]

    def update(
        self,
        *,
        language_id: int,
        language_data: LanguageUpdate,
        commit: bool = True,
    ) -> Language:
        lang = self.session.query(Language).filter(Language.id == language_id).one_or_none()
        if lang is None:
            raise NotFound("Language not found")

        updates = language_data.model_dump(exclude_none=True)
        for k, v in updates.items():
            setattr(lang, k, v)

        if commit:
            self.session.commit()
        else:
            self.session.flush()
        return lang

    def delete(
        self,
        *,
        language_id: int,
        commit: bool = True,
    ) -> DeleteResponse:
        lang = self.session.query(Language).filter(Language.id == language_id).one_or_none()
        if lang is None:
            return DeleteResponse(success=False, deleted_id=None, detail="Language not found")

        self.session.delete(lang)
        if commit:
            self.session.commit()
        else:
            self.session.flush()
        return DeleteResponse(success=True, deleted_id=language_id)

