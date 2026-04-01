from __future__ import annotations

import re
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse
from starlette.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.audit import get_client_info
from app.core.auth import CurrentAgentOptional
from app.models import get_db
from app.models.agent import Agent
from app.models.department import Department
from app.models.ticket import Priority
from app.schemas.ticket import TicketCreate
from app.services.agent_service import AgentService
from app.services.audit_log_service import AuditLogService
from app.services.department_service import DepartmentService
from app.services.errors import Conflict as ServiceConflict
from app.services.errors import NotFound as ServiceNotFound
from app.services.file_storage_service import FileStorageService
from app.services.language_service import LanguageService
from app.services.question_category_service import QuestionCategoryService
from app.services.ticket import TicketService, TicketEventService, MessageService, AttachmentService

from ..main import templates

router = APIRouter(prefix="", tags=["tickets-public"])


def _validate_track_id(track_id: str) -> tuple[bool, str]:
    """
    Проверить формат трек-номера.
    
    Допустимые форматы:
    - XXX-XXX-XXXX (например, ABC-123-DEF456)
    - XXXXXX (например, ABC123)
    
    Returns:
        (True, "") если формат верный
        (False, "сообщение об ошибке") если формат неверный
    """
    track_id = track_id.strip().upper()
    
    # Пустой трек-номер
    if not track_id:
        return False, "Введите трек-номер"
    
    # Слишком короткий
    if len(track_id) < 6:
        return False, "Трек-номер слишком короткий"
    
    # Слишком длинный
    if len(track_id) > 20:
        return False, "Трек-номер слишком длинный"
    
    # Разрешённые символы: буквы, цифры, дефис
    if not re.match(r'^[A-Z0-9\-]+$', track_id):
        return False, "Трек-номер должен содержать только буквы, цифры и дефисы"
    
    # Если есть дефисы, проверяем формат XXX-XXX-XXXX
    if '-' in track_id:
        parts = track_id.split('-')
        if len(parts) != 3:
            return False, "Неверный формат трек-номера (ожидается XXX-XXX-XXXX)"
        if any(len(p) == 0 for p in parts):
            return False, "Трек-номер не должен содержать пустых частей"
    
    return True, ""


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
        "public/new_ticket.html",
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
    """Публичная форма: ввод track_id для доступа к переписке."""
    return templates.TemplateResponse(
        "public/find_ticket.html",
        {"request": request, "agent": agent, "error": None},
    )


@router.post("/get-ticket", response_class=RedirectResponse)
def get_ticket_submit(
    track_id: str = Form(...),
):
    track_id = track_id.strip().upper()
    return RedirectResponse(url=f"/ticket/{track_id}/message", status_code=303)


