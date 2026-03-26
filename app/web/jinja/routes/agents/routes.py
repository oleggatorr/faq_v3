from __future__ import annotations

from fastapi import APIRouter, Depends, Form, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.core.audit import get_client_info
from app.core.auth import (
    check_agent_create,
    check_agent_delete,
    check_agent_edit,
    check_agent_view,
    CurrentAgent,
)
from app.core.permissions import (
    DEFAULT_OPERATOR_PERMISSIONS,
    Permission,
    PERMISSION_LABELS,
)
from app.models import get_db
from app.models.agent import Agent
from app.models.question_category import QuestionCategory
from app.schemas.agent import AgentCreate, AgentUpdate
from app.services.agent_service import AgentService
from app.services.audit_log_service import AuditLogService
from app.services.department_service import DepartmentService

from ..main import templates
from ..utils import _agent_filters

router = APIRouter(prefix="", tags=["agents"])


@router.get("/agents", response_class=HTMLResponse)
def agents_list(
    request: Request,
    agent: AgentRead = Depends(check_agent_view),
    db: Session = Depends(get_db),
    sort_by: str = Query("id"),
    sort_desc: bool = Query(False),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    agent_service = AgentService(db)
    filters = _agent_filters(request)

    # Получаем общее количество один раз
    total_agents = agent_service.list(filters=filters if filters else None, limit=999999)
    
    # Получаем страницу
    agents = agent_service.list(
        filters=filters if filters else None,
        sort_by=sort_by,
        sort_desc=sort_desc,
        limit=limit,
        offset=offset,
    )

    # Получаем список категорий для фильтра
    categories = db.query(QuestionCategory).filter(
        QuestionCategory.is_active == True
    ).order_by(QuestionCategory.name).all()

    return templates.TemplateResponse(
        "agents/list.html",
        {
            "request": request,
            "agents": agents,
            "agent": agent,
            "categories": categories,
            "total_count": len(total_agents),
            "sort_by": sort_by,
            "sort_desc": sort_desc,
            "search_query": request.query_params.get("search", ""),
            "offset": offset,
            "limit": limit,
            **agent.get_permissions_dict(),
        },
    )


@router.get("/agents/add", response_class=HTMLResponse)
def add_agent_form(
    request: Request,
    agent: AgentRead = Depends(check_agent_create),
    db: Session = Depends(get_db),
):
    # Получаем список категорий вопросов
    categories = db.query(QuestionCategory).filter(
        QuestionCategory.is_active == True
    ).order_by(QuestionCategory.name).all()
    
    # Получаем список департаментов для основного департамента агента
    dept_service = DepartmentService(db)
    departments = dept_service.list(
        filters={"is_active": True},
        sort_by="name",
        limit=200,
    )

    return templates.TemplateResponse(
        "agents/add.html",
        {
            "request": request,
            "agent": agent,
            "categories": categories,
            "departments": departments,
            "error": None,
            "permissions_list": list(Permission),
            "permission_labels": PERMISSION_LABELS,
            "form_data": None,
            **agent.get_permissions_dict(),
        },
    )


@router.post("/agents/add", response_class=HTMLResponse)
def add_agent_submit(
    request: Request,
    agent: AgentRead = Depends(check_agent_create),
    db: Session = Depends(get_db),
    full_name: str = Form(...),
    login: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    password_confirm: str = Form(...),
    role: str = Form(...),
    department_id: int = Form(...),
    category_access: list[str] = Form(default=[]),
    permissions: list[str] = Form(default=[]),
    phone: str | None = Form(None),
):
    agent_service = AgentService(db)
    
    # Если права не выбраны вручную, выдаём права по умолчанию для оператора
    if not permissions and role == "operator":
        permissions = [p.value for p in DEFAULT_OPERATOR_PERMISSIONS]
    
    # Проверка совпадения паролей
    if password != password_confirm:
        categories = db.query(QuestionCategory).filter(
            QuestionCategory.is_active == True
        ).order_by(QuestionCategory.name).all()
        dept_service = DepartmentService(db)
        departments = dept_service.list(
            filters={"is_active": True},
            sort_by="name",
            limit=200,
        )
        return templates.TemplateResponse(
            "agents/add.html",
            {
                "request": request,
                "agent": agent,
                "error": "Пароли не совпадают",
                "categories": categories,
                "departments": departments,
                "permissions_list": list(Permission),
                "permission_labels": PERMISSION_LABELS,
                "form_data": {
                    "full_name": full_name,
                    "login": login,
                    "email": email,
                    "role": role,
                    "department_id": department_id,
                    "phone": phone,
                    "category_access": category_access,
                    "permissions": permissions,
                },
            },
            status_code=400,
        )

    # Проверка на дубликаты
    existing_by_email = db.query(Agent).filter(Agent.email == email.strip().lower()).first()
    existing_by_login = db.query(Agent).filter(Agent.login == login.strip()).first()

    if existing_by_email:
        error_msg = "Агент с таким email уже существует"
    elif existing_by_login:
        error_msg = "Агент с таким логином уже существует"
    else:
        error_msg = None

    if error_msg:
        categories = db.query(QuestionCategory).filter(
            QuestionCategory.is_active == True
        ).order_by(QuestionCategory.name).all()
        dept_service = DepartmentService(db)
        departments = dept_service.list(
            filters={"is_active": True},
            sort_by="name",
            limit=200,
        )
        return templates.TemplateResponse(
            "agents/add.html",
            {
                "request": request,
                "agent": agent,
                "error": error_msg,
                "categories": categories,
                "departments": departments,
                "permissions_list": list(Permission),
                "permission_labels": PERMISSION_LABELS,
                "form_data": {
                    "full_name": full_name,
                    "login": login,
                    "email": email,
                    "role": role,
                    "department_id": department_id,
                    "phone": phone,
                    "category_access": category_access,
                    "permissions": permissions,
                },
            },
            status_code=400,
        )
    
    try:
        if role == "admin":
            category_access_str = ""
            permissions_str = ""
        else:
            category_access_str = ",".join(category_access)
            permissions_str = ",".join(permissions)

        from app.core.security import hash_password

        agent_data = AgentCreate(
            full_name=full_name.strip(),
            login=login.strip(),
            email=email.strip().lower(),
            password_hash=hash_password(password),
            role=role,
            department_id=department_id,
            category_access=category_access_str,
            permissions=permissions_str,
            is_active=True,
            phone=phone.strip() if phone else None,
        )

        agent_service.create(agent_data=agent_data)

        # Логируем создание агента
        client_info = get_client_info(request)
        log_service = AuditLogService(db)
        log_service.log_action(
            action="create",
            entity_type="agent",
            entity_id=None,
            agent_id=agent.id,
            details={
                "full_name": full_name,
                "login": login,
                "email": email,
                "role": role,
            },
            **client_info,
        )

        return RedirectResponse(url="/agents", status_code=303)

    except Exception as e:
        categories = db.query(QuestionCategory).filter(
            QuestionCategory.is_active == True
        ).order_by(QuestionCategory.name).all()
        dept_service = DepartmentService(db)
        departments = dept_service.list(
            filters={"is_active": True},
            sort_by="name",
            limit=200,
        )
        return templates.TemplateResponse(
            "agents/add.html",
            {
                "request": request,
                "agent": agent,
                "error": str(e),
                "categories": categories,
                "departments": departments,
                "permissions_list": list(Permission),
                "permission_labels": PERMISSION_LABELS,
                "form_data": {
                    "full_name": full_name,
                    "login": login,
                    "email": email,
                    "role": role,
                    "department_id": department_id,
                    "phone": phone,
                    "category_access": category_access,
                    "permissions": permissions,
                },
                **agent.get_permissions_dict(),
            },
            status_code=400,
        )


@router.get("/agents/{agent_id}/edit", response_class=HTMLResponse)
def edit_agent_form(
    request: Request,
    agent_id: int,
    agent: AgentRead = Depends(check_agent_edit),
    db: Session = Depends(get_db),
):
    agent_service = AgentService(db)

    target_agent = agent_service.get(agent_id=agent_id)

    # Получаем список категорий вопросов
    categories = db.query(QuestionCategory).filter(
        QuestionCategory.is_active == True
    ).order_by(QuestionCategory.name).all()
    
    # Получаем список департаментов для основного департамента агента
    dept_service = DepartmentService(db)
    departments = dept_service.list(
        filters={"is_active": True},
        sort_by="name",
        limit=200,
    )

    selected_categories = target_agent.category_access.split(",") if target_agent.category_access else []
    selected_permissions = target_agent.permissions.split(",") if target_agent.permissions else []

    return templates.TemplateResponse(
        "agents/edit.html",
        {
            "request": request,
            "agent": agent,
            "target_agent": target_agent,
            "categories": categories,
            "departments": departments,
            "error": None,
            "permissions_list": list(Permission),
            "permission_labels": PERMISSION_LABELS,
            "selected_categories": selected_categories,
            "selected_permissions": selected_permissions,
            **agent.get_permissions_dict(),
        },
    )


@router.post("/agents/{agent_id}/edit", response_class=HTMLResponse)
def edit_agent_submit(
    request: Request,
    agent_id: int,
    agent: AgentRead = Depends(check_agent_edit),
    db: Session = Depends(get_db),
    full_name: str = Form(...),
    login: str = Form(...),
    email: str = Form(...),
    password: str = Form(None),
    password_confirm: str = Form(None),
    role: str = Form(...),
    department_id: int = Form(...),
    category_access: list[str] = Form(default=[]),
    permissions: list[str] = Form(default=[]),
    phone: str | None = Form(None),
    is_active: bool = Form(False),
):
    agent_service = AgentService(db)
    
    # Если права не выбраны вручную, выдаём права по умолчанию для оператора
    if not permissions and role == "operator":
        permissions = [p.value for p in DEFAULT_OPERATOR_PERMISSIONS]

    # Проверка совпадения паролей
    if password or password_confirm:
        if password != password_confirm:
            categories = db.query(QuestionCategory).filter(
                QuestionCategory.is_active == True
            ).order_by(QuestionCategory.name).all()
            dept_service = DepartmentService(db)
            departments = dept_service.list(
                filters={"is_active": True},
                sort_by="name",
                limit=200,
            )
            target_agent = agent_service.get(agent_id=agent_id)
            return templates.TemplateResponse(
                "agents/edit.html",
                {
                    "request": request,
                    "agent": agent,
                    "target_agent": target_agent,
                    "categories": categories,
                    "departments": departments,
                    "error": "Пароли не совпадают",
                    "permissions_list": list(Permission),
                    "permission_labels": PERMISSION_LABELS,
                    "selected_categories": category_access,
                    "selected_permissions": permissions,
                    **agent.get_permissions_dict(),
                },
                status_code=400,
            )

    try:
        if role == "admin":
            category_access_str = ""
            permissions_str = ""
        else:
            category_access_str = ",".join(category_access)
            permissions_str = ",".join(permissions)

        from app.core.security import hash_password

        update_data = {
            "full_name": full_name.strip(),
            "login": login.strip(),
            "email": email.strip().lower(),
            "role": role,
            "department_id": department_id,
            "category_access": category_access_str,
            "permissions": permissions_str,
            "phone": phone.strip() if phone else None,
            "is_active": is_active,
        }

        if password and password.strip():
            update_data["password_hash"] = hash_password(password)

        agent_service.update(
            agent_id=agent_id,
            agent_data=AgentUpdate(**update_data),
        )
        
        # Логируем редактирование агента
        client_info = get_client_info(request)
        log_service = AuditLogService(db)
        log_service.log_action(
            action="update",
            entity_type="agent",
            entity_id=agent_id,
            agent_id=agent.id,
            details={
                "full_name": full_name,
                "login": login,
                "email": email,
                "role": role,
                "is_active": is_active,
                "password_changed": bool(password and password.strip()),
            },
            **client_info,
        )
        
        return RedirectResponse(url="/agents", status_code=303)

    except Exception as e:
        categories = db.query(QuestionCategory).filter(
            QuestionCategory.is_active == True
        ).order_by(QuestionCategory.name).all()
        dept_service = DepartmentService(db)
        departments = dept_service.list(
            filters={"is_active": True},
            sort_by="name",
            limit=200,
        )
        target_agent = agent_service.get(agent_id=agent_id)

        return templates.TemplateResponse(
            "agents/edit.html",
            {
                "request": request,
                "agent": agent,
                "target_agent": target_agent,
                "categories": categories,
                "departments": departments,
                "error": str(e),
                "permissions_list": list(Permission),
                "permission_labels": PERMISSION_LABELS,
                "selected_categories": category_access,
                "selected_permissions": permissions,
                **agent.get_permissions_dict(),
            },
            status_code=400,
        )


@router.post("/agents/{agent_id}/delete", response_class=HTMLResponse)
def delete_agent(
    request: Request,
    agent_id: int,
    agent: AgentRead = Depends(check_agent_delete),
    db: Session = Depends(get_db),
):
    if agent.id == agent_id:
        return templates.TemplateResponse(
            "agents/list.html",
            {
                "request": request,
                "agents": AgentService(db).list(limit=50),
                "agent": agent,
                "error": "Нельзя удалить самого себя!",
            },
            status_code=403,
        )

    agent_service = AgentService(db)
    result = agent_service.delete(agent_id=agent_id)

    if result.success:
        # Логируем удаление агента
        client_info = get_client_info(request)
        log_service = AuditLogService(db)
        log_service.log_action(
            action="delete",
            entity_type="agent",
            entity_id=agent_id,
            agent_id=agent.id,
            details={"deleted_agent_id": agent_id},
            **client_info,
        )
        
        return RedirectResponse(url="/agents", status_code=303)
    else:
        return templates.TemplateResponse(
            "agents/list.html",
            {
                "request": request,
                "agents": agent_service.list(limit=50),
                "agent": agent,
                "error": result.detail or "Ошибка при удалении",
            },
            status_code=400,
        )
