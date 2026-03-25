from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.core.auth import CurrentAgent
from app.models import get_db
from app.services.department_service import DepartmentService

from ..main import templates
from ..utils import _department_filters

router = APIRouter(prefix="", tags=["departments"])


@router.get("/departments", response_class=HTMLResponse)
def departments_list(
    request: Request,
    agent: CurrentAgent,
    db: Session = Depends(get_db),
    sort_by: str = Query("id"),
    sort_desc: bool = Query(False),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    department_service = DepartmentService(db)
    filters = _department_filters(request)
    departments = department_service.list(
        filters=filters if filters else None,
        sort_by=sort_by,
        sort_desc=sort_desc,
        limit=limit,
        offset=offset,
    )
    return templates.TemplateResponse(
        "departments/list.html",
        {"request": request, "departments": departments, "agent": agent},
    )


@router.get("/department", response_class=RedirectResponse)
def departments_alias(agent: CurrentAgent):
    return RedirectResponse(url="/departments", status_code=303)
