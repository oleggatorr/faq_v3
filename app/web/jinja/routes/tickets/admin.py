from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse
from starlette.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.audit import get_client_info
from app.core.auth import (
    CurrentAgent,
    check_agent_view,
    check_can_anonymize_tickets,
    check_can_archive_tickets,
    check_can_assign_others,
    check_can_assign_self,
    check_can_del_tickets,
    check_can_edit_tickets,
    check_can_hard_del_tickets,
    check_can_merge_tickets,
    check_can_reply_tickets,
    check_can_resolve,
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
from app.schemas.ticket import TicketCreate, TicketUpdate
from app.services.agent_service import AgentService
from app.services.audit_log_service import AuditLogService
from app.services.department_service import DepartmentService
from app.services.question_category_service import QuestionCategoryService
from app.services.errors import NotFound
from app.services.file_storage_service import FileStorageError, FileStorageService
from app.services.ticket_status_service import TicketStatusService
from app.services.ticket import (
    TicketService,
    TicketEventService,
    MessageService,
    AttachmentService,
    TicketReadStateService,
)
from app.services.ban_service import BanService

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
    from app.models.ticket import Priority
    
    dept_service = DepartmentService(db)
    cat_service = QuestionCategoryService(db)
    departments = dept_service.list(filters={"is_active": True}, sort_by="name", limit=200)
    categories = cat_service.list(filters={"is_active": True}, sort_by="sort_order", limit=200)
    priorities = list(Priority)

    return templates.TemplateResponse(
        "operator/tickets/create.html",
        {
            "request": request,
            "agent": agent,
            "departments": departments,
            "categories": categories,
            "priorities": priorities,
            "form_data": None,
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

    ticket_service = TicketService(
        db,
        ticket_event_service=TicketEventService(db),
        ticket_read_state_service=TicketReadStateService(db),
    )
    
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
    limit: str | None = Query(None),
    offset: str | None = Query(None),
    archived: str = Query("active", description="Filter by archived: active, archived, all"),
):
    """Неназначенные тикеты (требует права can_view_unassigned)."""
    # Обработка пустых значений
    limit_int = int(limit) if limit and limit.strip() else 10
    offset_int = int(offset) if offset and offset.strip() else 0
    
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
        limit=limit_int,
        offset=offset_int,
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
    limit: str | None = Query(None),
    offset: str | None = Query(None),
    archived: str = Query("active", description="Filter by archived: active, archived, all"),
):
    """Тикеты, назначенные другим агентам (требует права can_view_ass_others)."""
    # Обработка пустых значений
    limit_int = int(limit) if limit and limit.strip() else 10
    offset_int = int(offset) if offset and offset.strip() else 0
    
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
        limit=limit_int,
        offset=offset_int,
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
    status_ids: list[str] = Query([], description="Multiple status IDs"),
    category_id: str | None = Query(None),
    sort_by: str = Query("priority", description="Sort field"),
    sort_desc: bool = Query(False, description="Sort descending"),
    limit: str | None = Query(None),
    offset: str | None = Query(None),
    archived: str = Query("active", description="Filter by archived: active, archived, all"),
):
    """Тикеты, назначенные текущему агенту (требует права can_view_tickets)."""
    # Обработка пустых значений
    limit_int = int(limit) if limit and limit.strip() else 10
    offset_int = int(offset) if offset and offset.strip() else 0

    # Передаём agent_id для проверок прав в сервисе
    ticket_service = TicketService(db, agent_id=agent.id)
    category_service = QuestionCategoryService(db)
    status_service = TicketStatusService(db)
    agent_service = AgentService(db)

    # Фильтр: только тикеты, назначенные текущему агенту
    filters = {"owner_id": agent.id}

    # Преобразуем пустые строки в None
    status_ids_int = [int(s) for s in status_ids if s and s.strip()]
    category_id_int = int(category_id) if category_id and category_id.strip() else None

    if status_ids_int:
        filters["status_ids"] = status_ids_int
    if category_id_int:
        filters["category_id"] = category_id_int

    # Фильтр по архиву
    if archived == "active":
        filters["is_archived"] = False
    elif archived == "archived":
        filters["is_archived"] = True

    # Получаем тикеты с unread_count
    tickets = ticket_service.list(
        filters=filters if filters else None,
        sort_by=sort_by,
        sort_desc=sort_desc,
        limit=limit_int,
        offset=offset_int,
        include_unread=True,
        agent_id=agent.id,
    )
    categories = category_service.list(limit=500)
    statuses = status_service.list(limit=200)
    agents = agent_service.list(filters={"is_active": True}, sort_by="full_name", limit=500)

    # Словари для быстрого поиска имён
    category_name_by_id = {c.id: c.name for c in categories}
    status_name_by_id = {s.id: s.name for s in statuses}

    # Получаем общее количество для пагинации
    all_tickets = ticket_service.list(
        filters=filters if filters else None,
        limit=999999,
    )
    total_count = len(all_tickets)

    return templates.TemplateResponse(
        "operator/tickets/my.html",
        {
            "request": request,
            "agent": agent,
            "tickets": tickets,
            "categories": categories,
            "statuses": statuses,
            "agents": agents,
            "category_name_by_id": category_name_by_id,
            "status_name_by_id": status_name_by_id,
            "status_ids": status_ids,
            "category_id": category_id,
            "sort_by": sort_by,
            "sort_desc": sort_desc,
            "limit": limit,
            "offset": offset,
            "archived": archived,
            "total_count": total_count,
            "limit_int": limit_int,
            "offset_int": offset_int,
            **agent.get_permissions_dict(),
        },
    )