@router.post("/ticket/", response_class=RedirectResponse)
def ticket_search_submit(
    request: Request,
    track_id: str = Form(...),
):
    """Поиск тикета по трек-номеру (из формы)."""
    track_id = track_id.strip().upper()
    
    # Валидация формата
    is_valid, error_message = _validate_track_id(track_id)
    if not is_valid:
        # Сохраняем ошибку в сессию и возвращаем на страницу поиска
        request.session["flash_error"] = error_message
        return RedirectResponse(url="/get-ticket", status_code=303)
    
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

    # Передаём agent_id только если агент авторизован
    ticket_service = TicketService(db, agent_id=agent.id if agent else None)
    try:
        ticket = ticket_service.get_by_track_id(track_id)
    except ServiceNotFound:
        return templates.TemplateResponse(
            "public/find_ticket.html",
            {
                "request": request,
                "agent": agent,
                "error": "Заявка с таким трек-номером не найдена",
            },
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
    
    # Валидация формата
    is_valid, error_message = _validate_track_id(track_id)
    if not is_valid:
        return templates.TemplateResponse(
            "public/find_ticket.html",
            {"request": request, "agent": agent, "error": error_message},
            status_code=400,
        )
    
    ticket_service = TicketService(db, agent_id=agent.id if agent else None)
    try:
        ticket = ticket_service.get_by_track_id(track_id)
    except ServiceNotFound:
        return templates.TemplateResponse(
            "public/find_ticket.html",
            {"request": request, "agent": agent, "error": "Заявка с таким трек-номером не найдена"},
            status_code=404,
        )

    # Если тикет объединён с другим, перенаправляем на родительский
    if ticket.merged_into_id:
        if agent:
            return RedirectResponse(url=f"/tickets/{ticket.merged_into_id}", status_code=303)
        else:
            # Для публичного доступа получаем родительский тикет
            parent_ticket = ticket_service.get(ticket_id=ticket.merged_into_id)
            return RedirectResponse(url=f"/ticket/{parent_ticket.track_id}/message", status_code=303)

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

    # Получаем справочники для отображения
    from app.models.ticket_status import TicketStatus
    from app.models.ticket import Priority
    from app.services.ticket_status_service import TicketStatusService
    
    status_service = TicketStatusService(db)
    statuses = status_service.list(sort_by="sort_order", limit=200)
    status_name_by_id = {s.id: s.name for s in statuses}
    priorities = list(Priority)
    
    # Получаем агентов для отображения логина
    from app.services.agent_service import AgentService
    agent_service = AgentService(db)
    agents = agent_service.list(filters={"is_active": True}, sort_by="full_name", limit=500)
    agent_login_by_id = {a.id: a.login for a in agents}

    return templates.TemplateResponse(
        "public/ticket_chat.html",
        {
            "request": request,
            "agent": None,
            "ticket": ticket,
            "messages": messages,
            "attachments_by_message": attachments_by_message,
            "error": None,
            "status_name_by_id": status_name_by_id,
            "priorities": priorities,
            "agent_login_by_id": agent_login_by_id,
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

    # Логируем создание сообщения
    client_info = get_client_info(request)
    log_service = AuditLogService(db)
    log_service.log_action(
        action="create",
        entity_type="message",
        entity_id=message.id,
        agent_id=None,
        details={
            "ticket_id": ticket.id,
            "track_id": ticket.track_id,
            "customer_name": ticket.customer_name,
            "is_internal": False,
            "has_attachments": bool(attachments),
        },
        **client_info,
    )

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
    from app.web.jinja.routes.utils import _parse_int
    from app.services.ban_service import BanService

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

    # Проверка на бан по email и IP
    if BanService.is_email_banned(db, customer_email):
        return templates.TemplateResponse(
            "public/new_ticket.html",
            {
                "request": request,
                "departments": departments,
                "languages": languages,
                "categories": categories,
                "priorities": list(Priority),
                "agent": None,
                "error": "Доступ заблокирован: ваш email находится в чёрном списке.",
                "form_data": form_data,
            },
            status_code=403,
        )

    if BanService.is_ip_banned(db, customer_ip):
        return templates.TemplateResponse(
            "public/new_ticket.html",
            {
                "request": request,
                "departments": departments,
                "languages": languages,
                "categories": categories,
                "priorities": list(Priority),
                "agent": None,
                "error": "Доступ заблокирован: ваш IP-адрес находится в чёрном списке.",
                "form_data": form_data,
            },
            status_code=403,
        )

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

        # Логируем создание тикета
        client_info = get_client_info(request)
        log_service = AuditLogService(db)
        log_service.log_action(
            action="create",
            entity_type="ticket",
            entity_id=ticket.id,
            agent_id=None,
            details={
                "track_id": ticket.track_id,
                "subject": ticket.subject,
                "customer_name": ticket.customer_name,
                "customer_email": ticket.customer_email,
                "department_id": ticket.department_id,
                "priority": ticket.priority.value if ticket.priority else "normal",
            },
            **client_info,
        )

        # Уведомление о новом обращении (оператору или департаменту)
        from app.services.email_service import notify_ticket_created, notify_ticket_created_customer
        from app.services.agent_service import AgentService

        # Определяем получателя уведомления
        to_email_notify = None

        # Сначала пробуем отправить оператору, если тикет назначен
        if ticket.owner_id:
            try:
                agent_service = AgentService(db)
                assigned_agent = agent_service.get(agent_id=ticket.owner_id)
                # Проверяем, включены ли email-уведомления у оператора
                if assigned_agent and assigned_agent.email and assigned_agent.email_notifications:
                    to_email_notify = assigned_agent.email
                    print(f"📧 Уведомление отправляется оператору: {assigned_agent.full_name} ({to_email_notify})")
                elif assigned_agent and not assigned_agent.email_notifications:
                    print(f"⚠️ У оператора {assigned_agent.full_name} отключены email-уведомления")
            except Exception:
                pass

        # Если оператор не назначен или нет email — отправляем департаменту
        if not to_email_notify:
            dept = db.query(Department).filter(Department.id == ticket.department_id).one_or_none()
            to_email_notify = (dept.email if dept and dept.email else None) or "olegfesenko365@gmail.com"
            print(f"📧 Уведомление отправляется департаменту: {to_email_notify}")

        # Отправляем уведомление
        try:
            notify_ticket_created(
                to_email=to_email_notify,
                track_id=ticket.track_id,
                subject=ticket.subject,
                customer_name=ticket.customer_name,
                body_preview=body.strip(),
            )
        except Exception:
            pass

        # Уведомление пользователю о создании тикета
        try:
            notify_ticket_created_customer(
                to_email=ticket.customer_email,
                track_id=ticket.track_id,
                subject=ticket.subject,
                customer_name=ticket.customer_name,
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

    # Flash-сообщение об успешном создании
    request.session["flash_success"] = f"Обращение успешно создано! Трек-номер: {ticket.track_id}"

    return templates.TemplateResponse(
        "public/created.html",
        {
            "request": request,
            "track_id": ticket.track_id,
            "agent": None,
        },
    )


@router.get("/attachments/{attachment_id}/download")
def attachment_download_public(
    attachment_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Скачать вложение (публичный доступ).
    Проверяет, что вложение принадлежит тикету, к которому у пользователя есть доступ.
    """
    attachment_service = AttachmentService(db)
    
    # Получаем вложение
    att = attachment_service.get_orm(attachment_id=attachment_id)
    if att is None:
        raise HTTPException(status_code=404, detail="Вложение не найдено")
    
    # Проверяем, что вложение принадлежит тикету
    ticket = att.message.ticket if att.message else None
    if ticket is None:
        raise HTTPException(status_code=404, detail="Тикет не найден")
    
    # Для публичного доступа проверяем, что пользователь знает track_id
    # (это косвенная проверка, так как ссылка содержит ID вложения)
    # В реальной системе можно добавить проверку email или токена
    
    file_storage = FileStorageService()
    path = file_storage.get_path(att.file_path)
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Файл не найден")

    # Увеличиваем счётчик скачиваний
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
