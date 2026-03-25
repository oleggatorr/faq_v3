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

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.errors import AccessDeniedError
from app.core.permissions import Permission
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


def _check_permissions(
    request: Request,
    db: Session = Depends(get_db),
    *,  # Всё после * не передаётся как query/body параметр
    required_permissions: str = "",
) -> AgentRead:
    """
    Внутренняя зависимость для проверки прав.
    required_permissions — строка с правами через запятую.
    """
    agent = get_current_agent(request, db)
    # Админ всегда имеет все права
    if agent.role == AgentRole.admin:
        return agent
    
    if not required_permissions:
        return agent
    
    user_perms = agent._get_permissions_set()
    required = set(p.strip() for p in required_permissions.split(",") if p.strip())
    
    if not required.issubset(user_perms):
        missing = required - user_perms
        raise HTTPException(
            status_code=403,
            detail=f"Нет прав: {', '.join(missing)}"
        )
    return agent


# Явные зависимости для каждого права (чтобы FastAPI видел правильную сигнатуру)
def check_can_view_tickets(request: Request, db: Session = Depends(get_db)) -> AgentRead:
    agent = get_current_agent(request, db)
    if agent.role == AgentRole.admin:
        return agent
    if not agent.has_permission(Permission.can_view_tickets):
        raise AccessDeniedError("Нет прав доступа", required_permission="can_view_tickets")
    return agent

def check_can_submit_any_cat(request: Request, db: Session = Depends(get_db)) -> AgentRead:
    agent = get_current_agent(request, db)
    if agent.role == AgentRole.admin:
        return agent
    if not agent.has_permission(Permission.can_submit_any_cat):
        raise AccessDeniedError("Нет прав доступа", required_permission="can_submit_any_cat")
    return agent

def check_can_reply_tickets(request: Request, db: Session = Depends(get_db)) -> AgentRead:
    agent = get_current_agent(request, db)
    if agent.role == AgentRole.admin:
        return agent
    if not agent.has_permission(Permission.can_reply_tickets):
        raise AccessDeniedError("Нет прав доступа", required_permission="can_reply_tickets")
    return agent

def check_can_edit_tickets(request: Request, db: Session = Depends(get_db)) -> AgentRead:
    agent = get_current_agent(request, db)
    if agent.role == AgentRole.admin:
        return agent
    if not agent.has_permission(Permission.can_edit_tickets):
        raise AccessDeniedError("Нет прав доступа", required_permission="can_edit_tickets")
    return agent

def check_can_del_tickets(request: Request, db: Session = Depends(get_db)) -> AgentRead:
    agent = get_current_agent(request, db)
    if agent.role == AgentRole.admin:
        return agent
    if not agent.has_permission(Permission.can_del_tickets):
        raise AccessDeniedError("Нет прав доступа", required_permission="can_del_tickets")
    return agent

def check_agent_view(request: Request, db: Session = Depends(get_db)) -> AgentRead:
    agent = get_current_agent(request, db)
    if agent.role == AgentRole.admin:
        return agent
    if not agent.has_permission(Permission.agent_view):
        raise AccessDeniedError("Нет прав доступа", required_permission="agent_view")
    return agent

def check_agent_create(request: Request, db: Session = Depends(get_db)) -> AgentRead:
    agent = get_current_agent(request, db)
    if agent.role == AgentRole.admin:
        return agent
    if not agent.has_permission(Permission.agent_create):
        raise AccessDeniedError("Нет прав доступа", required_permission="agent_create")
    return agent

def check_agent_edit(request: Request, db: Session = Depends(get_db)) -> AgentRead:
    agent = get_current_agent(request, db)
    if agent.role == AgentRole.admin:
        return agent
    if not agent.has_permission(Permission.agent_edit):
        raise AccessDeniedError("Нет прав доступа", required_permission="agent_edit")
    return agent

def check_agent_delete(request: Request, db: Session = Depends(get_db)) -> AgentRead:
    agent = get_current_agent(request, db)
    if agent.role == AgentRole.admin:
        return agent
    if not agent.has_permission(Permission.agent_delete):
        raise AccessDeniedError("Нет прав доступа", required_permission="agent_delete")
    return agent

def check_audit_logs_view(request: Request, db: Session = Depends(get_db)) -> AgentRead:
    agent = get_current_agent(request, db)
    if agent.role == AgentRole.admin:
        return agent
    if not agent.has_permission(Permission.audit_logs_view):
        raise AccessDeniedError("Нет прав доступа", required_permission="audit_logs_view")
    return agent


def require_permission(*permissions: Permission) -> Depends:
    """
    Зависимость: текущий агент должен иметь указанные права.
    Администратор всегда проходит проверку.
    Для использования в роутах лучше использовать готовые алиасы ниже.
    """
    # Эта функция для динамической проверки, но для алиасов используйте явные функции выше
    perm_str = ",".join(p.value for p in permissions)
    
    def _dynamic_check(request: Request, db: Session = Depends(get_db)) -> AgentRead:
        return _check_permissions(request, db, perm_str)
    
    return Depends(_dynamic_check)


def require_any_permission(*permissions: Permission) -> Depends:
    """
    Зависимость: текущий агент должен иметь хотя бы одно из указанных прав.
    Администратор всегда проходит проверку.
    """
    perm_list = list(permissions)
    
    def _check_any(
        request: Request,
        db: Session = Depends(get_db),
    ) -> AgentRead:
        agent = get_current_agent(request, db)
        if agent.role == AgentRole.admin:
            return agent
        if not agent.has_any_permission(*perm_list):
            raise HTTPException(
                status_code=403,
                detail="Нет ни одного из требуемых прав"
            )
        return agent
    
    return Depends(_check_any)


# Алиасы для удобства в роутах
CurrentAgent = Annotated[AgentRead, Depends(get_current_agent)]
CurrentAgentOptional = Annotated[AgentRead | None, Depends(get_current_agent_optional)]

# Алиасы с проверкой прав (используют явные функции)
AgentWithTicketView = Annotated[AgentRead, Depends(check_can_view_tickets)]
AgentWithTicketCreate = Annotated[AgentRead, Depends(check_can_submit_any_cat)]
AgentWithTicketEdit = Annotated[AgentRead, Depends(check_can_edit_tickets)]
AgentWithTicketDelete = Annotated[AgentRead, Depends(check_can_del_tickets)]
AgentWithAgentView = Annotated[AgentRead, Depends(check_agent_view)]
AgentWithAgentCreate = Annotated[AgentRead, Depends(check_agent_create)]
AgentWithAgentEdit = Annotated[AgentRead, Depends(check_agent_edit)]
AgentWithAgentDelete = Annotated[AgentRead, Depends(check_agent_delete)]
AgentWithAuditLogsView = Annotated[AgentRead, Depends(check_audit_logs_view)]
