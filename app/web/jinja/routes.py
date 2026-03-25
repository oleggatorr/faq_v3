from __future__ import annotations

from pathlib import Path
from typing import Any
from urllib.parse import unquote

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.core.auth import CurrentAgent, CurrentAgentOptional
from app.core.config import settings
from app.core.security import create_access_token, verify_password
from app.models import get_db
from app.models.agent import Agent
from app.services.agent_service import AgentService
from app.services.attachment_service import AttachmentService
from app.services.department_service import DepartmentService
from app.services.errors import NotFound as ServiceNotFound
from app.services.language_service import LanguageService
from app.services.message_service import MessageService
from app.models.ticket import Priority
from app.schemas.ticket import TicketCreate
from app.services.errors import Conflict as ServiceConflict
from app.services.file_storage_service import FileStorageError, FileStorageService
from app.services.question_category_service import QuestionCategoryService
from app.services.ticket_event_service import TicketEventService
from app.services.ticket_service import TicketService
from app.services.ticket_status_service import TicketStatusService
from fastapi.templating import Jinja2Templates


router = APIRouter(prefix="", tags=["jinja"])

templates_dir = Path(__file__).resolve().parent / "templates"
templates = Jinja2Templates(directory=str(templates_dir))

from markupsafe import Markup

def nl2br(value: str) -> Markup:
    """Заменяет переносы строк на <br> для безопасного HTML-вывода."""
    if not value:
        return Markup("")
    return Markup(value.replace("\n", "<br>\n"))

# Регистрируем фильтр в окружении Jinja2
templates.env.filters["nl2br"] = nl2br


def _parse_int(value: str | None) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except ValueError:
        return None


def _parse_bool(value: str | None) -> bool | None:
    if value is None or value == "":
        return None
    v = value.lower()
    if v in ("1", "true", "yes", "on"):
        return True
    if v in ("0", "false", "no", "off"):
        return False
    return None


def _ticket_filters(request: Request) -> dict[str, Any]:
    """Extract ticket filters from query params (whitelist)."""
    params = request.query_params
    filters: dict[str, Any] = {}
    int_keys = {
        "id", "department_id", "language_id", "category_id", "status_id",
        "owner_id", "opened_by_id", "merged_into_id", "messages_count", "attachments_count",
    }
    bool_keys = {"is_archived", "is_locked"}
    str_keys = {"track_id", "customer_name", "customer_email", "subject"}

    for key in int_keys:
        val = _parse_int(params.get(key))
        if val is not None:
            filters[key] = val
    for key in bool_keys:
        val = _parse_bool(params.get(key))
        if val is not None:
            filters[key] = val
    for key in str_keys:
        val = params.get(key)
        if val:
            filters[key] = val

    if "priority" in params and params["priority"]:
        filters["priority"] = params["priority"]
    return filters


def _agent_filters(request: Request) -> dict[str, Any]:
    params = request.query_params
    filters: dict[str, Any] = {}
    if _parse_int(params.get("id")) is not None:
        filters["id"] = _parse_int(params.get("id"))
    if params.get("full_name"):
        filters["full_name"] = params["full_name"]
    if params.get("email"):
        filters["email"] = params["email"]
    if _parse_int(params.get("department_id")) is not None:
        filters["department_id"] = _parse_int(params.get("department_id"))
    val = _parse_bool(params.get("is_active"))
    if val is not None:
        filters["is_active"] = val
    return filters


def _department_filters(request: Request) -> dict[str, Any]:
    params = request.query_params
    filters: dict[str, Any] = {}
    if _parse_int(params.get("id")) is not None:
        filters["id"] = _parse_int(params.get("id"))
    if params.get("name"):
        filters["name"] = params["name"]
    val = _parse_bool(params.get("is_active"))
    if val is not None:
        filters["is_active"] = val
    return filters