@router.post("/tickets/my/mark-all-read", response_class=RedirectResponse)
def tickets_my_mark_all_read(
    request: Request,
    agent: AgentRead = Depends(check_can_view_own_tickets),
    db: Session = Depends(get_db),
):
    """Отметить все тикеты агента как прочитанные."""
    ticket_service = TicketService(db, agent_id=agent.id)
    
    # Получаем все тикеты агента
    my_tickets = ticket_service.list(
        filters={"owner_id": agent.id},
        limit=999999
    )
    
    # Отмечаем каждый как прочитанный
    for ticket in my_tickets:
        ticket_service.mark_as_read(ticket_id=ticket.id)
    
    request.session["flash_success"] = "Все тикеты отмечены как прочитанные"
    
    return RedirectResponse(url="/tickets/my", status_code=303)


@router.get("/tickets/all", response_class=HTMLResponse)
def tickets_all(
    request: Request,
    agent: AgentRead = Depends(check_can_view_unassigned),  # Право на просмотр неназначенных
    db: Session = Depends(get_db),
    q: str = Query("", description="Quick search by track_id/subject/customer"),
    status_ids: list[str] = Query([], description="Multiple status IDs"),
    category_id: str | None = Query(None),
    sort_by: str = Query("priority", description="Sort field"),
    sort_desc: bool = Query(False, description="Sort descending"),
    limit: str | None = Query(None),
    offset: str | None = Query(None),
    archived: str = Query("active", description="Filter by archived: active, archived, all"),
    owner_filter: str = Query("unassigned", description="Filter by owner: unassigned, assigned, any"),
    owner_id: str | None = Query(None, description="Specific owner ID"),
):
    """Все тикеты (требует право can_view_unassigned или админ)."""
    # Проверка прав на расширенный фильтр
    perms = agent.get_permissions_dict()
    is_admin = agent.role == 'admin'
    
    # Если выбран фильтр «Назначен на...» или «Все тикеты», нужно право can_view_ass_others
    if owner_filter in ('assigned', 'any') and not perms.get('can_view_ass_others', False) and not is_admin:
        # Принудительно сбрасываем на «Неназначенные»
        owner_filter = 'unassigned'
    
    # Обработка пустых значений
    limit_int = int(limit) if limit and limit.strip() else 20
    offset_int = int(offset) if offset and offset.strip() else 0

    # Передаём agent_id для проверок прав в сервисе
    ticket_service = TicketService(db, agent_id=agent.id)
    category_service = QuestionCategoryService(db)
    status_service = TicketStatusService(db)
    agent_service = AgentService(db)
    
    # Преобразуем пустые строки в None
    status_ids_int = [int(s) for s in status_ids if s and s.strip()]
    category_id_int = int(category_id) if category_id and category_id.strip() else None

    # Получаем базовые фильтры из запроса
    filters = _ticket_filters(request)

    if status_ids_int:
        filters["status_ids"] = status_ids_int
    if category_id_int:
        filters["category_id"] = category_id_int

    if q and not any(filters.get(k) for k in ("track_id", "subject", "customer_name", "customer_email")):
        filters["track_id"] = q.strip()

    # Фильтр по назначению (перекрывает owner_id из _ticket_filters)
    if owner_filter == "unassigned":
        filters["owner_id"] = "NULL"  # Специальное значение для IS NULL
    elif owner_filter == "assigned" and owner_id and owner_id.strip():
        filters["owner_id"] = int(owner_id)
    # Если owner_filter == "any" — удаляем owner_id из фильтров (оставляем как есть из _ticket_filters)
    elif owner_filter == "any":
        filters.pop("owner_id", None)  # Удаляем, если был установлен из _ticket_filters

    # Фильтр по архиву
    if archived == "active":
        filters["is_archived"] = False
    elif archived == "archived":
        filters["is_archived"] = True

    tickets = ticket_service.list(
        filters=filters if filters else None,
        sort_by=sort_by,
        sort_desc=sort_desc,
        limit=limit_int,
        offset=offset_int,
        include_unread=False,
        agent_id=agent.id,
    )
    categories = category_service.list(limit=500)
    statuses = status_service.list(limit=200)
    agents = agent_service.list(filters={"is_active": True}, sort_by="full_name", limit=500)
    category_name_by_id = {c.id: c.name for c in categories}
    status_name_by_id = {s.id: s.name for s in statuses}
    agent_name_by_id = {a.id: a.full_name for a in agents}

    # Получаем общее количество
    all_tickets = ticket_service.list(filters=filters if filters else None, limit=999999)
    total_count = len(all_tickets)

    return templates.TemplateResponse(
        "operator/tickets/all.html",
        {
            "request": request,
            "tickets": tickets,
            "agent": agent,
            "categories": categories,
            "statuses": statuses,
            "agents": agents,
            "category_name_by_id": category_name_by_id,
            "status_name_by_id": status_name_by_id,
            "agent_name_by_id": agent_name_by_id,
            "filters": filters,
            "q": q,
            "sort_by": sort_by,
            "sort_desc": sort_desc,
            "limit": limit,
            "offset": offset,
            "archived": archived,
            "owner_filter": owner_filter,
            "owner_id": owner_id,
            "status_ids": status_ids,
            "total_count": total_count,
            "limit_int": limit_int,
            "offset_int": offset_int,
            **agent.get_permissions_dict(),
        },
    )


