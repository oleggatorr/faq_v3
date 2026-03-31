from __future__ import annotations

from fastapi import APIRouter, Depends, Form, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.core.audit import get_client_info
from app.core.auth import check_category_manage
from app.models import get_db
from app.schemas.agent import AgentRead
from app.schemas.question_category import QuestionCategoryCreate, QuestionCategoryUpdate
from app.services.question_category_service import QuestionCategoryService
from app.services.audit_log_service import AuditLogService

from ..main import templates

router = APIRouter(prefix="", tags=["question-categories"])


@router.get("/question-category-list", response_class=HTMLResponse)
def question_category_list(
    request: Request,
    agent: AgentRead = Depends(check_category_manage),
    db: Session = Depends(get_db),
    sort_by: str = Query("sort_order"),
    sort_desc: bool = Query(False),
    limit: int = Query(200, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    service = QuestionCategoryService(db)
    items = service.list(
        filters={"is_active": True},
        sort_by=sort_by,
        sort_desc=sort_desc,
        limit=limit,
        offset=offset,
    )
    return templates.TemplateResponse(
        "operator/question_categories/list.html",
        {
            "request": request,
            "agent": agent,
            "categories": items,
            **agent.get_permissions_dict(),
        },
    )


@router.get("/question-category-add", response_class=HTMLResponse)
def question_category_add(
    request: Request,
    agent: AgentRead = Depends(check_category_manage),
    db: Session = Depends(get_db),
):
    # Получаем список департаментов для формы
    from app.services.department_service import DepartmentService
    
    dept_service = DepartmentService(db)
    departments = dept_service.list(
        filters={"is_active": True},
        sort_by="name",
        limit=200,
    )
    
    return templates.TemplateResponse(
        "operator/question_categories/add.html",
        {
            "request": request,
            "agent": agent,
            "departments": departments,
            **agent.get_permissions_dict(),
        },
    )


@router.get("/question-category/{category_id}/change", response_class=HTMLResponse)
def question_category_change(
    request: Request,
    category_id: int,
    agent: AgentRead = Depends(check_category_manage),
    db: Session = Depends(get_db),
):
    from app.services.department_service import DepartmentService
    
    service = QuestionCategoryService(db)
    category = service.get(category_id=category_id)
    
    dept_service = DepartmentService(db)
    departments = dept_service.list(
        filters={"is_active": True},
        sort_by="name",
        limit=200,
    )
    
    return templates.TemplateResponse(
        "operator/question_categories/edit.html",
        {
            "request": request,
            "agent": agent,
            "category": category,
            "departments": departments,
            **agent.get_permissions_dict(),
        },
    )


@router.post("/question-category-add", response_class=HTMLResponse)
def question_category_add_submit(
    request: Request,
    agent: AgentRead = Depends(check_category_manage),
    db: Session = Depends(get_db),
    name: str = Form(...),
    department_id: int | None = Form(None),
    is_active: bool = Form(False),
):
    from app.services.department_service import DepartmentService
    
    dept_service = DepartmentService(db)
    departments = dept_service.list(
        filters={"is_active": True},
        sort_by="name",
        limit=200,
    )
    
    try:
        category_data = QuestionCategoryCreate(
            name=name.strip(),
            department_id=department_id,
            is_active=is_active,
        )
        
        service = QuestionCategoryService(db)
        service.create(category_data=category_data)
        
        # Логируем создание
        client_info = get_client_info(request)
        log_service = AuditLogService(db)
        log_service.log_action(
            action="create",
            entity_type="question_category",
            entity_id=None,
            agent_id=agent.id,
            details={"name": name, "department_id": department_id},
            **client_info,
        )
        
        # Flash-сообщение
        request.session["flash_success"] = f"Категория '{name}' успешно создана!"
        
        return RedirectResponse(url="/question-category-list", status_code=303)
        
    except Exception as e:
        request.session["flash_error"] = f"Ошибка при создании: {str(e)}"
        return RedirectResponse(url="/question-category-list", status_code=303)


@router.post("/question-category/{category_id}/change", response_class=HTMLResponse)
def question_category_change_submit(
    request: Request,
    category_id: int,
    agent: AgentRead = Depends(check_category_manage),
    db: Session = Depends(get_db),
    name: str = Form(...),
    department_id: int | None = Form(None),
    is_active: bool = Form(False),
):
    from app.services.department_service import DepartmentService
    
    service = QuestionCategoryService(db)
    
    try:
        update_data = QuestionCategoryUpdate(
            name=name.strip(),
            department_id=department_id,
            is_active=is_active,
        )
        
        service.update(category_id=category_id, category_data=update_data)
        
        # Логируем обновление
        client_info = get_client_info(request)
        log_service = AuditLogService(db)
        log_service.log_action(
            action="update",
            entity_type="question_category",
            entity_id=category_id,
            agent_id=agent.id,
            details={"name": name, "department_id": department_id},
            **client_info,
        )
        
        # Flash-сообщение
        request.session["flash_success"] = f"Категория '{name}' успешно обновлена!"
        
        return RedirectResponse(url="/question-category-list", status_code=303)
        
    except Exception as e:
        request.session["flash_error"] = f"Ошибка при обновлении: {str(e)}"
        return RedirectResponse(url="/question-category-list", status_code=303)


@router.post("/question-category/{category_id}/delete", response_class=RedirectResponse)
def question_category_delete(
    request: Request,
    category_id: int,
    agent: AgentRead = Depends(check_category_manage),
    db: Session = Depends(get_db),
):
    service = QuestionCategoryService(db)
    
    try:
        result = service.delete(category_id=category_id)
        
        if result.success:
            # Логируем удаление
            client_info = get_client_info(request)
            log_service = AuditLogService(db)
            log_service.log_action(
                action="delete",
                entity_type="question_category",
                entity_id=category_id,
                agent_id=agent.id,
                details={"deleted_category_id": category_id},
                **client_info,
            )
            
            # Flash-сообщение
            request.session["flash_success"] = "Категория успешно удалена!"
        else:
            request.session["flash_error"] = result.detail or "Ошибка при удалении"
            
    except Exception as e:
        request.session["flash_error"] = f"Ошибка при удалении: {str(e)}"
    
    return RedirectResponse(url="/question-category-list", status_code=303)
