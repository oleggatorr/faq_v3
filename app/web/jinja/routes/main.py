from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.core.auth import CurrentAgent, CurrentAgentOptional

templates_dir = Path(__file__).resolve().parent.parent / "templates"
templates = Jinja2Templates(directory=str(templates_dir))


def _nl2br_filter(value: str) -> str:
    """Заменяет переносы строк на <br> для безопасного HTML-вывода."""
    if not value:
        return ""
    return value.replace("\n", "<br>\n")


templates.env.filters["nl2br"] = _nl2br_filter


router = APIRouter(prefix="", tags=["jinja"])


@router.get("/", response_class=HTMLResponse)
def index(request: Request, agent: CurrentAgentOptional):
    return templates.TemplateResponse(
        "index.html",
        {"request": request, "agent": agent},
    )


@router.get("/home-page", response_class=RedirectResponse)
def home_page(agent: CurrentAgent):
    return RedirectResponse(url="/operator/home-page", status_code=303)


@router.get("/operator/home-page", response_class=HTMLResponse)
def operator_home_page(request: Request, agent: CurrentAgent):
    return templates.TemplateResponse(
        "operator/home_page.html",
        {"request": request, "agent": agent},
    )
