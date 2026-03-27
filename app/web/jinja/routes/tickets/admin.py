from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse
from starlette.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.audit import get_client_info
from app.core.auth import (
    CurrentAgent,
    check_agent_view,
    check_can_del_tickets,
    check_can_edit_tickets,
    check_can_hard_del_tickets,
    check_can_reply_tickets,
    check_can_view_ass_others,
    check_can_view_own_tickets,
    check_can_view_tickets,
    check_can_view_unassigned,
    get_current_agent,
    get_current_agent_optional,
    require_permission,
)
from app.models import get_db
from app.models.agent import Agent
from app.models.ticket import Priority
from app.models.ticket_event import TicketEvent
from app.schemas.agent import AgentRead
from app.schemas.message import MessageCreate
from app.schemas.ticket import TicketUpdate
from app.services.agent_service import AgentService
from app.services.audit_log_service import AuditLogService
from app.services.question_category_service import QuestionCategoryService
from app.services.errors import NotFound
from app.services.file_storage_service import FileStorageError, FileStorageService
from app.services.ticket_status_service import TicketStatusService
from app.services.ticket import (
    TicketService,
    TicketEventService,
    MessageService,
    AttachmentService,
)

from ..main import templates
from ..utils import _ticket_filters

router = APIRouter(prefix="", tags=["tickets-admin"])


@router.get("/tickets/create", response_class=HTMLResponse)
def create_ticket_form(
    request: Request,
    agent: AgentRead = Depends(check_can_edit_tickets),
    db: Session = Depends(get_db),
):
    """Форма создания тикета оператором."""
    dept_service = DepartmentService(db)
    cat_service = QuestionCategoryService(db)
    departments = dept_service.list(filters={"is_active": True}, sort_by="name", limit=200)
    categories = cat_service.list(filters={"is_active": True}, sort_by="sort_order", limit=200)
    
    return templates.TemplateResponse(
        "tickets/create.html",
        {
            "request": request,
            "agent": agent,
            "departments": departments,
            "categories": categories,
        },
    )


@router.post("/tickets/create", response_class=RedirectResponse)
async def create_ticket_submit(
    request: Request,
    agent: AgentRead = Depends(check_can_edit_tickets),
    db: Session = Depends(get_db),
    customer_name: str = Form(...),
    customer_email: str = Form(...),
    subject: str = Form(...),
    body: str = Form(...),
    department_id: int = Form(...),
    category_id: str = Form(""),
    priority: str = Form("normal"),
    attachments: list[UploadFile] = File(default=[]),
):
    """Создание тикета оператором."""
    from app.web.jinja.routes.utils import _parse_int
    
    category_id_int = _parse_int(category_id) if category_id else None
    customer_ip = request.client.host if request.client else "0.0.0.0"
    
    ticket_service = TicketService(db, ticket_event_service=TicketEventService(db))
    
    try:
        track_id = ticket_service.generate_track_id()
        priority_enum = Priority(priority) if priority else Priority.normal
        
        ticket_data = TicketCreate(
            track_id=track_id,
            customer_name=customer_name.strip(),
            customer_email=customer_email.strip(),
            customer_ip=customer_ip,
            department_id=department_id,
            category_id=category_id_int,
            status_id=1,
            priority=priority_enum,
            subject=subject.strip(),
            owner_id=agent.id,  # Назначаем на создавшего оператора
        )
        
        ticket, message = ticket_service.create_ticket_with_first_message(
            ticket_data=ticket_data,
            first_message_body=body.strip(),
        )
        
        # Логируем создание
        client_info = get_client_info(request)
        log_service = AuditLogService(db)
        log_service.log_action(
            action="create",
            entity_type="ticket",
            entity_id=ticket.id,
            agent_id=agent.id,
            details={
                "track_id": ticket.track_id,
                "subject": ticket.subject,
                "customer_name": ticket.customer_name,
                "created_by_agent": True,
            },
            **client_info,
        )
        
        # Flash-сообщение
        request.session["flash_success"] = f"Тикет {ticket.track_id} успешно создан!"
        
    except Exception as e:
        request.session["flash_error"] = f"Ошибка при создании: {str(e)}"
    
    return RedirectResponse(url="/tickets", status_code=303)