@router.get("/tickets", response_class=HTMLResponse)
def tickets_list(
    request: Request,
    agent: AgentRead = Depends(check_can_view_own_tickets),  # Право на просмотр своих тикетов
    db: Session = Depends(get_db),
    q: str = Query("", description="Quick search by track_id/subject/customer"),
    status_id: str | None = Query(None),
    category_id: str | None = Query(None),
    sort_by: str = Query("created_at", description="Sort field"),
    sort_desc: bool = Query(True, description="Sort descending"),
    limit: str | None = Query(None),
    offset: str | None = Query(None),
    archived: str = Query("active", description="Filter by archived: active, archived, all"),
):
    """Список своих тикетов (требует права can_view_own_tickets)."""
    # Обработка пустых значений
    limit_int = int(limit) if limit and limit.strip() else 10
    offset_int = int(offset) if offset and offset.strip() else 0
    
    # Передаём agent_id для проверок прав в сервисе
    ticket_service = TicketService(db, agent_id=agent.id)
    category_service = QuestionCategoryService(db)
    status_service = TicketStatusService(db)
    agent_service = AgentService(db)
    filters = _ticket_filters(request)

    # Фильтр: только свои тикеты
    filters["owner_id"] = agent.id

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
        limit=limit_int,
        offset=offset_int,
        include_unread=True,
        agent_id=agent.id,
    )
    categories = category_service.list(limit=500)
    statuses = status_service.list(limit=200)
    agents = agent_service.list(filters={"is_active": True}, sort_by="full_name", limit=500)
    category_name_by_id = {c.id: c.name for c in categories}
    status_name_by_id = {s.id: s.name for s in statuses}

    # Получаем общее количество
    all_tickets = ticket_service.list(filters=filters if filters else None, limit=999999)
    total_count = len(all_tickets)

    return templates.TemplateResponse(
        "operator/tickets/my.html",
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
            "archived": archived,
            "total_count": total_count,
            "limit_int": limit_int,
            "offset_int": offset_int,
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
            "operator/tickets/detail.html",
            {"request": request, "ticket": None, "error": "Тикет не найден", "agent": agent},
            status_code=404,
        )

    # === Автоматически отмечаем сообщения как прочитанные ===
    # Если текущий агент является владельцем тикета
    if ticket.owner_id == agent.id:
        from app.services.ticket.read_state_service import TicketReadStateService
        read_state_service = TicketReadStateService(db)
        read_state_service.mark_as_read(ticket_id=ticket_id)
    # ===========================================================

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
        "operator/tickets/detail.html",
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

    # Автообновление статуса: если статус "Новая" (ID=1), меняем на "Ответ отправлен" (ID=2)
    if not is_internal_bool and ticket.status_id == 1:
        ticket_service.change_status(
            ticket_id=ticket.id,
            new_status_id=2,  # reply_sent: Ответ отправлен
            agent_id=agent.id,
        )

    return RedirectResponse(url=f"/tickets/{ticket_id}", status_code=303)


@router.post("/tickets/{ticket_id}/assign", response_class=RedirectResponse)
def assign_ticket(
    ticket_id: int,
    request: Request,
    agent: AgentRead = Depends(check_can_assign_others),
    db: Session = Depends(get_db),
    owner_id: str = Form(...),
):
    """Переназначить тикет другому оператору."""
    ticket_service = TicketService(
        db,
        agent_id=agent.id,
        ticket_event_service=TicketEventService(db),
        ticket_read_state_service=TicketReadStateService(db),
    )

    try:
        owner_id_int = int(owner_id)
        if owner_id_int <= 0:
            raise ValueError("Неверный ID оператора")

        ticket_service.update_ticket(
            ticket_id=ticket_id,
            ticket_data=TicketUpdate(owner_id=owner_id_int),
            agent_id=agent.id,
        )

        # Логируем изменение
        client_info = get_client_info(request)
        log_service = AuditLogService(db)
        log_service.log_action(
            action="update",
            entity_type="ticket",
            entity_id=ticket_id,
            agent_id=agent.id,
            details={"assigned_to": owner_id_int},
            **client_info,
        )

        request.session["flash_success"] = f"Тикет переназначен на оператора #{owner_id_int}"

    except Exception as e:
        request.session["flash_error"] = f"Ошибка: {str(e)}"

    return RedirectResponse(url=f"/tickets/{ticket_id}", status_code=303)


