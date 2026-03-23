from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.department import Department
from app.schemas.department import DepartmentCreate, DepartmentRead

from .errors import NotFound


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