def _language_filters(request: Request) -> dict[str, Any]:
    params = request.query_params
    filters: dict[str, Any] = {}
    if _parse_int(params.get("id")) is not None:
        filters["id"] = _parse_int(params.get("id"))
    if params.get("code"):
        filters["code"] = params["code"]
    if params.get("name"):
        filters["name"] = params["name"]
    val = _parse_bool(params.get("is_active"))
    if val is not None:
        filters["is_active"] = val
    return filters


@router.get("/", response_class=HTMLResponse)
def index(request: Request, agent: CurrentAgentOptional):
    return templates.TemplateResponse(
        "index.html",
        {"request": request, "agent": agent},
    )


@router.get("/home-page", response_class=RedirectResponse)
def home_page(agent: CurrentAgent):
    return RedirectResponse(url="/operator/home-page", status_code=303)

@router.get("/operator/home-page", response_class=HTMLResponse)
def operator_home_page(request: Request, agent: CurrentAgent):
    return templates.TemplateResponse(
        "operator/home_page.html",
        {"request": request, "agent": agent},
    )


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
    email: str = Form(...),
    password: str = Form(...),
    next: str = Form("/"),
):
    agent = db.query(Agent).filter(Agent.email == email, Agent.is_active == True).one_or_none()
    if not agent or not verify_password(password, agent.password_hash):
        return templates.TemplateResponse(
            "auth/login.html",
            {
                "request": request,
                "next_url": next,
                "error": "Неверный email или пароль",
                "agent": None,
            },
            status_code=401,
        )
    token = create_access_token(data={"sub": str(agent.id)})
    response = RedirectResponse(url=unquote(next) if next else "/", status_code=303)
    response.set_cookie(
        key=settings.COOKIE_NAME,
        value=token,
        max_age=settings.COOKIE_MAX_AGE,
        httponly=True,
        samesite="lax",
    )
    return response


@router.post("/logout", response_class=RedirectResponse)
def logout():
    response = RedirectResponse(url="/", status_code=303)
    response.delete_cookie(key=settings.COOKIE_NAME)
    return response


@router.get("/new-ticket", response_class=HTMLResponse)
def new_ticket_form(
    request: Request,
    agent: CurrentAgentOptional,
    db: Session = Depends(get_db),
):
    """Публичная форма создания тикета (без авторизации)."""
    dept_service = DepartmentService(db)
    lang_service = LanguageService(db)
    cat_service = QuestionCategoryService(db)
    departments = dept_service.list(filters={"is_active": True}, sort_by="sort_order", limit=200)
    languages = lang_service.list(filters={"is_active": True}, sort_by="sort_order", limit=100)
    categories = cat_service.list(filters={"is_active": True}, sort_by="sort_order", limit=200)
    return templates.TemplateResponse(
        "tickets/new.html",
        {
            "request": request,
            "departments": departments,
            "languages": languages,
            "categories": categories,
            "priorities": list(Priority),
            "agent": agent,
            "error": None,
            "form_data": {},
        },
    )


@router.get("/get-ticket", response_class=HTMLResponse)
def get_ticket_form(request: Request, agent: CurrentAgentOptional):
    """Публичная форма: ввод track_id + email для доступа к переписке."""
    return templates.TemplateResponse(
        "tickets/get_ticket.html",
        {"request": request, "agent": agent, "error": None},
    )


@router.post("/get-ticket", response_class=RedirectResponse)
def get_ticket_submit(
    track_id: str = Form(...),
):
    track_id = track_id.strip().upper()
    return RedirectResponse(url=f"/ticket/{track_id}/message", status_code=303)


@router.get("/ticket/{track_id}", response_class=HTMLResponse)
def ticket_by_track_id(
    request: Request,
    track_id: str,
    agent: CurrentAgentOptional,
    db: Session = Depends(get_db),
):
    """
    Единая точка:
    - без авторизации: редирект в переписку `/ticket/{track_id}/message`
    - с авторизацией: страница тикета (как `/tickets/{id}`)
    """
    track_id = track_id.strip().upper()
    if not agent:
        return RedirectResponse(url=f"/ticket/{track_id}/message", status_code=303)

    ticket_service = TicketService(db)
    try:
        ticket = ticket_service.get_by_track_id(track_id)
    except ServiceNotFound:
        return templates.TemplateResponse(
            "tickets/detail.html",
            {
                "request": request,
                "ticket": None,
                "messages": [],
                "events": [],
                "attachments_by_message": {},
                "error": "Тикет не найден",
                "agent": agent,
            }
            ,
            status_code=404,
        )

    return RedirectResponse(url=f"/tickets/{ticket.id}", status_code=303)



