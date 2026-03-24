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
from fastapi.templating import Jinja2Templates

router = APIRouter(prefix="", tags=["jinja"])

templates_dir = Path(__file__).resolve().parent / "templates"
templates = Jinja2Templates(directory=str(templates_dir))


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
            },
            status_code=404,
        )

    return RedirectResponse(url=f"/tickets/{ticket.id}", status_code=303)


@router.get("/ticket/{track_id}/messege", response_class=HTMLResponse)
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
    email: str = Form(...),
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

    if email.strip().lower() != (ticket.customer_email or "").strip().lower():
        raise HTTPException(status_code=403, detail="Неверный email для данного тикета")

    from app.schemas.message import MessageCreate

    message_service = MessageService(db, ticket_event_service=TicketEventService(db))
    message_data = MessageCreate(
        ticket_id=ticket.id,
        agent_id=None,
        customer_name=ticket.customer_name,
        customer_email=ticket.customer_email,
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
    sort_by: str = Query("id", description="Sort field"),
    sort_desc: bool = Query(False, description="Sort descending"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    ticket_service = TicketService(db)
    filters = _ticket_filters(request)
    tickets = ticket_service.list(
        filters=filters if filters else None,
        sort_by=sort_by,
        sort_desc=sort_desc,
        limit=limit,
        offset=offset,
    )
    return templates.TemplateResponse(
        "tickets/list.html",
        {"request": request, "tickets": tickets, "agent": agent},
    )


@router.get("/list-tickets", response_class=RedirectResponse)
def list_tickets_alias(agent: CurrentAgent):
    return RedirectResponse(url="/tickets", status_code=303)


@router.get("/tickets/{ticket_id}", response_class=HTMLResponse)
def tickets_detail(
    request: Request,
    ticket_id: int,
    agent: CurrentAgent,
    db: Session = Depends(get_db),
):
    ticket_service = TicketService(db)
    message_service = MessageService(db)
    event_service = TicketEventService(db)
    attachment_service = AttachmentService(db)

    try:
        ticket = ticket_service.get(ticket_id=ticket_id)
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
            },
            status_code=404,
        )

    messages = message_service.list(
        filters={"ticket_id": ticket_id},
        sort_by="created_at",
        sort_desc=False,
        limit=200,
    )
    events = event_service.list_by_ticket(
        ticket_id=ticket_id,
        sort_by="occurred_at",
        sort_desc=True,
        limit=100,
    )
    attachments_by_message: dict[int, list] = {}
    for msg in messages:
        atts = attachment_service.list(
            filters={"message_id": msg.id},
            sort_by="id",
            limit=50,
        )
        attachments_by_message[msg.id] = atts

    return templates.TemplateResponse(
        "tickets/detail.html",
        {
            "request": request,
            "ticket": ticket,
            "messages": messages,
            "events": events,
            "attachments_by_message": attachments_by_message,
            "agent": agent,
        },
    )


@router.post("/tickets/{ticket_id}/reply", response_class=RedirectResponse)
async def ticket_reply(
    ticket_id: int,
    agent: CurrentAgent,
    db: Session = Depends(get_db),
    body: str = Form(...),
    attachments: list[UploadFile] = File(default=[]),
):
    """Добавить ответ к тикету (с вложениями)."""
    from app.models.ticket import Ticket as TicketModel
    from app.schemas.message import MessageCreate

    ticket = db.query(TicketModel).filter(TicketModel.id == ticket_id).one_or_none()
    if not ticket:
        raise HTTPException(status_code=404, detail="Тикет не найден")

    message_service = MessageService(db, ticket_event_service=TicketEventService(db))
    attachment_service = AttachmentService(db, ticket_event_service=TicketEventService(db))
    message_data = MessageCreate(
        ticket_id=ticket_id,
        agent_id=agent.id,
        body=body.strip(),
        subject=ticket.subject,
        customer_name=ticket.customer_name,
        customer_email=ticket.customer_email,
    )
    message = message_service.add_message(message_data=message_data, agent_id=agent.id)

    if attachments:
        file_storage = FileStorageService()
        files_meta = []
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
                uploaded_by_agent_id=agent.id,
                files=files_meta,
            )

        # Уведомление назначенному оператору (не самому себе) или департаменту
        from app.models.department import Department
        from app.services.email_service import notify_new_message
        to_email = None
        from_name = agent.full_name
        if ticket.owner_id and ticket.owner_id != agent.id:
            owner_agent = db.query(Agent).filter(Agent.id == ticket.owner_id).one_or_none()
            if owner_agent and owner_agent.email:
                to_email = owner_agent.email
        if not to_email and ticket.department_id:
            dept = db.query(Department).filter(Department.id == ticket.department_id).one_or_none()
            if dept and dept.email:
                to_email = dept.email
        if to_email:
            try:
                notify_new_message(
                    to_email=to_email,
                    track_id=ticket.track_id,
                    subject=ticket.subject,
                    message_preview=body.strip(),
                    from_name=from_name,
                )
            except Exception:
                pass

    return RedirectResponse(url=f"/tickets/{ticket_id}", status_code=303)


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
    return templates.TemplateResponse(
        "agents/list.html",
        {"request": request, "agents": agents, "agent": agent},
    )


@router.get("/list-users", response_class=RedirectResponse)
def list_users_alias(agent: CurrentAgent):
    return RedirectResponse(url="/agents", status_code=303)


@router.get("/add-user", response_class=HTMLResponse)
def add_user_form(request: Request, agent: CurrentAgent):
    return templates.TemplateResponse(
        "users/add.html",
        {"request": request, "agent": agent, "error": None},
    )


@router.get("/change-user", response_class=HTMLResponse)
def change_user_form(request: Request, agent: CurrentAgent):
    return templates.TemplateResponse(
        "users/change.html",
        {"request": request, "agent": agent, "error": None},
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