@router.get("/tickets/unassigned", response_class=HTMLResponse)
def tickets_unassigned(
    request: Request,
    agent: AgentRead = Depends(check_can_view_unassigned),  # Право на просмотр неназначенных
    db: Session = Depends(get_db),
    status_id: str | None = Query(None),
    category_id: str | None = Query(None),
    sort_by: str = Query("created_at", description="Sort field"),
    sort_desc: bool = Query(True, description="Sort descending"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    archived: str = Query("active", description="Filter by archived: active, archived, all"),
):
    """Неназначенные тикеты (требует права can_view_unassigned)."""
    # Передаём agent_id для проверок прав в сервисе
    ticket_service = TicketService(db, agent_id=agent.id)
    category_service = QuestionCategoryService(db)
    status_service = TicketStatusService(db)
    agent_service = AgentService(db)

    # Фильтр: только неназначенные тикеты
    filters = {"owner_id": None}

    # Преобразуем пустые строки в None
    status_id_int = int(status_id) if status_id and status_id.strip() else None
    category_id_int = int(category_id) if category_id and category_id.strip() else None

    # Дополнительные фильтры
    if status_id_int:
        filters["status_id"] = status_id_int
    if category_id_int:
        filters["category_id"] = category_id_int

    # Фильтр по архиву
    if archived == "active":
        filters["is_archived"] = False
    elif archived == "archived":
        filters["is_archived"] = True

    tickets = ticket_service.list(
        filters=filters,
        sort_by=sort_by,
        sort_desc=sort_desc,
        limit=limit,
        offset=offset,
    )
    categories = category_service.list(limit=500)
    statuses = status_service.list(limit=200)
    agents = agent_service.list(filters={"is_active": True}, sort_by="full_name", limit=500)
    category_name_by_id = {c.id: c.name for c in categories}
    status_name_by_id = {s.id: s.name for s in statuses}

    # Получаем общее количество
    all_tickets = ticket_service.list(filters=filters, limit=999999)
    total_count = len(all_tickets)

    return templates.TemplateResponse(
        "tickets/unassigned.html",
        {
            "request": request,
            "agent": agent,
            "tickets": tickets,
            "category_name_by_id": category_name_by_id,
            "status_name_by_id": status_name_by_id,
            "statuses": statuses,
            "categories": categories,
            "agents": agents,
            "sort_by": sort_by,
            "sort_desc": sort_desc,
            "limit": limit,
            "offset": offset,
            "archived_filter": archived,
            "total_count": total_count,
            **agent.get_permissions_dict(),
        },
    )


@router.get("/tickets/others", response_class=HTMLResponse)
def tickets_others(
    request: Request,
    agent: AgentRead = Depends(check_can_view_ass_others),  # Право на просмотр чужих
    db: Session = Depends(get_db),
    status_id: str | None = Query(None),
    category_id: str | None = Query(None),
    sort_by: str = Query("created_at", description="Sort field"),
    sort_desc: bool = Query(True, description="Sort descending"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    archived: str = Query("active", description="Filter by archived: active, archived, all"),
):
    """Тикеты, назначенные другим агентам (требует права can_view_ass_others)."""
    # Передаём agent_id для проверок прав в сервисе
    ticket_service = TicketService(db, agent_id=agent.id)
    category_service = QuestionCategoryService(db)
    status_service = TicketStatusService(db)
    agent_service = AgentService(db)

    # Фильтр: только тикеты, назначенные другим агентам
    filters = {"owner_id": agent.id}  # Будет инвертировано ниже

    # Преобразуем пустые строки в None
    status_id_int = int(status_id) if status_id and status_id.strip() else None
    category_id_int = int(category_id) if category_id and category_id.strip() else None

    # Дополнительные фильтры
    if status_id_int:
        filters["status_id"] = status_id_int
    if category_id_int:
        filters["category_id"] = category_id_int

    # Фильтр по архиву
    if archived == "active":
        filters["is_archived"] = False
    elif archived == "archived":
        filters["is_archived"] = True

    tickets = ticket_service.list(
        filters=filters,
        sort_by=sort_by,
        sort_desc=sort_desc,
        limit=limit,
        offset=offset,
    )
    # Фильтруем тикеты, назначенные другим (не текущему агенту и не None)
    tickets = [t for t in tickets if t.owner_id and t.owner_id != agent.id]
    
    categories = category_service.list(limit=500)
    statuses = status_service.list(limit=200)
    agents = agent_service.list(filters={"is_active": True}, sort_by="full_name", limit=500)
    category_name_by_id = {c.id: c.name for c in categories}
    status_name_by_id = {s.id: s.name for s in statuses}

    # Получаем общее количество
    all_tickets = ticket_service.list(filters=filters, limit=999999)
    all_tickets = [t for t in all_tickets if t.owner_id and t.owner_id != agent.id]
    total_count = len(all_tickets)

    return templates.TemplateResponse(
        "tickets/others.html",
        {
            "request": request,
            "agent": agent,
            "tickets": tickets,
            "category_name_by_id": category_name_by_id,
            "status_name_by_id": status_name_by_id,
            "statuses": statuses,
            "categories": categories,
            "agents": agents,
            "sort_by": sort_by,
            "sort_desc": sort_desc,
            "limit": limit,
            "offset": offset,
            "archived_filter": archived,
            "total_count": total_count,
            **agent.get_permissions_dict(),
        },
    )


@router.get("/tickets/my", response_class=HTMLResponse)
def tickets_my(
    request: Request,
    agent: AgentRead = Depends(check_can_view_own_tickets),  # Право на просмотр своих тикетов
    db: Session = Depends(get_db),
    status_id: str | None = Query(None),
    category_id: str | None = Query(None),
    sort_by: str = Query("created_at", description="Sort field"),
    sort_desc: bool = Query(True, description="Sort descending"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    archived: str = Query("active", description="Filter by archived: active, archived, all"),
):
    """Тикеты, назначенные текущему агенту (требует права can_view_tickets)."""
    # Передаём agent_id для проверок прав в сервисе
    ticket_service = TicketService(db, agent_id=agent.id)
    category_service = QuestionCategoryService(db)
    status_service = TicketStatusService(db)
    agent_service = AgentService(db)

    # Фильтр: только тикеты, назначенные текущему агенту
    filters = {"owner_id": agent.id}


@router.get("/tickets", response_class=HTMLResponse)
def tickets_list(
    request: Request,
    agent: AgentRead = Depends(check_can_view_own_tickets),  # Право на просмотр списка тикетов
    db: Session = Depends(get_db),
    q: str = Query("", description="Quick search by track_id/subject/customer"),
    status_id: str | None = Query(None),
    category_id: str | None = Query(None),
    sort_by: str = Query("created_at", description="Sort field"),
    sort_desc: bool = Query(True, description="Sort descending"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    archived: str = Query("active", description="Filter by archived: active, archived, all"),
):
    # Сервис сам проверит права внутри (двойная защита)
    ticket_service = TicketService(db, agent_id=agent.id)
    category_service = QuestionCategoryService(db)
    status_service = TicketStatusService(db)
    agent_service = AgentService(db)
    filters = _ticket_filters(request)

    # Преобразуем пустые строки в None
    status_id_int = int(status_id) if status_id and status_id.strip() else None
    category_id_int = int(category_id) if category_id and category_id.strip() else None

    if status_id_int:
        filters["status_id"] = status_id_int
    if category_id_int:
        filters["category_id"] = category_id_int

    if q and not any(filters.get(k) for k in ("track_id", "subject", "customer_name", "customer_email")):
        filters["track_id"] = q.strip()

    # Фильтр по архиву
    if archived == "active":
        filters["is_archived"] = False
    elif archived == "archived":
        filters["is_archived"] = True

    tickets = ticket_service.list(
        filters=filters if filters else None,
        sort_by=sort_by,
        sort_desc=sort_desc,
        limit=limit,
        offset=offset,
    )
    categories = category_service.list(limit=500)
    statuses = status_service.list(limit=200)
    agents = agent_service.list(filters={"is_active": True}, sort_by="full_name", limit=500)
    category_name_by_id = {c.id: c.name for c in categories}
    status_name_by_id = {s.id: s.name for s in statuses}

    return templates.TemplateResponse(
        "tickets/list.html",
        {
            "request": request,
            "tickets": tickets,
            "agent": agent,
            "categories": categories,
            "statuses": statuses,
            "agents": agents,
            "category_name_by_id": category_name_by_id,
            "status_name_by_id": status_name_by_id,
            "filters": filters,
            "q": q,
            "sort_by": sort_by,
            "sort_desc": sort_desc,
            "limit": limit,
            "offset": offset,
            "archived_filter": archived,
            **agent.get_permissions_dict(),
        },
    )


@router.get("/list-tickets", response_class=RedirectResponse)
def list_tickets_alias(agent: CurrentAgent):
    return RedirectResponse(url="/tickets", status_code=303)


@router.get("/tickets/{ticket_id}", response_class=HTMLResponse)
def ticket_detail_admin(
    request: Request,
    ticket_id: int,
    agent: AgentRead = Depends(check_can_view_tickets),
    db: Session = Depends(get_db),
):
    # Передаём agent_id для проверок прав в сервисе
    ticket_service = TicketService(db, agent_id=agent.id)
    try:
        ticket = ticket_service.get(ticket_id=ticket_id)
    except NotFound:
        return templates.TemplateResponse(
            "tickets/detail.html",
            {"request": request, "ticket": None, "error": "Тикет не найден", "agent": agent},
            status_code=404,
        )

    message_service = MessageService(db)
    messages = message_service.list(
        filters={"ticket_id": ticket.id},
        sort_by="created_at",
        sort_desc=False,
        limit=500,
    )

    attachment_service = AttachmentService(db)
    attachments_by_message: dict[int, list] = {}
    for msg in messages:
        attachments_by_message[msg.id] = attachment_service.list(
            filters={"message_id": msg.id},
            sort_by="id",
            limit=50,
        )

    events = (
        db.query(TicketEvent)
        .filter(TicketEvent.ticket_id == ticket.id)
        .order_by(TicketEvent.occurred_at.asc())
        .limit(200)
        .all()
    )

    status_service = TicketStatusService(db)
    category_service = QuestionCategoryService(db)
    agent_service = AgentService(db)

    statuses = status_service.list(sort_by="sort_order", limit=200)
    categories = category_service.list(filters={"is_active": True}, sort_by="sort_order", limit=200)
    agents = agent_service.list(filters={"is_active": True}, sort_by="full_name", limit=500)

    priorities = list(Priority)

    status_name_by_id = {s.id: s.name for s in statuses}
    category_name_by_id = {c.id: c.name for c in categories}
    agent_name_by_id = {a.id: a.full_name for a in agents}

    return templates.TemplateResponse(
        "tickets/detail.html",
        {
            "request": request,
            "ticket": ticket,
            "messages": messages,
            "events": events,
            "attachments_by_message": attachments_by_message,
            "agent": agent,
            "statuses": statuses,
            "priorities": priorities,
            "categories": categories,
            "agents": agents,
            "status_name_by_id": status_name_by_id,
            "category_name_by_id": category_name_by_id,
            "agent_name_by_id": agent_name_by_id,
            "error": None,
            **agent.get_permissions_dict(),
        },
    )


@router.post("/tickets/{ticket_id}/reply", response_class=RedirectResponse)
async def admin_reply(
    ticket_id: int,
    request: Request,
    agent: AgentRead = Depends(check_can_reply_tickets),
    db: Session = Depends(get_db),
    body: str = Form(...),
    is_internal: str = Form("false"),
    attachments: list[UploadFile] = File(default=[]),
):
    is_internal_bool = is_internal.lower() in ("true", "on", "1", "yes")

    # Сервис сам проверит права внутри (двойная защита)
    ticket_service = TicketService(db, agent_id=agent.id, ticket_event_service=TicketEventService(db))
    try:
        ticket = ticket_service.get(ticket_id=ticket_id)
    except NotFound:
        raise HTTPException(status_code=404, detail="Тикет не найден")

    message_service = MessageService(db, ticket_event_service=TicketEventService(db))

    message_data = MessageCreate(
        ticket_id=ticket.id,
        agent_id=agent.id,
        customer_name=None,
        customer_email=None,
        subject=ticket.subject,
        body=body.strip(),
        is_internal=is_internal_bool,
        is_automatic=False,
        ip_address=(request.client.host if request.client else None),
    )
    message = message_service.add_message(message_data=message_data, agent_id=agent.id)

    # Логируем создание сообщения
    client_info = get_client_info(request)
    log_service = AuditLogService(db)
    log_service.log_action(
        action="create",
        entity_type="message",
        entity_id=message.id,
        agent_id=agent.id,
        details={
            "ticket_id": ticket.id,
            "is_internal": is_internal_bool,
            "has_attachments": bool(attachments),
        },
        **client_info,
    )

    if attachments:
        file_storage = FileStorageService()
        attachment_service = AttachmentService(db, ticket_event_service=TicketEventService(db))
        files_meta = []
        for uf in attachments:
            if not uf.filename or not uf.filename.strip():
                continue
            content = await uf.read()
            if not content:
                continue
            try:
                meta = file_storage.save(
                    content=content,
                    original_filename=uf.filename,
                    mime_type=uf.content_type or "application/octet-stream",
                )
                files_meta.append(meta)
            except FileStorageError:
                continue
        if files_meta:
            attachment_service.add_attachments(
                message=message,
                uploaded_by_agent_id=agent.id,
                files=files_meta,
            )

    if not is_internal_bool and ticket.customer_email:
        try:
            from app.services.email_service import notify_new_message
            notify_new_message(
                to_email=ticket.customer_email,
                track_id=ticket.track_id,
                subject=ticket.subject,
                message_preview=body.strip()[:200],
                from_name=agent.full_name or "Поддержка",
            )
        except Exception:
            pass

    return RedirectResponse(url=f"/tickets/{ticket_id}", status_code=303)


@router.post("/tickets/{ticket_id}/update", response_class=RedirectResponse)
def admin_update_ticket(
    ticket_id: int,
    request: Request,
    agent: AgentRead = Depends(check_can_edit_tickets),
    db: Session = Depends(get_db),
    status_id: str = Form(""),
    priority: str = Form(""),
    owner_id: str = Form(""),
    category_id: str = Form(""),
    is_locked: str = Form("false"),
    is_archived: str = Form("false"),
):
    # Сервис сам проверит права внутри (двойная защита)
    ticket_service = TicketService(db, agent_id=agent.id, ticket_event_service=TicketEventService(db))
    update_data = {}

    if status_id and status_id.isdigit():
        update_data["status_id"] = int(status_id)

    if priority:
        try:
            update_data["priority"] = Priority(priority)
        except ValueError:
            pass

    if owner_id and owner_id.isdigit():
        owner_val = int(owner_id)
        update_data["owner_id"] = owner_val if owner_val > 0 else None

    if category_id and category_id.isdigit():
        cat_val = int(category_id)
        update_data["category_id"] = cat_val if cat_val > 0 else None

    update_data["is_locked"] = is_locked.lower() in ("true", "on", "1", "yes")
    update_data["is_archived"] = is_archived.lower() in ("true", "on", "1", "yes")

    clean_update = {k: v for k, v in update_data.items() if v is not None}

    if clean_update:
        try:
            ticket_service.update_ticket(
                ticket_id=ticket_id,
                ticket_data=TicketUpdate(**clean_update),
                agent_id=agent.id,
            )
            
            # Логируем изменение тикета
            client_info = get_client_info(request)
            log_service = AuditLogService(db)
            log_service.log_action(
                action="update",
                entity_type="ticket",
                entity_id=ticket_id,
                agent_id=agent.id,
                details={"changes": clean_update},
                **client_info,
            )
        except NotFound:
            raise HTTPException(status_code=404, detail="Тикет не найден")
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Ошибка обновления: {str(e)}")

    return RedirectResponse(url=f"/tickets/{ticket_id}", status_code=303)


@router.post("/tickets/{ticket_id}/delete")
async def delete_ticket(
    request: Request,
    ticket_id: int,
    db: Session = Depends(get_db),
    agent: AgentRead = Depends(check_can_del_tickets),
):
    # Сервис сам проверит права внутри (двойная защита)
    ticket_service = TicketService(db, agent_id=agent.id)
    result = ticket_service.delete_ticket(
        ticket_id=ticket_id,
        agent_id=agent.id,
    )

    if not result.success:
        raise HTTPException(status_code=404, detail=result.detail or "Тикет не найден")
    
    # Логируем удаление тикета
    client_info = get_client_info(request)
    log_service = AuditLogService(db)
    log_service.log_action(
        action="delete",
        entity_type="ticket",
        entity_id=ticket_id,
        agent_id=agent.id,
        details={"deleted_by": agent.full_name},
        **client_info,
    )

    return RedirectResponse(url="/tickets", status_code=303)


@router.post("/tickets/{ticket_id}/hard-delete")
async def hard_delete_ticket(
    request: Request,
    ticket_id: int,
    db: Session = Depends(get_db),
    agent: AgentRead = Depends(check_can_hard_del_tickets),
):
    """Полное удаление тикета со всеми сообщениями и вложениями."""
    # Передаём agent_id для проверок прав в сервисе
    ticket_service = TicketService(db, agent_id=agent.id)
    result = ticket_service.hard_delete_ticket(
        ticket_id=ticket_id,
        agent_id=agent.id,
    )

    if not result.success:
        raise HTTPException(status_code=404, detail=result.detail or "Тикет не найден")

    # Логируем полное удаление тикета
    client_info = get_client_info(request)
    log_service = AuditLogService(db)
    log_service.log_action(
        action="delete",
        entity_type="ticket",
        entity_id=ticket_id,
        agent_id=agent.id,
        details={"deleted_by": agent.full_name, "hard_delete": True},
        **client_info,
    )
    
    # Flash-сообщение
    request.session["flash_success"] = "Тикет полностью удалён!"

    return RedirectResponse(url="/tickets", status_code=303)


@router.post("/tickets/{ticket_id}/restore", response_class=RedirectResponse)
def restore_ticket(
    ticket_id: int,
    request: Request,
    agent: AgentRead = Depends(check_can_edit_tickets),
    db: Session = Depends(get_db),
):
    """Восстановить тикет из архива (снять флаг is_archived)."""
    ticket_service = TicketService(db, ticket_event_service=TicketEventService(db))
    try:
        ticket_service.update_ticket(
            ticket_id=ticket_id,
            ticket_data=TicketUpdate(is_archived=False),
            agent_id=agent.id,
        )
        
        # Логируем восстановление тикета
        client_info = get_client_info(request)
        log_service = AuditLogService(db)
        log_service.log_action(
            action="update",
            entity_type="ticket",
            entity_id=ticket_id,
            agent_id=agent.id,
            details={"restored_from_archive": True},
            **client_info,
        )
    except NotFound:
        raise HTTPException(status_code=404, detail="Тикет не найден")

    return RedirectResponse(url=f"/tickets/{ticket_id}", status_code=303)


@router.post("/tickets/bulk-operation", response_class=RedirectResponse)
async def tickets_bulk_operation(
    request: Request,
    agent: AgentRead = Depends(check_can_edit_tickets),
    db: Session = Depends(get_db),
    ticket_ids: str = Form(...),  # JSON array of ticket IDs
    operation: str = Form(...),  # archive, delete, assign, change_status
    owner_id: int | None = Form(None),
    status_id: int | None = Form(None),
):
    """Массовые операции с тикетами."""
    import json

    ticket_service = TicketService(db, ticket_event_service=TicketEventService(db))

    try:
        ids = json.loads(ticket_ids)
        if not isinstance(ids, list) or not all(isinstance(i, int) for i in ids):
            raise ValueError("Invalid ticket IDs")
    except (json.JSONDecodeError, ValueError):
        request.session["flash_error"] = "Неверный формат данных"
        return RedirectResponse(url="/tickets", status_code=303)

    success_count = 0
    error_count = 0

    for ticket_id in ids:
        try:
            ticket = ticket_service.get(ticket_id=ticket_id)
            if not ticket:
                error_count += 1
                continue

            # Админ может всё, операторы только с can_edit_tickets
            # (проверка уже была в Depends(check_can_edit_tickets))

            if operation == 'archive':
                ticket_service.update_ticket(
                    ticket_id=ticket_id,
                    ticket_data=TicketUpdate(is_archived=True),
                    agent_id=agent.id,
                )
                success_count += 1
                
                # Логируем архивирование
                client_info = get_client_info(request)
                log_service = AuditLogService(db)
                log_service.log_action(
                    action="update",
                    entity_type="ticket",
                    entity_id=ticket_id,
                    agent_id=agent.id,
                    details={"bulk_operation": "archive", "track_id": ticket.track_id},
                    **client_info,
                )

            elif operation == 'unarchive':
                ticket_service.update_ticket(
                    ticket_id=ticket_id,
                    ticket_data=TicketUpdate(is_archived=False),
                    agent_id=agent.id,
                )
                success_count += 1
                
                # Логируем разархивирование
                client_info = get_client_info(request)
                log_service = AuditLogService(db)
                log_service.log_action(
                    action="update",
                    entity_type="ticket",
                    entity_id=ticket_id,
                    agent_id=agent.id,
                    details={"bulk_operation": "unarchive", "track_id": ticket.track_id},
                    **client_info,
                )

            elif operation == 'delete':
                if agent.has_permission('can_hard_del_tickets') or agent.role == 'admin':
                    ticket_service.hard_delete_ticket(
                        ticket_id=ticket_id,
                        agent_id=agent.id,
                    )
                    success_count += 1
                    
                    # Логируем удаление
                    client_info = get_client_info(request)
                    log_service = AuditLogService(db)
                    log_service.log_action(
                        action="delete",
                        entity_type="ticket",
                        entity_id=ticket_id,
                        agent_id=agent.id,
                        details={"bulk_operation": "hard_delete", "track_id": ticket.track_id},
                        **client_info,
                    )
                else:
                    # Архивирование вместо удаления
                    ticket_service.update_ticket(
                        ticket_id=ticket_id,
                        ticket_data=TicketUpdate(is_archived=True),
                        agent_id=agent.id,
                    )
                    success_count += 1
                    
                    # Логируем архивирование
                    client_info = get_client_info(request)
                    log_service = AuditLogService(db)
                    log_service.log_action(
                        action="update",
                        entity_type="ticket",
                        entity_id=ticket_id,
                        agent_id=agent.id,
                        details={"bulk_operation": "archive_fallback", "track_id": ticket.track_id},
                        **client_info,
                    )

            elif operation == 'assign' and owner_id:
                ticket_service.update_ticket(
                    ticket_id=ticket_id,
                    ticket_data=TicketUpdate(owner_id=owner_id),
                    agent_id=agent.id,
                )
                success_count += 1
                
                # Логируем назначение
                client_info = get_client_info(request)
                log_service = AuditLogService(db)
                log_service.log_action(
                    action="update",
                    entity_type="ticket",
                    entity_id=ticket_id,
                    agent_id=agent.id,
                    details={"bulk_operation": "assign", "track_id": ticket.track_id, "new_owner_id": owner_id},
                    **client_info,
                )

            elif operation == 'change_status' and status_id:
                ticket_service.update_ticket(
                    ticket_id=ticket_id,
                    ticket_data=TicketUpdate(status_id=status_id),
                    agent_id=agent.id,
                )
                success_count += 1
                
                # Логируем изменение статуса
                client_info = get_client_info(request)
                log_service = AuditLogService(db)
                log_service.log_action(
                    action="update",
                    entity_type="ticket",
                    entity_id=ticket_id,
                    agent_id=agent.id,
                    details={"bulk_operation": "change_status", "track_id": ticket.track_id, "new_status_id": status_id},
                    **client_info,
                )

        except Exception as e:
            error_count += 1
            print(f"Error processing ticket {ticket_id}: {e}")

    # Flash-сообщение
    if success_count > 0:
        request.session["flash_success"] = f"Обработано тикетов: {success_count}"
    if error_count > 0:
        request.session["flash_error"] = f"Ошибок: {error_count}"

    return RedirectResponse(url="/tickets", status_code=303)


@router.get("/attachments/{attachment_id}/download")
def attachment_download(
    attachment_id: int,
    agent: CurrentAgent,
    db: Session = Depends(get_db),
):
    """Скачать вложение (для авторизованных операторов)."""
    attachment_service = AttachmentService(db)
    att = attachment_service.get_orm(attachment_id=attachment_id)
    if att is None:
        raise HTTPException(status_code=404, detail="Вложение не найдено")

    file_storage = FileStorageService()
    path = file_storage.get_path(att.file_path)
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Файл не найден")

    attachment_service.increment_download_count(attachment_id=attachment_id)

    # Определяем, как открывать файл
    # Изображения и PDF - inline (в браузере), остальные - attachment (скачивание)
    if att.mime_type.startswith('image/') or att.mime_type == 'application/pdf':
        disposition = f'inline; filename="{att.original_filename}"'
    else:
        disposition = f'attachment; filename="{att.original_filename}"'

    return FileResponse(
        path=str(path),
        filename=att.original_filename,
        media_type=att.mime_type,
        headers={"Content-Disposition": disposition},
    )
