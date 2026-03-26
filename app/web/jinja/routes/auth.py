from __future__ import annotations

from urllib.parse import unquote

from fastapi import APIRouter, Depends, Form, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.core.audit import get_client_info
from app.core.auth import CurrentAgent, CurrentAgentOptional
from app.core.config import settings
from app.core.security import create_access_token, verify_password
from app.models import get_db
from app.models.agent import Agent
from app.services.audit_log_service import AuditLogService

from .main import templates

router = APIRouter(prefix="", tags=["auth"])


@router.get("/accaunt", response_class=HTMLResponse)
def account_page(request: Request, agent: CurrentAgent):
    return templates.TemplateResponse(
        "account/index.html",
        {"request": request, "agent": agent},
    )


@router.get("/login", response_class=HTMLResponse)
def login_page(
    request: Request,
    agent: CurrentAgentOptional,
    next: str = Query("/", alias="next"),
):
    if agent:
        return RedirectResponse(url=unquote(next) if next else "/", status_code=303)
    return templates.TemplateResponse(
        "auth/login.html",
        {"request": request, "next_url": next, "error": None, "agent": None},
    )


@router.post("/login")
def login_submit(
    request: Request,
    db: Session = Depends(get_db),
    login: str = Form(...),
    password: str = Form(...),
    next: str = Form("/"),
):
    agent = db.query(Agent).filter(Agent.login == login, Agent.is_active == True).one_or_none()
    
    if not agent or not verify_password(password, agent.password_hash):
        # Логируем неудачную попытку входа
        client_info = get_client_info(request)
        log_service = AuditLogService(db)
        log_service.log_action(
            action="login_failed",
            entity_type="agent",
            entity_id=None,
            agent_id=None,
            details={"login_attempt": login, "reason": "invalid_credentials"},
            **client_info,
        )

        return templates.TemplateResponse(
            "auth/login.html",
            {
                "request": request,
                "next_url": next,
                "error": "Неверный логин или пароль",
                "agent": None,
            },
            status_code=401,
        )

    # Успешный вход — логируем и обновляем время последнего входа
    from datetime import datetime, timezone
    
    # Обновляем last_login_at
    agent.last_login_at = datetime.now(timezone.utc)
    db.commit()
    
    client_info = get_client_info(request)
    log_service = AuditLogService(db)
    log_service.log_action(
        action="login",
        entity_type="agent",
        entity_id=agent.id,
        agent_id=agent.id,
        details={"method": "password"},
        **client_info,
    )

    token = create_access_token(data={"sub": str(agent.id)})
    
    # Перенаправляем с flash-сообщением
    redirect_url = unquote(next) if next else "/"
    
    response = RedirectResponse(url=redirect_url, status_code=303)
    response.set_cookie(
        key=settings.COOKIE_NAME,
        value=token,
        max_age=settings.COOKIE_MAX_AGE,
        httponly=True,
        samesite="lax",
        path="/",
        secure=False,
    )
    
    # Flash-сообщение об успешном входе
    request.session["flash_success"] = f"С возвращением, {agent.full_name}!"

    return response


@router.post("/logout", response_class=RedirectResponse)
def logout(
    request: Request,
    db: Session = Depends(get_db),
    agent: CurrentAgentOptional = None,
):
    # Логируем выход
    if agent:
        client_info = get_client_info(request)
        log_service = AuditLogService(db)
        log_service.log_action(
            action="logout",
            entity_type="agent",
            entity_id=agent.id,
            agent_id=agent.id,
            details={},
            **client_info,
        )

    response = RedirectResponse(url="/", status_code=303)
    response.delete_cookie(key=settings.COOKIE_NAME)
    
    # Flash-сообщение о выходе
    request.session["flash_info"] = "Вы успешно вышли из системы"
    
    return response
