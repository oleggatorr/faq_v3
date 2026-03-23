from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.models.department import Department
from app.schemas.department import DepartmentCreate, DepartmentRead, DepartmentUpdate
from app.schemas.deletion import DeleteResponse

from .errors import NotFound
from .utils import apply_filters, apply_sort


class DepartmentService:
    """
    Department CRUD and validations.
    """

    def __init__(self, session: Session):
        self.session = session

    def create(self, *, department_data: DepartmentCreate, commit: bool = True) -> Department:
        dept = Department(
            name=department_data.name,
            description=department_data.description,
            email=department_data.email,
            is_active=department_data.is_active,
            sort_order=department_data.sort_order,
        )
        self.session.add(dept)
        if commit:
            self.session.commit()
        else:
            self.session.flush()
        return dept

    def get(self, *, department_id: int) -> DepartmentRead:
        dept = self.session.query(Department).filter(Department.id == department_id).one_or_none()
        if dept is None:
            raise NotFound("Department not found")
        return DepartmentRead.model_validate(dept)

    def list(
        self,
        *,
        filters: dict[str, Any] | None = None,
        sort_by: str = "id",
        sort_desc: bool = False,
        limit: int = 100,
        offset: int = 0,
    ) -> list[DepartmentRead]:
        allowed_filters = {"id", "name", "email", "is_active", "sort_order"}
        allowed_sort = {"id", "name", "email", "is_active", "sort_order", "created_at", "updated_at"}

        if filters:
            unknown = set(filters.keys()) - allowed_filters
            if unknown:
                raise ValueError(f"Unknown filter fields: {', '.join(sorted(unknown))}")

        query = self.session.query(Department)
        query = apply_filters(
            query,
            Department,
            filters=filters,
            text_like_fields={"name", "email"},
        )
        query = apply_sort(query, Department, sort_by=sort_by, sort_desc=sort_desc, allowed_sort_fields=allowed_sort)
        depts = query.offset(offset).limit(limit).all()
        return [DepartmentRead.model_validate(d) for d in depts]

    def update(
        self,
        *,
        department_id: int,
        department_data: DepartmentUpdate,
        commit: bool = True,
    ) -> Department:
        dept = self.session.query(Department).filter(Department.id == department_id).one_or_none()
        if dept is None:
            raise NotFound("Department not found")

        updates = department_data.model_dump(exclude_none=True)
        for k, v in updates.items():
            setattr(dept, k, v)

        if commit:
            self.session.commit()
        else:
            self.session.flush()
        return dept

    def delete(
        self,
        *,
        department_id: int,
        commit: bool = True,
    ) -> DeleteResponse:
        dept = self.session.query(Department).filter(Department.id == department_id).one_or_none()
        if dept is None:
            return DeleteResponse(success=False, deleted_id=None, detail="Department not found")

        self.session.delete(dept)
        if commit:
            self.session.commit()
        else:
            self.session.flush()
        return DeleteResponse(success=True, deleted_id=department_id)

