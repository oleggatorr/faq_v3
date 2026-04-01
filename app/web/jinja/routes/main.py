from pathlib import Path

from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.core.auth import CurrentAgent, CurrentAgentOptional
from app.models import get_db
from app.services.ticket.read_state_service import TicketReadStateService

templates_dir = Path(__file__).resolve().parent.parent / "templates"
templates = Jinja2Templates(directory=str(templates_dir))


def _nl2br_filter(value: str) -> str:
    """Заменяет переносы строк на <br> для безопасного HTML-вывода."""
    if not value:
        return ""
    return value.replace("\n", "<br>\n")


templates.env.filters["nl2br"] = _nl2br_filter


def _get_unread_count(agent_id: int | None = None) -> int:
    """Получить количество непрочитанных сообщений для текущего агента."""
    if not agent_id:
        return 0

    db = next(get_db())
    try:
        read_state_service = TicketReadStateService(db)
        return read_state_service.get_total_unread_for_agent(agent_id=agent_id)
    except Exception:
        return 0
    finally:
        db.close()


# Добавляем глобальную функцию для получения количества непрочитанных
templates.env.globals["get_unread_count"] = _get_unread_count


router = APIRouter(prefix="", tags=["jinja"])


@router.get("/", response_class=HTMLResponse)
def public_home(request: Request, agent: CurrentAgentOptional):
    """
    Публичная домашняя страница для неавторизованных.
    Если авторизован — редирект на /operator/home-page.
    """
    if agent:
        return RedirectResponse(url="/operator/home-page", status_code=303)

    return templates.TemplateResponse(
        "public/home.html",
        {"request": request, "agent": None},
    )


@router.get("/home-page", response_class=RedirectResponse)
def home_page(agent: CurrentAgent):
    """Для авторизованных — редирект на страницу оператора."""
    return RedirectResponse(url="/operator/home-page", status_code=303)


@router.get("/operator/home-page", response_class=HTMLResponse)
def operator_home_page(request: Request, agent: CurrentAgent, db: Session = Depends(get_db)):
    """Домашняя страница оператора (требует авторизации)."""
    from app.services.ticket.ticket_service import TicketService
    from datetime import datetime, timezone
    
    ticket_service = TicketService(db, agent_id=agent.id)
    
    # Получаем все тикеты агента для статистики
    my_tickets = ticket_service.list(
        filters={"owner_id": agent.id, "is_archived": False},
        limit=999999
    )
    
    # Считаем статистику
    total_my_tickets = len(my_tickets)
    
    # Ожидают ответа (статус "Новый" или сообщения от клиента)
    awaiting_response = len([t for t in my_tickets if t.status_id == 1])
    
    # Решено сегодня (закрытые тикеты с updated_at сегодня)
    today = datetime.now(tz=timezone.utc).date()
    solved_today = len([
        t for t in my_tickets 
        if t.is_archived and t.updated_at and t.updated_at.date() == today
    ])
    
    # В работе (не архив, не новый)
    in_progress = len([t for t in my_tickets if t.status_id not in [1] and not t.is_archived])
    
    return templates.TemplateResponse(
        "operator/home_page.html",
        {
            "request": request,
            "agent": agent,
            "stats": {
                "total_my_tickets": total_my_tickets,
                "awaiting_response": awaiting_response,
                "solved_today": solved_today,
                "in_progress": in_progress,
            }
        },
    )
