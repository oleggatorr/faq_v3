from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.core.auth import CurrentAgent
from app.models import get_db
from app.services.question_category_service import QuestionCategoryService

from ..main import templates

router = APIRouter(prefix="", tags=["question-categories"])


@router.get("/question-category-list", response_class=HTMLResponse)
def question_category_list(
    request: Request,
    agent: CurrentAgent,
    db: Session = Depends(get_db),
    sort_by: str = Query("sort_order"),
    sort_desc: bool = Query(False),
    limit: int = Query(200, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    service = QuestionCategoryService(db)
    items = service.list(
        filters={"is_active": True},
        sort_by=sort_by,
        sort_desc=sort_desc,
        limit=limit,
        offset=offset,
    )
    return templates.TemplateResponse(
        "question_categories/list.html",
        {"request": request, "agent": agent, "categories": items},
    )


@router.get("/question-category-add", response_class=HTMLResponse)
def question_category_add(request: Request, agent: CurrentAgent):
    return templates.TemplateResponse(
        "question_categories/add.html",
        {"request": request, "agent": agent},
    )


@router.get("/question-category-change", response_class=HTMLResponse)
def question_category_change(request: Request, agent: CurrentAgent):
    return templates.TemplateResponse(
        "question_categories/change.html",
        {"request": request, "agent": agent},
    )