@router.get("/ticket/{track_id}/message", response_class=HTMLResponse)
def ticket_messages_by_track_id(
    request: Request,
    track_id: str,
    agent: CurrentAgentOptional,
    db: Session = Depends(get_db),
):
    """
    Переписка по тикету:
    - оператор (авторизован): редирект на `/tickets/{id}`
    - пользователь (без авторизации): публичный чат по track_id
    """
    track_id = track_id.strip().upper()
    ticket_service = TicketService(db)
    try:
        ticket = ticket_service.get_by_track_id(track_id)
    except ServiceNotFound:
        return templates.TemplateResponse(
            "tickets/get_ticket.html",
            {"request": request, "agent": agent, "error": "Тикет не найден"},
            status_code=404,
        )

    if agent:
        return RedirectResponse(url=f"/tickets/{ticket.id}", status_code=303)

    message_service = MessageService(db)
    attachment_service = AttachmentService(db)
    messages = message_service.list(
        filters={"ticket_id": ticket.id, "is_internal": False},
        sort_by="created_at",
        sort_desc=False,
        limit=200,
    )
    attachments_by_message: dict[int, list] = {}
    for msg in messages:
        attachments_by_message[msg.id] = attachment_service.list(
            filters={"message_id": msg.id},
            sort_by="id",
            limit=50,
        )

    return templates.TemplateResponse(
        "tickets/public_chat.html",
        {
            "request": request,
            "agent": None,
            "ticket": ticket,
            "messages": messages,
            "attachments_by_message": attachments_by_message,
            "error": None,
        },
    )


@router.post("/ticket/{track_id}/message", response_class=RedirectResponse)
async def ticket_public_reply(
    track_id: str,
    request: Request,
    db: Session = Depends(get_db),
    body: str = Form(...),
    attachments: list[UploadFile] = File(default=[]),
):
    """Публичный ответ по тикету (проверка по email заявителя)."""
    track_id = track_id.strip().upper()
    ticket_service = TicketService(db, ticket_event_service=TicketEventService(db))
    try:
        ticket = ticket_service.get_by_track_id(track_id)
    except ServiceNotFound:
        raise HTTPException(status_code=404, detail="Тикет не найден")


    from app.schemas.message import MessageCreate

    message_service = MessageService(db, ticket_event_service=TicketEventService(db))
    message_data = MessageCreate(
        ticket_id=ticket.id,
        agent_id=None,
        customer_name=ticket.customer_name,
        subject=ticket.subject,
        body=body.strip(),
        is_internal=False,
        is_automatic=False,
        ip_address=(request.client.host if request.client else None),
    )
    message = message_service.add_message(message_data=message_data, agent_id=None)

    if attachments:
        file_storage = FileStorageService()
        attachment_service = AttachmentService(db, ticket_event_service=TicketEventService(db))
        files_meta: list[dict] = []
        for uf in attachments:
            if not uf.filename or uf.filename.strip() == "":
                continue
            content = await uf.read()
            if len(content) == 0:
                continue
            try:
                meta = file_storage.save(
                    content=content,
                    original_filename=uf.filename,
                    mime_type=uf.content_type or "application/octet-stream",
                )
                files_meta.append(meta)
            except FileStorageError:
                pass
        if files_meta:
            attachment_service.add_attachments(
                message=message,
                uploaded_by_agent_id=None,
                files=files_meta,
            )

    # Email: уведомить назначенного оператора (если есть), иначе департамент
    try:
        from app.models.department import Department
        from app.services.email_service import notify_new_message

        to_email = None
        if ticket.owner_id:
            owner_agent = db.query(Agent).filter(Agent.id == ticket.owner_id).one_or_none()
            if owner_agent and owner_agent.email:
                to_email = owner_agent.email
        if not to_email and ticket.department_id:
            dept = db.query(Department).filter(Department.id == ticket.department_id).one_or_none()
            if dept and dept.email:
                to_email = dept.email
        if to_email:
            notify_new_message(
                to_email=to_email,
                track_id=ticket.track_id,
                subject=ticket.subject,
                message_preview=body.strip(),
                from_name=ticket.customer_name,
            )
    except Exception:
        pass

    return RedirectResponse(url=f"/ticket/{track_id}/message", status_code=303)


