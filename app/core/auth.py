"""
Модуль аутентификации: зависимости для проверки прав доступа.

Использование в роутах:
- Публичный роут: без зависимостей.
- Защищённый роут: agent: AgentRead = Depends(get_current_agent)
- Опционально авторизованный: agent: AgentRead | None = Depends(get_current_agent_optional)
- С проверкой роли: agent: AgentRead = Depends(require_roles(AgentRole.admin))
"""
from __future__ import annotations

from typing import Annotated

from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import verify_password, verify_token
from app.models import get_db
from app.models.agent import Agent, AgentRole
from app.schemas.agent import AgentRead


def _get_token_from_cookie(request: Request) -> str | None:
    return request.cookies.get(settings.COOKIE_NAME)


def _load_agent_from_token(
    token: str | None,
    db: Session,
) -> AgentRead | None:
    if not token:
        return None
    payload = verify_token(token)
    if not payload:
        return None
    agent_id = payload.get("sub")
    if not agent_id:
        return None
    try:
        agent_id = int(agent_id)
    except (TypeError, ValueError):
        return None
    agent = db.query(Agent).filter(Agent.id == agent_id, Agent.is_active == True).one_or_none()
    if not agent:
        return None
    return AgentRead.model_validate(agent)


def get_current_agent_optional(
    request: Request,
    db: Session = Depends(get_db),
) -> AgentRead | None:
    """
    Возвращает текущего агента, если авторизован, иначе None.
    Не выбрасывает исключений. Используйте для публичных страниц с опциональным логином.
    """
    token = _get_token_from_cookie(request)
    return _load_agent_from_token(token, db)


def get_current_agent(
    request: Request,
    db: Session = Depends(get_db),
) -> AgentRead:
    """
    Возвращает текущего агента. Если не авторизован — HTTP 401.
    Для HTML-запросов обработчик в main.py перенаправит на /login.
    """
    agent = get_current_agent_optional(request, db)
    if agent is None:
        raise HTTPException(status_code=401, detail="Требуется авторизация")
    return agent


def require_roles(*allowed_roles: AgentRole):
    """
    Зависимость: текущий агент должен иметь одну из указанных ролей.
    Использование: agent = Depends(require_roles(AgentRole.admin))
    """

    def _check(request: Request, db: Session = Depends(get_db)) -> AgentRead:
        agent = get_current_agent(request, db)
        if agent.role not in allowed_roles:
            raise HTTPException(status_code=403, detail="Недостаточно прав")
        return agent

    return _check


# Алиасы для удобства в роутах
CurrentAgent = Annotated[AgentRead, Depends(get_current_agent)]
CurrentAgentOptional = Annotated[AgentRead | None, Depends(get_current_agent_optional)]
