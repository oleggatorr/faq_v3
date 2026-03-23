from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.models.ticket_status import TicketStatus
from app.schemas.deletion import DeleteResponse
from app.schemas.ticket_status import TicketStatusCreate, TicketStatusRead, TicketStatusUpdate

from .errors import NotFound
from .utils import apply_filters, apply_sort


class TicketStatusService:
    """
    TicketStatus CRUD and list with filtering/sorting.
    """

    def __init__(self, session: Session):
        self.session = session

    def create(self, *, status_data: TicketStatusCreate, commit: bool = True) -> TicketStatus:
        st = TicketStatus(
            code=status_data.code,
            name=status_data.name,
            color=status_data.color,
            is_closed=status_data.is_closed,
            is_default=status_data.is_default,
            sort_order=status_data.sort_order,
        )
        self.session.add(st)
        if commit:
            self.session.commit()
        else:
            self.session.flush()
        return st

    def get(self, *, status_id: int) -> TicketStatusRead:
        st = self.session.query(TicketStatus).filter(TicketStatus.id == status_id).one_or_none()
        if st is None:
            raise NotFound("Ticket status not found")
        return TicketStatusRead.model_validate(st)

    def list(
        self,
        *,
        filters: dict[str, Any] | None = None,
        sort_by: str = "id",
        sort_desc: bool = False,
        limit: int = 100,
        offset: int = 0,
    ) -> list[TicketStatusRead]:
        allowed_filters = {"id", "code", "name", "is_closed", "is_default", "sort_order", "color"}
        allowed_sort = {"id", "code", "name", "is_closed", "is_default", "sort_order", "color"}

        if filters:
            unknown = set(filters.keys()) - allowed_filters
            if unknown:
                raise ValueError(f"Unknown filter fields: {', '.join(sorted(unknown))}")

        query = self.session.query(TicketStatus)
        query = apply_filters(
            query,
            TicketStatus,
            filters=filters,
            text_like_fields={"code", "name", "color"},
        )
        query = apply_sort(
            query,
            TicketStatus,
            sort_by=sort_by,
            sort_desc=sort_desc,
            allowed_sort_fields=allowed_sort,
        )
        items = query.offset(offset).limit(limit).all()
        return [TicketStatusRead.model_validate(x) for x in items]

    def update(
        self,
        *,
        status_id: int,
        status_data: TicketStatusUpdate,
        commit: bool = True,
    ) -> TicketStatus:
        st = self.session.query(TicketStatus).filter(TicketStatus.id == status_id).one_or_none()
        if st is None:
            raise NotFound("Ticket status not found")

        updates = status_data.model_dump(exclude_none=True)
        for k, v in updates.items():
            setattr(st, k, v)

        if commit:
            self.session.commit()
        else:
            self.session.flush()
        return st

    def delete(
        self,
        *,
        status_id: int,
        commit: bool = True,
    ) -> DeleteResponse:
        st = self.session.query(TicketStatus).filter(TicketStatus.id == status_id).one_or_none()
        if st is None:
            return DeleteResponse(success=False, deleted_id=None, detail="Ticket status not found")

        self.session.delete(st)
        if commit:
            self.session.commit()
        else:
            self.session.flush()
        return DeleteResponse(success=True, deleted_id=status_id)