@router.post("/new-ticket", response_class=HTMLResponse)
async def new_ticket_submit(
    request: Request,
    db: Session = Depends(get_db),
    customer_name: str = Form(...),
    customer_email: str = Form(...),
    subject: str = Form(...),
    body: str = Form(...),
    department_id: int = Form(...),
    language_id: str = Form(""),
    category_id: str = Form(""),
    priority: str = Form("normal"),
    attachments: list[UploadFile] = File(default=[]),
):
    """Публичное создание тикета. После успеха — страница с трек-номером."""
    dept_service = DepartmentService(db)
    lang_service = LanguageService(db)
    cat_service = QuestionCategoryService(db)
    departments = dept_service.list(filters={"is_active": True}, sort_by="sort_order", limit=200)
    languages = lang_service.list(filters={"is_active": True}, sort_by="sort_order", limit=100)
    categories = cat_service.list(filters={"is_active": True}, sort_by="sort_order", limit=200)
    language_id_int = _parse_int(language_id) if language_id else None
    category_id_int = _parse_int(category_id) if category_id else None
    form_data = {
        "customer_name": customer_name,
        "customer_email": customer_email,
        "subject": subject,
        "body": body,
        "department_id": department_id,
        "language_id": language_id_int,
        "category_id": category_id_int,
        "priority": priority,
    }

    customer_ip = request.client.host if request.client else "0.0.0.0"
    if len(customer_ip) > 45:
        customer_ip = customer_ip[:45]

    ticket_service = TicketService(db, ticket_event_service=TicketEventService(db))
    try:
        track_id = ticket_service.generate_track_id()
        try:
            priority_enum = Priority(priority) if priority else Priority.normal
        except ValueError:
            priority_enum = Priority.normal

        ticket_data = TicketCreate(
            track_id=track_id,
            customer_name=customer_name.strip(),
            customer_email=customer_email.strip(),
            customer_ip=customer_ip,
            department_id=department_id,
            language_id=language_id_int,
            category_id=category_id_int,
            status_id=1,
            priority=priority_enum,
            subject=subject.strip(),
        )

        ticket, message = ticket_service.create_ticket_with_first_message(
            ticket_data=ticket_data,
            first_message_body=body.strip(),
        )

        if attachments:
            file_storage = FileStorageService()
            attachment_service = AttachmentService(
                db, ticket_event_service=TicketEventService(db)
            )
            files_meta: list[dict] = []
            for uf in attachments:
                if not uf.filename or uf.filename.strip() == "":
                    continue
                content = await uf.read()
                if len(content) == 0:
                    continue
                try:
                    meta = file_storage.save(
                        content=content,
                        original_filename=uf.filename,
                        mime_type=uf.content_type or "application/octet-stream",
                    )
                    files_meta.append(meta)
                except FileStorageError:
                    pass
            if files_meta:
                attachment_service.add_attachments(
                    message=message,
                    uploaded_by_agent_id=None,
                    files=files_meta,
                )

        # Уведомление департаменту о новом обращении
        from app.models.department import Department
        from app.services.email_service import notify_ticket_created
        dept = db.query(Department).filter(Department.id == ticket.department_id).one_or_none()
        to_email = (dept.email if dept and dept.email else None) or "olegfesenko365@gmail.com"
        try:
            notify_ticket_created(
                to_email=to_email,
                track_id=ticket.track_id,
                subject=ticket.subject,
                customer_name=ticket.customer_name,
                body_preview=body.strip(),
            )
        except Exception:
            pass
    except ServiceConflict:
        return templates.TemplateResponse(
            "tickets/new.html",
            {
                "request": request,
                "departments": departments,
                "languages": languages,
                "categories": categories,
                "priorities": list(Priority),
                "agent": None,
                "error": "Ошибка создания. Попробуйте ещё раз.",
                "form_data": form_data,
            },
            status_code=409,
        )

    return templates.TemplateResponse(
        "tickets/created.html",
        {
            "request": request,
            "track_id": ticket.track_id,
            "agent": None,
        },
    )


