from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

router = APIRouter(prefix="", tags=["jinja"])

templates_dir = Path(__file__).resolve().parent / "templates"
templates = Jinja2Templates(directory=str(templates_dir))


@router.get("/", response_class=HTMLResponse)
def index(request: Request):
    # Public home page (placeholder).
    return templates.TemplateResponse("index.html", {"request": request})


@router.get("/tickets", response_class=HTMLResponse)
def tickets_list(request: Request):
    # Placeholder: later will accept filters/sort and call TicketService.
    return templates.TemplateResponse(
        "tickets/list.html",
        {"request": request, "tickets": []},
    )


@router.get("/tickets/{ticket_id}", response_class=HTMLResponse)
def tickets_detail(request: Request, ticket_id: int):
    # Placeholder: later will load ticket + messages + events.
    return templates.TemplateResponse(
        "tickets/detail.html",
        {"request": request, "ticket_id": ticket_id},
    )


@router.get("/agents", response_class=HTMLResponse)
def agents_list(request: Request):
    return templates.TemplateResponse(
        "agents/list.html",
        {"request": request, "agents": []},
    )


@router.get("/departments", response_class=HTMLResponse)
def departments_list(request: Request):
    return templates.TemplateResponse(
        "departments/list.html",
        {"request": request, "departments": []},
    )


@router.get("/lookups/languages", response_class=HTMLResponse)
def languages_list(request: Request):
    return templates.TemplateResponse(
        "lookups/languages.html",
        {"request": request, "languages": []},
    )

