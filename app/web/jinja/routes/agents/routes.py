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
)
from app.core.permissions import (
    PERMISSION_LABELS,
    PERMISSION_GROUPS,
    Permission,
)
from app.models import get_db
from app.models.agent import Agent
from app.models.question_category import QuestionCategory
from app.schemas.agent import AgentCreate
from app.services import (
    AgentQueryService,
    AgentCreateService,
    AgentEditService,
    AgentDeleteService,
)
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
    # Используем новый сервис для просмотра
    query_service = AgentQueryService(db, current_agent_id=agent.id)
    filters = _agent_filters(request)

    # Получаем общее количество один раз
    total_agents = query_service.list(
        filters=filters if filters else None,
        limit=999999,
    )

    # Получаем страницу
    agents = query_service.list(
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
        "operator/agents/list.html",
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
        "operator/agents/add.html",
        {
            "request": request,
            "agent": agent,
            "categories": categories,
            "departments": departments,
            "error": None,
            "permissions_list": list(Permission),
            "permission_labels": PERMISSION_LABELS,
            "permission_groups": PERMISSION_GROUPS,
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
    password: str = Form(None),
    password_confirm: str = Form(None),
    role: str = Form(...),
    department_id: int = Form(...),
    category_access: list[str] = Form(default=[]),
    permissions: list[str] = Form(default=[]),
    phone: str | None = Form(None),
    is_active: str = Form("off"),
    auto_assign: str = Form("off"),
    email_notifications: str = Form("off"),
):
    # Используем новый сервис для создания
    create_service = AgentCreateService(db, current_agent_id=agent.id)

    # Проверка на пустой пароль
    if not password or not password.strip():
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
            "operator/agents/add.html",
            {
                "request": request,
                "agent": agent,
                "error": "Пароль обязателен",
                "categories": categories,
                "departments": departments,
                "permissions_list": list(Permission),
                "permission_labels": PERMISSION_LABELS,
                "permission_groups": PERMISSION_GROUPS,
                "form_data": {
                    "full_name": full_name,
                    "login": login,
                    "email": email,
                    "role": role,
                    "department_id": department_id,
                    "phone": phone,
                    "category_access": category_access,
                    "permissions": permissions,
                    "is_active": is_active == "on",
                    "auto_assign": auto_assign == "on",
                    "email_notifications": email_notifications == "on",
                },
            },
            status_code=400,
        )

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
            "operator/agents/add.html",
            {
                "request": request,
                "agent": agent,
                "error": "Пароли не совпадают",
                "categories": categories,
                "departments": departments,
                "permissions_list": list(Permission),
                "permission_labels": PERMISSION_LABELS,
                "permission_groups": PERMISSION_GROUPS,
                "form_data": {
                    "full_name": full_name,
                    "login": login,
                    "email": email,
                    "role": role,
                    "department_id": department_id,
                    "phone": phone,
                    "category_access": category_access,
                    "permissions": permissions,
                    "is_active": is_active == "on",
                    "auto_assign": auto_assign == "on",
                    "email_notifications": email_notifications == "on",
                },
            },
            status_code=400,
        )

    # Проверка на дубликаты (теперь делается в сервисе, но оставим для лучшего UX)
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
                "permission_groups": PERMISSION_GROUPS,
                "form_data": {
                    "full_name": full_name,
                    "login": login,
                    "email": email,
                    "role": role,
                    "department_id": department_id,
                    "phone": phone,
                    "category_access": category_access,
                    "permissions": permissions,
                    "is_active": is_active == "on",
                    "auto_assign": auto_assign == "on",
                    "email_notifications": email_notifications == "on",
                },
            },
            status_code=400,
        )

    try:
        # Права для админа — пустые (админ имеет все права автоматически)
        if role == "admin":
            category_access_str = ""
            permissions_str = ""
        else:
            category_access_str = ",".join(category_access)
            permissions_str = ",".join(permissions)

        # Используем метод create_with_password для удобства
        new_agent = create_service.create_with_password(
            email=email.strip().lower(),
            full_name=full_name.strip(),
            password=password,
            role=role,
            department_id=department_id,
            login=login.strip(),
            phone=phone.strip() if phone else None,
            category_access=category_access_str,
            permissions=permissions_str,
            is_active=(is_active == "on"),
            auto_assign=(auto_assign == "on"),
            email_notifications=(email_notifications == "on"),
            created_by_agent_id=agent.id,
        )

        # Логируем создание агента
        client_info = get_client_info(request)
        log_service = AuditLogService(db)
        log_service.log_action(
            action="create",
            entity_type="agent",
            entity_id=new_agent.id,
            agent_id=agent.id,
            details={
                "full_name": full_name,
                "login": login,
                "email": email,
                "role": role,
            },
            **client_info,
        )

        # Flash-сообщение об успехе
        request.session["flash_success"] = f"Агент {full_name} успешно создан!"

        return RedirectResponse(url="/agents", status_code=303)

    except ValueError as e:
        # Ошибка валидации (дубликат email/login)
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
                "permission_groups": PERMISSION_GROUPS,
                "form_data": {
                    "full_name": full_name,
                    "login": login,
                    "email": email,
                    "role": role,
                    "department_id": department_id,
                    "phone": phone,
                    "category_access": category_access,
                    "permissions": permissions,
                    "is_active": is_active == "on",
                    "auto_assign": auto_assign == "on",
                    "email_notifications": email_notifications == "on",
                },
            },
            status_code=400,
        )
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
                "permission_groups": PERMISSION_GROUPS,
                "form_data": {
                    "full_name": full_name,
                    "login": login,
                    "email": email,
                    "role": role,
                    "department_id": department_id,
                    "phone": phone,
                    "category_access": category_access,
                    "permissions": permissions,
                    "is_active": is_active == "on",
                    "auto_assign": auto_assign == "on",
                    "email_notifications": email_notifications == "on",
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
    # Используем новый сервис для просмотра
    query_service = AgentQueryService(db, current_agent_id=agent.id)
    target_agent = query_service.get(agent_id=agent_id)

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
        "operator/agents/edit.html",
        {
            "request": request,
            "agent": agent,
            "target_agent": target_agent,
            "categories": categories,
            "departments": departments,
            "error": None,
            "permissions_list": list(Permission),
            "permission_labels": PERMISSION_LABELS,
            "permission_groups": PERMISSION_GROUPS,
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
    is_active: str = Form("off"),
    auto_assign: str = Form("off"),
    email_notifications: str = Form("off"),
):
    # Используем новый сервис для редактирования
    edit_service = AgentEditService(db, current_agent_id=agent.id)

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
            query_service = AgentQueryService(db, current_agent_id=agent.id)
            target_agent = query_service.get(agent_id=agent_id)
            return templates.TemplateResponse(
                "operator/agents/edit.html",
                {
                    "request": request,
                    "agent": agent,
                    "target_agent": target_agent,
                    "categories": categories,
                    "departments": departments,
                    "error": "Пароли не совпадают",
                    "permissions_list": list(Permission),
                    "permission_labels": PERMISSION_LABELS,
                    "permission_groups": PERMISSION_GROUPS,
                    "selected_categories": category_access,
                    "selected_permissions": permissions,
                    **agent.get_permissions_dict(),
                },
                status_code=400,
            )

    try:
        # Права для админа — пустые (админ имеет все права автоматически)
        if role == "admin":
            category_access_str = ""
            permissions_str = ""
        else:
            category_access_str = ",".join(category_access)
            permissions_str = ",".join(permissions)

        # Собираем данные для обновления
        from app.schemas.agent import AgentUpdate

        update_data = {
            "full_name": full_name.strip(),
            "login": login.strip(),
            "email": email.strip().lower(),
            "role": role,
            "department_id": department_id,
            "category_access": category_access_str,
            "permissions": permissions_str,
            "phone": phone.strip() if phone else None,
            "is_active": (is_active == "on"),
            "auto_assign": (auto_assign == "on"),
            "email_notifications": (email_notifications == "on"),
        }

        # Пароль добавляем только если указан
        if password and password.strip():
            update_data["password"] = password

        # Вызываем сервис
        edit_service.update(
            agent_id=agent_id,
            agent_data=AgentUpdate(**update_data),
            updated_by_agent_id=agent.id,
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

        # Flash-сообщение об успехе
        request.session["flash_success"] = f"Агент {full_name} успешно обновлён!"

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
        query_service = AgentQueryService(db, current_agent_id=agent.id)
        target_agent = query_service.get(agent_id=agent_id)

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
    # Используем новый сервис для удаления
    delete_service = AgentDeleteService(db, current_agent_id=agent.id)

    # Проверка: нельзя удалить самого себя
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

    result = delete_service.delete(agent_id=agent_id, deleted_by_agent_id=agent.id)

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

        # Flash-сообщение об успехе
        request.session["flash_success"] = "Агент успешно удалён!"

        return RedirectResponse(url="/agents", status_code=303)
    else:
        # Flash-сообщение об ошибке
        request.session["flash_error"] = result.detail or "Ошибка при удалении агента"

        return RedirectResponse(url="/agents", status_code=303)