@router.get("/tickets", response_class=HTMLResponse)
def tickets_list(
    request: Request,
    agent: CurrentAgent,
    db: Session = Depends(get_db),
    q: str = Query("", description="Quick search by track_id/subject/customer"),
    sort_by: str = Query("id", description="Sort field"),
    sort_desc: bool = Query(False, description="Sort descending"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    ticket_service = TicketService(db)
    category_service = QuestionCategoryService(db)
    status_service = TicketStatusService(db)
    filters = _ticket_filters(request)
    if q and not any(filters.get(k) for k in ("track_id", "subject", "customer_name", "customer_email")):
        filters["track_id"] = q.strip()

    tickets = ticket_service.list(
        filters=filters if filters else None,
        sort_by=sort_by,
        sort_desc=sort_desc,
        limit=limit,
        offset=offset,
    )
    categories = category_service.list(limit=500)
    statuses = status_service.list(limit=200)
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
            "category_name_by_id": category_name_by_id,
            "status_name_by_id": status_name_by_id,
            "filters": filters,
            "q": q,
            "sort_by": sort_by,
            "sort_desc": sort_desc,
            "limit": limit,
            "offset": offset,
        },
    )


@router.get("/list-tickets", response_class=RedirectResponse)
def list_tickets_alias(agent: CurrentAgent):
    return RedirectResponse(url="/tickets", status_code=303)


@router.get("/tickets/{ticket_id}", response_class=HTMLResponse)
def ticket_detail_admin(
    request: Request,
    ticket_id: int,
    agent: CurrentAgent,
    db: Session = Depends(get_db),
):
    from app.models.ticket_event import TicketEvent
    # === 1. Тикет ===
    ticket_service = TicketService(db)
    try:
        ticket = ticket_service.get(ticket_id=ticket_id)
    except NotFound:
        return templates.TemplateResponse(
            "tickets/detail.html",
            {"request": request, "ticket": None, "error": "Тикет не найден", "agent": agent},
            status_code=404,
        )

    # === 2. Сообщения ===
    message_service = MessageService(db)
    messages = message_service.list(
        filters={"ticket_id": ticket.id},
        sort_by="created_at",
        sort_desc=False,
        limit=500,
    )

    # === 3. Вложения ===
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
    .order_by(TicketEvent.occurred_at.asc())  # или .desc() для новых сверху
    .limit(200)
    .all()
)

    # === 5. Справочники для форм И для отображения ===
    status_service = TicketStatusService(db)
    category_service = QuestionCategoryService(db)
    agent_service = AgentService(db)
    
    statuses = status_service.list(sort_by="sort_order", limit=200)
    categories = category_service.list(filters={"is_active": True}, sort_by="sort_order", limit=200)
    agents = agent_service.list(filters={"is_active": True}, sort_by="full_name", limit=500)
    
    from app.models.ticket import Priority
    priorities = list(Priority)

    # === 🔑 КЛЮЧЕВОЕ: словари для безопасного доступа в шаблоне ===
    status_name_by_id = {s.id: s.name for s in statuses}
    category_name_by_id = {c.id: c.name for c in categories}
    agent_name_by_id = {a.id: a.full_name for a in agents}

    # === 6. Рендер ===
    return templates.TemplateResponse(
        "tickets/detail.html",
        {
            "request": request,
            "ticket": ticket,
            "messages": messages,
            "events": events,
            "attachments_by_message": attachments_by_message,
            "agent": agent,
            
            # Для форм:
            "statuses": statuses,
            "priorities": priorities,
            "categories": categories,
            "agents": agents,
            
            # 🔑 Для отображения (защита от UndefinedError):
            "status_name_by_id": status_name_by_id,
            "category_name_by_id": category_name_by_id,
            "agent_name_by_id": agent_name_by_id,
            
            "error": None,
        },
    )


