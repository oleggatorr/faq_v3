from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.core.auth import CurrentAgent, CurrentAgentOptional
from app.models import get_db
from app.services.ticket.read_state_service import TicketReadStateService

from .main import templates

router = APIRouter(prefix="/test", tags=["test"])


@router.get("/", response_class=HTMLResponse)
def test_base(request: Request, agent: CurrentAgentOptional):
    """
    Тестовая страница для проверки base.html.
    
    Показывает работу базового шаблона с header, footer и flash-сообщениями.
    """
    return templates.TemplateResponse(
        "test/base.html",
        {
            "request": request,
            "agent": agent,
        },
    )


@router.get("/unread", response_class=HTMLResponse)
def test_unread_messages(
    request: Request,
    agent: CurrentAgent,
    db: Session = Depends(get_db),
):
    """
    Тестовая страница для проверки количества непрочитанных сообщений.

    Показывает:
    - Общее количество непрочитанных сообщений
    - Список тикетов с непрочитанными сообщениями
    """
    print(f"\n=== [DEBUG] /test/unread: agent_id={agent.id}, agent_login={agent.login}")

    read_state_service = TicketReadStateService(db)

    # Получаем общее количество непрочитанных
    total_unread = read_state_service.get_total_unread_for_agent(
        agent_id=agent.id,
        exclude_internal=True,
    )
    print(f"[DEBUG] total_unread={total_unread}")

    # Получаем список тикетов с непрочитанными
    tickets_with_unread = read_state_service.get_tickets_with_unread(
        agent_id=agent.id,
        exclude_internal=True,
        min_unread=1,
    )
    print(f"[DEBUG] tickets_with_unread={tickets_with_unread}")

    return templates.TemplateResponse(
        "test/unread.html",
        {
            "request": request,
            "agent": agent,
            "total_unread": total_unread,
            "tickets_with_unread": tickets_with_unread,
        },
    )


@router.get("/assignment", response_class=HTMLResponse)
def test_assignment(
    request: Request,
    agent: CurrentAgent,
    db: Session = Depends(get_db),
):
    """
    Тестовая страница для проверки автоназначения операторов.

    Показывает список операторов, доступных для назначения на тикет.
    """
    return templates.TemplateResponse(
        "test/assignment.html",
        {
            "request": request,
            "agent": agent,
        },
    )