@router.post("/tickets/{ticket_id}/update", response_class=RedirectResponse)
def admin_update_ticket(
    ticket_id: int,
    request: Request,
    agent: AgentRead = Depends(check_can_view_tickets),
    db: Session = Depends(get_db),
    status_id: str = Form(""),
    priority: str = Form(""),
    owner_id: str = Form(""),
    category_id: str = Form(""),
):
    """
    Обновление тикета с проверкой прав на каждое поле.

    Права:
    - status_id: can_edit_tickets
    - priority: can_edit_tickets
    - owner_id: can_assign_tickets или can_assign_self
    - category_id: can_man_cat (или админ)
    """
    ticket_service = TicketService(
        db,
        agent_id=agent.id,
        ticket_event_service=TicketEventService(db),
        ticket_read_state_service=TicketReadStateService(db),
    )
    update_data = {}

    # Получаем права агента
    perms = agent.get_permissions_dict()
    is_admin = agent.role == 'admin'

    # Статус (требует can_edit_tickets)
    if status_id and status_id.isdigit():
        if perms.get('can_edit_tickets', False) or is_admin:
            update_data["status_id"] = int(status_id)

    # Приоритет (требует can_edit_tickets)
    if priority:
        if perms.get('can_edit_tickets', False) or is_admin:
            try:
                update_data["priority"] = Priority(priority)
            except ValueError:
                pass

    # Исполнитель (требует can_assign_tickets, can_assign_self или админ)
    if owner_id and owner_id.isdigit():
        owner_val = int(owner_id)
        # Назначение себе (can_assign_self)
        if owner_val == agent.id and (perms.get('can_assign_self', False) or is_admin):
            update_data["owner_id"] = owner_val
        # Назначение другим (can_assign_tickets)
        elif perms.get('can_assign_tickets', False) or is_admin:
            update_data["owner_id"] = owner_val if owner_val > 0 else None

    # Категория (требует can_man_cat или админ)
    if category_id and category_id.isdigit():
        if perms.get('can_man_cat', False) or is_admin:
            cat_val = int(category_id)
            update_data["category_id"] = cat_val if cat_val > 0 else None

    # Применяем только изменённые поля
    if update_data:
        try:
            ticket_service.update_ticket(
                ticket_id=ticket_id,
                ticket_data=TicketUpdate(**update_data),
                agent_id=agent.id,
            )

            # Логируем изменение
            client_info = get_client_info(request)
            log_service = AuditLogService(db)
            log_service.log_action(
                action="update",
                entity_type="ticket",
                entity_id=ticket_id,
                agent_id=agent.id,
                details={"changes": update_data},
                **client_info,
            )
            
            request.session["flash_success"] = "Тикет обновлён"
        except NotFound:
            request.session["flash_error"] = "Тикет не найден"
        except Exception as e:
            request.session["flash_error"] = f"Ошибка: {str(e)}"

    return RedirectResponse(url=f"/tickets/{ticket_id}", status_code=303)


@router.post("/tickets/{ticket_id}/resolve", response_class=RedirectResponse)
def resolve_ticket(
    ticket_id: int,
    request: Request,
    agent: AgentRead = Depends(check_can_resolve),
    db: Session = Depends(get_db),
):
    """Отметить тикет как решённый (закрытый статус)."""
    ticket_service = TicketService(
        db,
        agent_id=agent.id,
        ticket_event_service=TicketEventService(db),
        ticket_read_state_service=TicketReadStateService(db),
    )

    # Статус "Решена" (ID=4)
    RESOLVED_STATUS_ID = 4

    try:
        ticket_service.change_status(
            ticket_id=ticket_id,
            new_status_id=RESOLVED_STATUS_ID,
            agent_id=agent.id,
        )

        # Логируем смену статуса
        client_info = get_client_info(request)
        log_service = AuditLogService(db)
        log_service.log_action(
            action="update",
            entity_type="ticket",
            entity_id=ticket_id,
            agent_id=agent.id,
            details={"resolved_by": agent.full_name, "new_status_id": RESOLVED_STATUS_ID},
            **client_info,
        )

        request.session["flash_success"] = "Тикет отмечен как решённый ✅"

    except Exception as e:
        request.session["flash_error"] = f"Ошибка: {str(e)}"

    return RedirectResponse(url=f"/tickets/{ticket_id}", status_code=303)