@router.post("/tickets/{ticket_id}/reply", response_class=RedirectResponse)
async def admin_reply(
    ticket_id: int,
    request: Request,
    agent: CurrentAgent,  # ← БЕЗ = Depends(...), если CurrentAgent уже Annotated
    db: Session = Depends(get_db),
    body: str = Form(...),
    is_internal: str = Form("false"),
    attachments: list[UploadFile] = File(default=[]),
):
    is_internal_bool = is_internal.lower() in ("true", "on", "1", "yes")
    
    ticket_service = TicketService(db, ticket_event_service=TicketEventService(db))
    try:
        ticket = ticket_service.get(ticket_id=ticket_id)
    except NotFound:
        raise HTTPException(status_code=404, detail="Тикет не найден")

    from app.schemas.message import MessageCreate
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

    # Вложения
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

    # Email-уведомление (только если не внутренняя заметка)
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
    agent: CurrentAgent,  # ← БЕЗ = Depends(...)
    db: Session = Depends(get_db),
    status_id: str = Form(""),
    priority: str = Form(""),
    owner_id: str = Form(""),
    category_id: str = Form(""),
    is_locked: str = Form("false"),
    is_archived: str = Form("false"),
):
    ticket_service = TicketService(db, ticket_event_service=TicketEventService(db))
    update_data = {}
    
    if status_id and status_id.isdigit():
        update_data["status_id"] = int(status_id)
    
    if priority:
        try:
            from app.models.ticket import Priority
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
        except NotFound:
            raise HTTPException(status_code=404, detail="Тикет не найден")
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Ошибка обновления: {str(e)}")
    
    return RedirectResponse(url=f"/tickets/{ticket_id}", status_code=303)

from app.core.auth import get_current_agent 
@router.post("/tickets/{ticket_id}/delete")
async def delete_ticket(
    request: Request,
    ticket_id: int,
    db: Session = Depends(get_db),
    current_user: AgentRead = Depends(get_current_agent),
):
    #if not getattr(current_user, "is_admin", False):
    #    raise HTTPException(status_code=403, detail="Недостаточно прав")

    ticket_service = TicketService(db)
    result = ticket_service.delete_ticket(  # result — это DeleteResponse
        ticket_id=ticket_id,
        agent_id=current_user.id,
    )

    # ПРАВИЛЬНАЯ ПРОВЕРКА: обращаемся к полю .success
    if not result.success:
        raise HTTPException(status_code=404, detail=result.detail or "Тикет не найден")

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

    return FileResponse(
        path=path,
        filename=att.original_filename,
        media_type=att.mime_type,
    )


from fastapi import APIRouter, Depends, Form, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session


from app.core.security import hash_password, verify_password
from app.core.permissions import Permission, PERMISSION_LABELS
from app.schemas.agent import AgentCreate, AgentUpdate
from app.services.agent_service import AgentService
from app.services.department_service import DepartmentService




def _agent_filters(request: Request) -> dict | None:
    """Извлечение фильтров из query-параметров"""
    filters = {}
    if search := request.query_params.get("search"):
        filters["full_name"] = search
    if role := request.query_params.get("role"):
        filters["role"] = role
    if dept := request.query_params.get("department_id"):
        filters["department_id"] = int(dept)
    return filters if filters else None





