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


@router.post("/account/update")
def account_update(
    request: Request,
    db: Session = Depends(get_db),
    agent: CurrentAgent = None,
    full_name: str = Form(...),
    login: str = Form(...),
    email: str = Form(...),
    phone: str = Form(""),
    signature: str = Form(""),
    current_password: str = Form(...),
    new_password: str = Form(""),
):
    """Обновление профиля текущего агента."""
    # Проверка текущего пароля
    if not verify_password(current_password, agent.password_hash):
        request.session["flash_error"] = "Неверный текущий пароль"
        return RedirectResponse(url="/accaunt", status_code=303)

    # Проверка уникальности логина (если изменён)
    if login != agent.login:
        existing = db.query(Agent).filter(Agent.login == login, Agent.id != agent.id).one_or_none()
        if existing:
            request.session["flash_error"] = "Такой логин уже занят"
            return RedirectResponse(url="/accaunt", status_code=303)

    # Проверка уникальности email (если изменён)
    if email != agent.email:
        existing = db.query(Agent).filter(Agent.email == email, Agent.id != agent.id).one_or_none()
        if existing:
            request.session["flash_error"] = "Такой email уже используется"
            return RedirectResponse(url="/accaunt", status_code=303)

    # Обновление данных
    agent.full_name = full_name
    agent.login = login
    agent.email = email
    agent.phone = phone.strip() if phone else None
    agent.signature = signature.strip() if signature else None

    # Смена пароля (если указан новый)
    if new_password and new_password.strip():
        from app.core.security import get_password_hash
        agent.password_hash = get_password_hash(new_password)

    db.commit()

    # Логирование
    client_info = get_client_info(request)
    log_service = AuditLogService(db)
    log_service.log_action(
        action="profile_update",
        entity_type="agent",
        entity_id=agent.id,
        agent_id=agent.id,
        details={"changes": ["full_name", "login", "email", "phone", "signature"] + (["password"] if new_password else [])},
        **client_info,
    )

    request.session["flash_success"] = "Профиль успешно обновлён"
    return RedirectResponse(url="/accaunt", status_code=303)


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