@router.post("/tickets/{ticket_id}/delete")
async def delete_ticket(
    request: Request,
    ticket_id: int,
    db: Session = Depends(get_db),
    agent: AgentRead = Depends(check_can_archive_tickets),
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
    db: Session = Depends(get_db),
    ticket_ids: str = Form(...),  # JSON array of ticket IDs
    operation: str = Form(...),  # archive, delete, assign, assign_self, change_status, change_priority, mark_read, hard_delete, merge
    owner_id: str | None = Form(None),
    status_id: str | None = Form(None),
    priority: str | None = Form(None),
    target_ticket_id: str | None = Form(None),  # Для операции merge
):
    """Массовые операции с тикетами."""
    import json

    # Проверка прав в зависимости от операции
    if operation == 'mark_read':
        # Для отметки прочитанным достаточно права просмотра своих тикетов
        agent = check_can_view_own_tickets(request, db)
    elif operation == 'archive':
        # Для архивации нужно специальное право
        agent = check_can_archive_tickets(request, db)
    elif operation == 'hard_delete':
        # Для полного удаления нужно специальное право
        agent = check_can_hard_del_tickets(request, db)
    elif operation == 'assign_self':
        # Для назначения себе нужно право can_assign_self
        agent = check_can_assign_self(request, db)
    elif operation == 'assign':
        # Для назначения другим нужно право can_assign_others
        agent = check_can_assign_others(request, db)
    elif operation == 'merge':
        # Для слияния нужно право can_merge_tickets
        agent = check_can_merge_tickets(request, db)
    else:
        # Для остальных операций нужно право на редактирование
        agent = check_can_edit_tickets(request, db)

    try:
        ids = json.loads(ticket_ids)
        if not isinstance(ids, list) or not all(isinstance(i, int) or (isinstance(i, str) and i.isdigit()) for i in ids):
            raise ValueError("Invalid ticket IDs")
        # Конвертируем в int если строки
        ids = [int(i) if isinstance(i, str) else i for i in ids]
    except (json.JSONDecodeError, ValueError) as e:
        request.session["flash_error"] = f"Неверный формат данных: {e}"
        return RedirectResponse(url="/tickets", status_code=303)

    # Создаём сервисы после получения agent
    ticket_service = TicketService(
        db,
        agent_id=agent.id,
        ticket_event_service=TicketEventService(db),
        ticket_read_state_service=TicketReadStateService(db),
    )

    success_count = 0
    error_count = 0

    # Обработка слияния (отдельно, до цикла)
    if operation == 'merge' and target_ticket_id:
        try:
            target_id_int = int(target_ticket_id)
            
            # Объединяем все выбранные тикеты (кроме целевого) в целевой
            merged_count = 0
            for source_id in ids:
                if int(source_id) != target_id_int:
                    ticket_service.merge_tickets(
                        source_ticket_id=int(source_id),
                        target_ticket_id=target_id_int,
                        agent_id=agent.id,
                    )
                    merged_count += 1
            
            success_count = merged_count

            # Логируем слияние
            client_info = get_client_info(request)
            log_service = AuditLogService(db)
            log_service.log_action(
                action="merge",
                entity_type="ticket",
                entity_id=target_id_int,
                agent_id=agent.id,
                details={"bulk_operation": "merge", "target_ticket_id": target_id_int, "merged_count": merged_count},
                **client_info,
            )
        except Exception as merge_error:
            error_count += 1
            print(f"Merge error: {merge_error}")
        
        # Flash-сообщение
        if success_count > 0:
            request.session["flash_success"] = f"Объединено тикетов: {success_count}"
        if error_count > 0:
            request.session["flash_error"] = f"Ошибок: {error_count}"

        # Возвращаем на страницу, откуда пришли (Referer)
        referer = request.headers.get("referer")
        if referer:
            return RedirectResponse(url=referer, status_code=303)
        else:
            return RedirectResponse(url="/tickets", status_code=303)

    # Остальные операции обрабатываем в цикле
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

            elif operation == 'mark_read':
                # Отметить тикет как прочитанный
                ticket_service.mark_as_read(ticket_id=ticket_id)
                success_count += 1

                # Логируем отметку о прочтении
                client_info = get_client_info(request)
                log_service = AuditLogService(db)
                log_service.log_action(
                    action="update",
                    entity_type="ticket",
                    entity_id=ticket_id,
                    agent_id=agent.id,
                    details={"bulk_operation": "mark_read", "track_id": ticket.track_id},
                    **client_info,
                )

            elif operation == 'anonymize':
                # Анонимизировать тикет (установить флаг is_anonymized)
                from app.models.ticket import Ticket
                
                ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
                if ticket:
                    ticket.is_anonymized = True
                    success_count += 1
                
                db.commit()

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

            elif operation == 'hard_delete':
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

            elif operation == 'assign':
                # Назначение или снятие назначения
                # owner_id = "0" означает снятие назначения (owner_id = None)
                from app.models.ticket import Ticket
                
                if owner_id == "0":
                    # Снятие назначения - прямое обновление в БД
                    db.query(Ticket).filter(Ticket.id == ticket_id).update({"owner_id": None})
                    db.commit()
                    new_owner_id = None
                elif owner_id and owner_id.isdigit():
                    # Назначение на оператора
                    new_owner_id = int(owner_id)
                    ticket_service.update_ticket(
                        ticket_id=ticket_id,
                        ticket_data=TicketUpdate(owner_id=new_owner_id),
                        agent_id=agent.id,
                    )
                else:
                    new_owner_id = None
                
                success_count += 1

                # Логируем назначение
                client_info = get_client_info(request)
                log_service = AuditLogService(db)
                log_service.log_action(
                    action="update",
                    entity_type="ticket",
                    entity_id=ticket_id,
                    agent_id=agent.id,
                    details={"bulk_operation": "assign", "track_id": ticket.track_id, "new_owner_id": new_owner_id},
                    **client_info,
                )

            elif operation == 'assign_self':
                # Назначить тикет себе
                ticket_service.update_ticket(
                    ticket_id=ticket_id,
                    ticket_data=TicketUpdate(owner_id=agent.id),
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
                    details={"bulk_operation": "assign_self", "track_id": ticket.track_id},
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

            elif operation == 'change_priority' and priority:
                try:
                    ticket_service.update_ticket(
                        ticket_id=ticket_id,
                        ticket_data=TicketUpdate(priority=Priority(priority)),
                        agent_id=agent.id,
                    )
                    success_count += 1

                    # Логируем изменение приоритета
                    client_info = get_client_info(request)
                    log_service = AuditLogService(db)
                    log_service.log_action(
                        action="update",
                        entity_type="ticket",
                        entity_id=ticket_id,
                        agent_id=agent.id,
                        details={"bulk_operation": "change_priority", "track_id": ticket.track_id, "new_priority": priority},
                        **client_info,
                    )
                except ValueError:
                    error_count += 1

        except Exception as e:
            error_count += 1
            print(f"Error processing ticket {ticket_id}: {e}")

    # Flash-сообщение
    if success_count > 0:
        request.session["flash_success"] = f"Обработано тикетов: {success_count}"
    if error_count > 0:
        request.session["flash_error"] = f"Ошибок: {error_count}"

    # Возвращаем на страницу, откуда пришли (Referer)
    referer = request.headers.get("referer")
    if referer:
        return RedirectResponse(url=referer, status_code=303)
    else:
        # Если Referer нет, возвращаем на /tickets
        return RedirectResponse(url="/tickets", status_code=303)


@router.get("/attachments/{attachment_id}/download", response_class=HTMLResponse)
def attachment_download(
    attachment_id: int,
    request: Request,
    agent: CurrentAgent,
    db: Session = Depends(get_db),
):
    """Скачать вложение (для авторизованных операторов)."""
    from app.services.ticket.attachment_service import AttachmentService
    from app.services.file_storage_service import FileStorageService
    
    attachment_service = AttachmentService(db)
    att = attachment_service.get_orm(attachment_id=attachment_id)
    
    print(f"[DEBUG] Download attachment {attachment_id}")
    print(f"[DEBUG] Attachment: {att}")
    
    if att is None:
        # Вложение не найдено в БД
        print(f"[DEBUG] Attachment not found in DB")
        return templates.TemplateResponse(
            "error/file_not_found.html",
            {
                "request": request,
                "agent": agent,
                "attachment_id": attachment_id,
                "error_message": "Вложение не найдено в базе данных",
            },
            status_code=404,
        )

    file_storage = FileStorageService()
    path = file_storage.get_path(att.file_path)
    
    print(f"[DEBUG] File path: {path}")
    print(f"[DEBUG] File exists: {path.exists()}")
    print(f"[DEBUG] File is_file: {path.is_file()}")
    
    # Проверяем существование файла ПЕРЕД тем как возвращать FileResponse
    if not path.exists():
        print(f"[DEBUG] File does not exist, returning HTML error")
        return templates.TemplateResponse(
            "error/file_not_found.html",
            {
                "request": request,
                "agent": agent,
                "attachment_id": attachment_id,
                "error_message": "Файл не найден на диске",
            },
            status_code=404,
        )
    
    if not path.is_file():
        print(f"[DEBUG] Path is not a file, returning HTML error")
        return templates.TemplateResponse(
            "error/file_not_found.html",
            {
                "request": request,
                "agent": agent,
                "attachment_id": attachment_id,
                "error_message": "Указанный путь не является файлом",
            },
            status_code=404,
        )

    print(f"[DEBUG] File exists, returning FileResponse")
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


# === API endpoints ===

@router.post("/tickets/{ticket_id}/mark-as-read")
def mark_ticket_as_read(
    ticket_id: int,
    request: Request,
    agent: AgentRead = Depends(check_can_view_tickets),
    db: Session = Depends(get_db),
):
    """
    Отметить сообщения в тикете как прочитанные.

    Используется для сброса счётчика непрочитанных сообщений.
    """
    from app.services.ticket.read_state_service import TicketReadStateService

    print(f"\n=== [DEBUG] mark-as-read: ticket_id={ticket_id}, agent_id={agent.id}, agent_login={agent.login}")

    # Проверяем, что тикет существует (через TicketService без проверки прав)
    from app.models.ticket import Ticket
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    print(f"[DEBUG] ticket found: {ticket is not None}")
    if ticket is None:
        print(f"[DEBUG] ticket not found!")
        raise HTTPException(status_code=404, detail="Тикет не найден")

    # Проверяем, что агент имеет доступ к тикету (владелец или админ)
    print(f"[DEBUG] ticket.owner_id={ticket.owner_id}, agent.id={agent.id}, agent.role={agent.role}")
    if ticket.owner_id != agent.id and agent.role != "admin":
        print(f"[DEBUG] access denied!")
        raise HTTPException(status_code=403, detail="Нет доступа к тикету")

    # Отмечаем как прочитанное
    print(f"[DEBUG] calling mark_as_read...")
    read_state_service = TicketReadStateService(db)
    read_state_service.mark_as_read(ticket_id=ticket_id)
    print(f"[DEBUG] mark_as_read done!")

    # Если запрос пришёл с тестовой страницы, редиректим обратно
    referer = request.headers.get("referer", "")
    print(f"[DEBUG] referer={referer}")
    if "/test/unread" in referer:
        print(f"[DEBUG] redirecting to /test/unread")
        return RedirectResponse(url="/test/unread", status_code=303)

    print(f"[DEBUG] returning JSON")
    return {"success": True, "ticket_id": ticket_id}


@router.post("/messages/{message_id}/anonymize", response_class=RedirectResponse)
def anonymize_message(
    message_id: int,
    request: Request,
    agent: AgentRead = Depends(check_can_edit_tickets),
    db: Session = Depends(get_db),
):
    """
    Анонимизировать сообщение.
    
    Удаляет персональные данные (имя, email), сохраняя IP для аудита.
    """
    from app.services.ticket.message_service import MessageService
    from app.models.message import Message
    
    message_service = MessageService(db, ticket_event_service=TicketEventService(db))
    
    try:
        # Анонимизируем сообщение
        message_service.anonymize_message(
            message_id=message_id,
            agent_id=agent.id,
        )
        
        request.session["flash_success"] = "Сообщение анонимизировано"
    except Exception as e:
        request.session["flash_error"] = f"Ошибка: {str(e)}"
    
    # Возвращаем на страницу тикета
    # Сначала получаем ticket_id из сообщения
    msg = db.query(Message).filter(Message.id == message_id).first()
    if msg:
        return RedirectResponse(url=f"/tickets/{msg.ticket_id}", status_code=303)
    else:
        return RedirectResponse(url="/tickets", status_code=303)


@router.post("/tickets/{ticket_id}/anonymize", response_class=RedirectResponse)
def anonymize_ticket(
    ticket_id: int,
    request: Request,
    agent: AgentRead = Depends(check_can_anonymize_tickets),
    db: Session = Depends(get_db),
):
    """
    Анонимизировать тикет.

    Устанавливает флаг is_anonymized.
    При чтении данные будут заменяться на "Аноним".
    """
    from app.models.ticket import Ticket

    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if ticket is None:
        request.session["flash_error"] = "Тикет не найден"
        return RedirectResponse(url="/tickets", status_code=303)

    try:
        # Устанавливаем флаг анонимизации
        ticket.is_anonymized = True
        db.commit()

        request.session["flash_success"] = f"Тикет {ticket.track_id} анонимизирован"

    except Exception as e:
        db.rollback()
        request.session["flash_error"] = f"Ошибка: {str(e)}"

    return RedirectResponse(url=f"/tickets/{ticket_id}", status_code=303)


@router.get("/tickets/{ticket_id}/unread-count")
def get_ticket_unread_count(
    ticket_id: int,
    agent: AgentRead = Depends(check_can_view_tickets),
    db: Session = Depends(get_db),
):
    """
    Получить количество непрочитанных сообщений в тикете.
    """
    ticket_service = TicketService(db)

    # Проверяем, что тикет существует
    try:
        ticket = ticket_service.get(ticket_id=ticket_id)
    except NotFound:
        raise HTTPException(status_code=404, detail="Тикет не найден")

    # Проверяем, что агент имеет доступ к тикету (владелец или админ)
    if ticket.owner_id != agent.id and agent.role != "admin":
        raise HTTPException(status_code=403, detail="Нет доступа к тикету")

    unread_count = ticket_service.get_unread_count(ticket_id=ticket_id)

    return {"ticket_id": ticket_id, "unread_count": unread_count}


@router.get("/tickets/unread/total")
def get_total_unread_count(
    agent: AgentRead = Depends(check_can_view_tickets),
    db: Session = Depends(get_db),
):
    """
    Получить общее количество непрочитанных сообщений по всем тикетам агента.

    Возвращает сумму непрочитанных сообщений во всех тикетах, которые ведёт агент.
    """
    from app.services.ticket.read_state_service import TicketReadStateService

    read_state_service = TicketReadStateService(db)

    total_unread = read_state_service.get_total_unread_for_agent(
        agent_id=agent.id,
        exclude_internal=True,
    )

    return {
        "agent_id": agent.id,
        "total_unread": total_unread,
    }


@router.get("/tickets/unread/list")
def get_tickets_with_unread(
    agent: AgentRead = Depends(check_can_view_tickets),
    db: Session = Depends(get_db),
    min_unread: int = Query(1, ge=1, description="Минимальное кол-во непрочитанных"),
):
    """
    Получить список тикетов агента с непрочитанными сообщениями.

    Возвращает тикеты, отсортированные по количеству непрочитанных сообщений (убывание).
    """
    from app.services.ticket.read_state_service import TicketReadStateService

    read_state_service = TicketReadStateService(db)

    tickets_with_unread = read_state_service.get_tickets_with_unread(
        agent_id=agent.id,
        exclude_internal=True,
        min_unread=min_unread,
    )

    return {
        "agent_id": agent.id,
        "count": len(tickets_with_unread),
        "tickets": tickets_with_unread,
    }


@router.get("/tickets/{ticket_id}/available-operators")
def get_available_operators(
    ticket_id: int,
    agent: AgentRead = Depends(check_can_view_tickets),
    db: Session = Depends(get_db),
    random: bool = Query(False, description="Вернуть случайного оператора"),
):
    """
    Получить список операторов, доступных для назначения на тикет.

    Операторы отбираются по категории вопроса, совпадающей с категорией тикета.
    Возвращает операторов с score (приоритетом назначения).

    ?random=true — вернуть одного случайного оператора
    """
    from app.services.ticket.assignment_service import AssignmentService
    from app.models.ticket import Ticket

    # Проверяем, что тикет существует
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if ticket is None:
        raise HTTPException(status_code=404, detail="Тикет не найден")

    # Получаем доступных операторов (ищем по категории, НЕ по департаменту)
    assignment_service = AssignmentService(db)
    operators = assignment_service.get_available_operators(
        category_id=ticket.category_id,
        department_id=None,  # НЕ фильтруем по департаменту
        only_auto_assign=False,
        include_inactive=False,
        limit=None,  # Сначала получаем всех
        random=False,  # Сами перемешаем после фильтрации
    )

    # Сначала фильтруем только операторов с доступом (score > 0)
    suitable_operators = [op for op in operators if op.score > 0]

    # Теперь перемешиваем и берём одного случайного
    if random and suitable_operators:
        import random as rnd
        rnd.shuffle(suitable_operators)
        suitable_operators = suitable_operators[:1]

    # Формируем ответ
    return {
        "ticket_id": ticket_id,
        "category_id": ticket.category_id,
        "department_id": ticket.department_id,
        "random": random,
        "count": len(suitable_operators),
        "operators": [
            {
                "id": op.agent.id,
                "full_name": op.agent.full_name,
                "email": op.agent.email,
                "login": op.agent.login,
                "role": op.agent.role.value,
                "score": op.score,
                "has_explicit_access": op.has_explicit_access,
                "is_admin": op.is_admin,
                "department_name": op.department_name,
                "auto_assign": op.agent.auto_assign,
                "email_notifications": op.agent.email_notifications,
            }
            for op in suitable_operators
        ],
    }


# =============================================================================
# Управление банами (Email и IP)
# =============================================================================

@router.get("/bans", response_class=HTMLResponse)
def bans_list(
    request: Request,
    agent: AgentRead = Depends(check_can_view_tickets),  # Требуется право просмотра тикетов
    db: Session = Depends(get_db),
):
    """Страница управления банами (email и IP)."""
    banned_emails = BanService.get_banned_emails(db)
    banned_ips = BanService.get_banned_ips(db)

    return templates.TemplateResponse(
        "operator/bans/list.html",
        {
            "request": request,
            "agent": agent,
            "banned_emails": banned_emails,
            "banned_ips": banned_ips,
        },
    )


@router.post("/bans/email/add", response_class=RedirectResponse)
def ban_email_add(
    request: Request,
    agent: AgentRead = Depends(check_can_view_tickets),
    db: Session = Depends(get_db),
    email: str = Form(...),
    reason: str = Form(""),
):
    """Добавить email в бан-лист."""
    try:
        BanService.add_email_ban(
            db=db,
            email=email.strip(),
            banned_by=agent.id,
            reason=reason.strip() if reason else None,
        )
        request.session["flash_success"] = f"Email '{email}' добавлен в чёрный список."
    except ValueError as e:
        request.session["flash_error"] = str(e)

    return RedirectResponse(url="/bans", status_code=303)


@router.post("/bans/email/remove", response_class=RedirectResponse)
def ban_email_remove(
    request: Request,
    ban_id: int = Form(...),
    agent: AgentRead = Depends(check_can_view_tickets),
    db: Session = Depends(get_db),
):
    """Удалить email из бан-листа."""
    if BanService.remove_email_ban(db, ban_id):
        request.session["flash_success"] = "Email удалён из чёрного списка."
    else:
        request.session["flash_error"] = "Бан не найден."

    return RedirectResponse(url="/bans", status_code=303)


@router.post("/bans/ip/add", response_class=RedirectResponse)
def ban_ip_add(
    request: Request,
    agent: AgentRead = Depends(check_can_view_tickets),
    db: Session = Depends(get_db),
    ip_from: str = Form(...),
    ip_to: str = Form(""),
    ip_display: str = Form(""),
):
    """Добавить IP или диапазон IP в бан-лист."""
    from app.services.utils import ip_to_int

    try:
        # Валидация IP
        ip_to_int(ip_from)
        ip_to_val = ip_to.strip() if ip_to and ip_to.strip() else None
        if ip_to_val:
            ip_to_int(ip_to_val)

        BanService.add_ip_ban(
            db=db,
            ip_from=ip_from.strip(),
            ip_to=ip_to_val if ip_to_val else None,
            banned_by=agent.id,
            ip_display=ip_display.strip() if ip_display and ip_display.strip() else None,
        )

        display = ip_display.strip() if ip_display and ip_display.strip() else (
            f"{ip_from} - {ip_to_val}" if ip_to_val else ip_from
        )
        request.session["flash_success"] = f"IP-диапазон '{display}' добавлен в чёрный список."

    except ValueError as e:
        request.session["flash_error"] = f"Неверный формат IP: {e}"

    return RedirectResponse(url="/bans", status_code=303)


@router.post("/bans/ip/remove", response_class=RedirectResponse)
def ban_ip_remove(
    request: Request,
    ban_id: int = Form(...),
    agent: AgentRead = Depends(check_can_view_tickets),
    db: Session = Depends(get_db),
):
    """Удалить IP из бан-листа."""
    if BanService.remove_ip_ban(db, ban_id):
        request.session["flash_success"] = "IP удалён из чёрного списка."
    else:
        request.session["flash_error"] = "Бан не найден."

    return RedirectResponse(url="/bans", status_code=303)