@router.get("/agents", response_class=HTMLResponse)
def agents_list(
    request: Request,
    agent: CurrentAgent,
    db: Session = Depends(get_db),
    sort_by: str = Query("id"),
    sort_desc: bool = Query(False),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    agent_service = AgentService(db)
    filters = _agent_filters(request)
    
    agents = agent_service.list(
        filters=filters if filters else None,
        sort_by=sort_by,
        sort_desc=sort_desc,
        limit=limit,
        offset=offset,
    )
    
    # Для пагинации
    total = agent_service.list(filters=filters, limit=999999) if filters else agent_service.list(limit=999999)
    
    return templates.TemplateResponse(
        "agents/list.html",
        {
            "request": request,
            "agents": agents,
            "agent": agent,  # текущий авторизованный агент
            "total_count": len(total),
            "sort_by": sort_by,
            "sort_desc": sort_desc,
            "search_query": request.query_params.get("search", ""),
            "offset": offset,
            "limit": limit,
        },
    )





@router.get("/agents/add", response_class=HTMLResponse)
def add_agent_form(
    request: Request,
    agent: CurrentAgent,
    db: Session = Depends(get_db),
):
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
            "departments": departments,
            "error": None,
            "permissions_list": list(Permission),
            "permission_labels": PERMISSION_LABELS,
            "form_data": None,
        },
    )


