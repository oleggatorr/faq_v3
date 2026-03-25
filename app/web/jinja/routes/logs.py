from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.core.auth import check_audit_logs_view
from app.models import get_db
from app.schemas.agent import AgentRead
from app.services.audit_log_service import AuditLogService

from .main import templates

router = APIRouter(prefix="", tags=["audit_logs"])


@router.get("/logs", response_class=HTMLResponse)
def logs_list(
    request: Request,
    agent: AgentRead = Depends(check_audit_logs_view),
    db: Session = Depends(get_db),
    action: str | None = Query(None),
    entity_type: str | None = Query(None),
    agent_id: int | None = Query(None),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """Страница просмотра аудиторских логов."""
    
    log_service = AuditLogService(db)
    
    # Получаем логи с фильтрацией
    logs = log_service.get_list(
        agent_id=agent_id,
        action=action,
        entity_type=entity_type,
        limit=limit,
        offset=offset,
    )
    
    # Получаем общее количество для пагинации
    total_count = log_service.get_count(
        agent_id=agent_id,
        action=action,
        entity_type=entity_type,
    )
    
    # Список всех агентов для фильтра
    from app.services.agent_service import AgentService
    agent_service = AgentService(db)
    all_agents = agent_service.list(limit=500)
    
    return templates.TemplateResponse(
        "logs/list.html",
        {
            "request": request,
            "agent": agent,
            "logs": logs,
            "action_filter": action,
            "entity_type_filter": entity_type,
            "agent_id_filter": agent_id,
            "all_agents": all_agents,
            "total_count": total_count,
            "offset": offset,
            "limit": limit,
            **agent.get_permissions_dict(),
        },
    )
