from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.core.auth import CurrentAgent
from app.models import get_db
from app.services.language_service import LanguageService

from ..main import templates
from ..utils import _language_filters

router = APIRouter(prefix="", tags=["lookups"])


@router.get("/lookups/languages", response_class=HTMLResponse)
def languages_list(
    request: Request,
    agent: CurrentAgent,
    db: Session = Depends(get_db),
    sort_by: str = Query("sort_order"),
    sort_desc: bool = Query(False),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    language_service = LanguageService(db)
    filters = _language_filters(request)
    languages = language_service.list(
        filters=filters if filters else None,
        sort_by=sort_by,
        sort_desc=sort_desc,
        limit=limit,
        offset=offset,
    )
    return templates.TemplateResponse(
        "lookups/languages.html",
        {"request": request, "languages": languages, "agent": agent},
    )