@router.post("/agents/add", response_class=HTMLResponse)
def add_agent_submit(
    request: Request,
    agent: CurrentAgent,
    db: Session = Depends(get_db),
    full_name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    role: str = Form(...),
    department_id: int = Form(...),
    category_access: list[str] = Form(default=[]),
    permissions: list[str] = Form(default=[]),
    phone: str | None = Form(None),
):
    agent_service = AgentService(db)
    
    try:
        # 👉 Админ получает все права автоматически
        if role == "admin":
            category_access_str = ""
            permissions_str = ""
        else:
            category_access_str = ",".join(category_access)
            permissions_str = ",".join(permissions)

        agent_data = AgentCreate(
            full_name=full_name.strip(),
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
        return RedirectResponse(url="/agents", status_code=303)
    
    except Exception as e:
        dept_service = DepartmentService(db)
        return templates.TemplateResponse(
            "agents/add.html",
            {
                "request": request,
                "agent": agent,
                "error": str(e),
                "permissions_list": list(Permission),
                "permission_labels": PERMISSION_LABELS,
                "form_data": {
                    "full_name": full_name,
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
    
@router.get("/agents/{agent_id}/edit", response_class=HTMLResponse)
def edit_agent_form(
    request: Request,
    agent: CurrentAgent,
    agent_id: int,
    db: Session = Depends(get_db),
):
    agent_service = AgentService(db)
    dept_service = DepartmentService(db)
    
    # Получаем агента для редактирования
    target_agent = agent_service.get(agent_id=agent_id)
    
    departments = dept_service.list(
        filters={"is_active": True},
        sort_by="name",
        limit=200,
    )
    
    # Парсим строки с правами обратно в списки для чекбоксов
    selected_categories = target_agent.category_access.split(",") if target_agent.category_access else []
    selected_permissions = target_agent.permissions.split(",") if target_agent.permissions else []
    
    return templates.TemplateResponse(
        "agents/edit.html",
        {
            "request": request,
            "agent": agent,  # текущий авторизованный
            "target_agent": target_agent,
            "departments": departments,
            "error": None,
            "permissions_list": list(Permission),
            "permission_labels": PERMISSION_LABELS,
            "selected_categories": selected_categories,
            "selected_permissions": selected_permissions,
        },
    )


@router.post("/agents/{agent_id}/edit", response_class=HTMLResponse)
def edit_agent_submit(
    request: Request,
    agent: CurrentAgent,
    agent_id: int,
    db: Session = Depends(get_db),
    full_name: str = Form(...),
    email: str = Form(...),
    password: str = Form(None),  # необязательно при редактировании
    role: str = Form(...),
    department_id: int = Form(...),
    category_access: list[str] = Form(default=[]),
    permissions: list[str] = Form(default=[]),
    phone: str | None = Form(None),
    is_active: bool = Form(False),
):
    agent_service = AgentService(db)
    
    try:
        # 👉 Админ — игнорируем чекбоксы
        if role == "admin":
            category_access_str = ""
            permissions_str = ""
        else:
            category_access_str = ",".join(category_access)
            permissions_str = ",".join(permissions)

        update_data = {
            "full_name": full_name.strip(),
            "email": email.strip().lower(),
            "role": role,
            "department_id": department_id,
            "category_access": category_access_str,
            "permissions": permissions_str,
            "phone": phone.strip() if phone else None,
            "is_active": is_active,
        }
        
        # Пароль обновляем только если указан
        if password and password.strip():
            update_data["password_hash"] = hash_password(password)

        agent_service.update(
            agent_id=agent_id,
            agent_data=AgentUpdate(**update_data),
        )
        
        return RedirectResponse(url="/agents", status_code=303)
    
    except Exception as e:
        # Возвращаем форму с ошибкой
        dept_service = DepartmentService(db)
        target_agent = agent_service.get(agent_id=agent_id)
        
        return templates.TemplateResponse(
            "agents/edit.html",
            {
                "request": request,
                "agent": agent,
                "target_agent": target_agent,
                "departments": dept_service.list(filters={"is_active": True}, sort_by="name", limit=200),
                "error": str(e),
                "permissions_list": list(Permission),
                "permission_labels": PERMISSION_LABELS,
                "selected_categories": category_access,
                "selected_permissions": permissions,
            },
            status_code=400,
        )


# ─────────────────────────────────────────────────────────────
# 🗑️ Удаление агента
# ─────────────────────────────────────────────────────────────
@router.post("/agents/{agent_id}/delete", response_class=HTMLResponse)
def delete_agent(
    request: Request,
    agent: CurrentAgent,  # проверяем права через зависимость
    agent_id: int,
    db: Session = Depends(get_db),
):
    # 🔐 Защита: нельзя удалить самого себя
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







@router.get("/departments", response_class=HTMLResponse)
def departments_list(
    request: Request,
    agent: CurrentAgent,
    db: Session = Depends(get_db),
    sort_by: str = Query("id"),
    sort_desc: bool = Query(False),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    department_service = DepartmentService(db)
    filters = _department_filters(request)
    departments = department_service.list(
        filters=filters if filters else None,
        sort_by=sort_by,
        sort_desc=sort_desc,
        limit=limit,
        offset=offset,
    )
    return templates.TemplateResponse(
        "departments/list.html",
        {"request": request, "departments": departments, "agent": agent},
    )


@router.get("/department", response_class=RedirectResponse)
def departments_alias(agent: CurrentAgent):
    return RedirectResponse(url="/departments", status_code=303)


@router.get("/question-category-list", response_class=HTMLResponse)
def question_category_list(
    request: Request,
    agent: CurrentAgent,
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
        "question_categories/list.html",
        {"request": request, "agent": agent, "categories": items},
    )


@router.get("/question-category-add", response_class=HTMLResponse)
def question_category_add(request: Request, agent: CurrentAgent):
    return templates.TemplateResponse(
        "question_categories/add.html",
        {"request": request, "agent": agent},
    )


@router.get("/question-category-change", response_class=HTMLResponse)
def question_category_change(request: Request, agent: CurrentAgent):
    return templates.TemplateResponse(
        "question_categories/change.html",
        {"request": request, "agent": agent},
    )


@router.get("/lookups/languages", response_class=HTMLResponse)
def languages_list(
    request: Request,
    agent: CurrentAgent,
    db: Session = Depends(get_db),
    sort_by: str = Query("sort_order"),
    sort_desc: bool = Query(False),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    language_service = LanguageService(db)
    filters = _language_filters(request)
    languages = language_service.list(
        filters=filters if filters else None,
        sort_by=sort_by,
        sort_desc=sort_desc,
        limit=limit,
        offset=offset,
    )
    return templates.TemplateResponse(
        "lookups/languages.html",
        {"request": request, "languages": languages, "agent": agent},
    )
