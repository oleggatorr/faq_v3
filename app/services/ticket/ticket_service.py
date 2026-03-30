from __future__ import annotations

import random
import string
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.models.message import Message
from app.models.ticket import Ticket
from app.models.ticket_status import TicketStatus
from app.models.ticket_event import EventType, TicketEvent
from app.schemas.deletion import DeleteResponse
from app.schemas.ticket import TicketCreate, TicketRead, TicketUpdate
from app.services.errors import Conflict, NotFound, ValidationFailed
from app.services.ticket.ticket_event_service import TicketEventService
from app.services.ticket.ticket_base_service import TicketBaseService
from app.services.ticket.read_state_service import TicketReadStateService
from app.services.utils import apply_filters, apply_sort, format_preview
from app.core.permissions import Permission


class TicketService(TicketBaseService):
    """
    Ticket domain operations.

    Contract recap (based on `docs/06-services/index.md`):
    - `create_ticket_with_first_message`: create a ticket + first customer message
    in one workflow, including `preview_message` computed from the first body.
    """

    def __init__(
        self,
        session: Session,
        *,
        ticket_event_service: TicketEventService | None = None,
        ticket_read_state_service: TicketReadStateService | None = None,
        agent_id: int | None = None,
    ):
        super().__init__(session, agent_id=agent_id)
        self.ticket_event_service = ticket_event_service
        self.ticket_read_state_service = ticket_read_state_service

    def _get_by_track_id(self, track_id: str) -> Optional[Ticket]:
        return (
            self.session.query(Ticket)
            .filter(Ticket.track_id == track_id)
            .one_or_none()
        )

    def generate_track_id(self, max_attempts: int = 10) -> str:
        """
        Генерирует уникальный track_id. Формат: XXX-XXX-XXXX
        (заглавная латиница или цифра).
        """
        chars = string.ascii_uppercase + string.digits

        def _rand_part(n: int) -> str:
            return "".join(random.choices(chars, k=n))

        for _ in range(max_attempts):
            track_id = f"{_rand_part(3)}-{_rand_part(3)}-{_rand_part(4)}"
            if self._get_by_track_id(track_id) is None:
                return track_id
        raise Conflict("Не удалось сгенерировать уникальный track_id")

    def create_ticket_with_first_message(
        self,
        *,
        ticket_data: TicketCreate,
        first_message_body: str,
        commit: bool = True,
    ) -> tuple[Ticket, Message]:
        """
        Create `Ticket` and immediately create the first `Message`.

        preview rules:
        - if len(body) <= 200 -> preview = body
        - else preview = body[:200] + "..."
        """

        existing = self._get_by_track_id(ticket_data.track_id)
        if existing is not None:
            raise Conflict("track_id already exists")

        preview = format_preview(first_message_body, 200)

        # 1) create ticket
        ticket = Ticket(
            track_id=ticket_data.track_id,
            customer_name=ticket_data.customer_name,
            customer_email=ticket_data.customer_email,
            customer_ip=ticket_data.customer_ip,
            department_id=ticket_data.department_id,
            language_id=ticket_data.language_id,
            category_id=ticket_data.category_id,
            status_id=ticket_data.status_id,
            priority=ticket_data.priority,
            subject=ticket_data.subject,
            preview_message=preview,
            owner_id=ticket_data.owner_id,
            opened_by_id=ticket_data.opened_by_id,
            first_responded_at=ticket_data.first_responded_at,
            closed_at=ticket_data.closed_at,
            closed_by_id=ticket_data.closed_by_id,
            is_archived=ticket_data.is_archived,
            is_locked=ticket_data.is_locked,
            merged_into_id=ticket_data.merged_into_id,
            messages_count=1,
            attachments_count=ticket_data.attachments_count,
        )

        self.session.add(ticket)
        self.session.flush()  # populate ticket.id

        # 2) create first message
        message = Message(
            ticket_id=ticket.id,
            agent_id=None,
            sender_name=ticket.customer_name,  # ФИО отправителя = имя клиента
            customer_name=ticket.customer_name,
            customer_email=ticket.customer_email,
            subject=ticket.subject,
            body=first_message_body,
            is_internal=False,
            is_automatic=False,
            ip_address=ticket.customer_ip,
        )
        self.session.add(message)

        # 3) optionally create audit event
        if self.ticket_event_service is not None:
            self.ticket_event_service.add_event(
                ticket_id=ticket.id,
                agent_id=ticket_data.opened_by_id,
                action_type=EventType.created,
                field_name=None,
                old_value=None,
                new_value=None,
                comment=None,
            )

        if commit:
            self.session.commit()
        else:
            self.session.flush()

        return ticket, message

    # --- Other operations (interfaces for future implementation) ---

    def get_by_track_id(self, track_id: str) -> TicketRead:
        ticket = self._get_by_track_id(track_id)
        if ticket is None:
            raise NotFound("Ticket not found")
        return TicketRead.model_validate(ticket)

    def get(self, *, ticket_id: int) -> TicketRead:
        # Проверка права на просмотр тикетов
        self._check_permission(Permission.can_view_tickets)
        
        ticket = self.session.query(Ticket).filter(Ticket.id == ticket_id).one_or_none()
        if ticket is None:
            raise NotFound("Ticket not found")
        return TicketRead.model_validate(ticket)

    def list(
        self,
        *,
        filters: dict[str, Any] | None = None,
        sort_by: str = "id",
        sort_desc: bool = False,
        limit: int = 100,
        offset: int = 0,
        include_unread: bool = False,
        agent_id: int | None = None,
    ) -> list[TicketRead]:
        # Проверка права выполняется на уровне роута (check_can_view_*)
        # Здесь просто фильтрация и выборка

        allowed_filters = {
            "id",
            "track_id",
            "customer_name",
            "customer_email",
            "department_id",
            "language_id",
            "category_id",
            "status_id",
            "priority",
            "subject",
            "owner_id",
            "opened_by_id",
            "is_archived",
            "is_locked",
            "merged_into_id",
            "messages_count",
            "attachments_count",
        }
        allowed_sort = {
            "id",
            "track_id",
            "created_at",
            "updated_at",
            "status_id",
            "priority",
            "is_archived",
            "is_locked",
            "messages_count",
            "attachments_count",
        }

        if filters:
            unknown = set(filters.keys()) - allowed_filters
            if unknown:
                raise ValueError(f"Unknown filter fields: {', '.join(sorted(unknown))}")

        query = self.session.query(Ticket)
        query = apply_filters(
            query,
            Ticket,
            filters=filters,
            text_like_fields={"track_id", "customer_name", "customer_email", "subject"},
        )
        query = apply_sort(
            query,
            Ticket,
            sort_by=sort_by,
            sort_desc=sort_desc,
            allowed_sort_fields=allowed_sort,
        )
        tickets = query.offset(offset).limit(limit).all()
        
        # Если нужно включить unread_count, получаем его для каждого тикета
        ticket_read_list = []
        if include_unread and agent_id is not None:
            for ticket in tickets:
                ticket_dict = ticket.__dict__.copy()
                if '_sa_instance_state' in ticket_dict:
                    del ticket_dict['_sa_instance_state']
                
                # Считаем непрочитанные сообщения
                unread_count = self.get_unread_count(ticket_id=ticket.id)
                ticket_read = TicketRead(**ticket_dict, unread_count=unread_count)
                ticket_read_list.append(ticket_read)
            return ticket_read_list
        
        return [TicketRead.model_validate(t) for t in tickets]

    def create_ticket(
        self,
        *,
        ticket_data: TicketCreate,
        commit: bool = True,
    ) -> Ticket:
        existing = self._get_by_track_id(ticket_data.track_id)
        if existing is not None:
            raise Conflict("track_id already exists")

        ticket = Ticket(
            track_id=ticket_data.track_id,
            customer_name=ticket_data.customer_name,
            customer_email=ticket_data.customer_email,
            customer_ip=ticket_data.customer_ip,
            department_id=ticket_data.department_id,
            language_id=ticket_data.language_id,
            category_id=ticket_data.category_id,
            status_id=ticket_data.status_id,
            priority=ticket_data.priority,
            subject=ticket_data.subject,
            preview_message=ticket_data.preview_message,
            owner_id=ticket_data.owner_id,
            opened_by_id=ticket_data.opened_by_id,
            first_responded_at=ticket_data.first_responded_at,
            closed_at=ticket_data.closed_at,
            closed_by_id=ticket_data.closed_by_id,
            is_archived=ticket_data.is_archived,
            is_locked=ticket_data.is_locked,
            merged_into_id=ticket_data.merged_into_id,
            messages_count=ticket_data.messages_count,
            attachments_count=ticket_data.attachments_count,
        )

        self.session.add(ticket)
        self.session.flush()

        if self.ticket_event_service is not None:
            self.ticket_event_service.add_event(
                ticket_id=ticket.id,
                agent_id=ticket_data.opened_by_id,
                action_type=EventType.created,
                field_name=None,
                old_value=None,
                new_value=None,
                comment=None,
            )

        if commit:
            self.session.commit()
        else:
            self.session.flush()
        return ticket

    def update_ticket(
        self,
        *,
        ticket_id: int,
        ticket_data: TicketUpdate,
        agent_id: int | None,
        commit: bool = True,
    ) -> Ticket:
        # Проверка права на редактирование тикетов
        self._check_permission(Permission.can_edit_tickets)
        
        ticket = self.session.query(Ticket).filter(Ticket.id == ticket_id).one_or_none()
        if ticket is None:
            raise NotFound("Ticket not found")

        updates = ticket_data.model_dump(exclude_none=True)
        if not updates:
            return ticket

        # Keep old values for conditional event creation.
        old_status_id = ticket.status_id
        old_owner_id = ticket.owner_id
        old_category_id = ticket.category_id
        old_priority = ticket.priority
        old_is_locked = ticket.is_locked
        old_is_archived = ticket.is_archived
        old_merged_into_id = ticket.merged_into_id

        # Domain operations: these methods also write ticket_events.
        if "status_id" in updates:
            self.change_status(
                ticket_id=ticket_id,
                new_status_id=updates.pop("status_id"),
                agent_id=agent_id,
                commit=False,
            )
        if "owner_id" in updates:
            self.assign_owner(
                ticket_id=ticket_id,
                new_owner_id=updates.pop("owner_id"),
                agent_id=agent_id,
                commit=False,
            )
        if "category_id" in updates:
            self.change_category(
                ticket_id=ticket_id,
                new_category_id=updates.pop("category_id"),
                agent_id=agent_id,
                commit=False,
            )
        if "is_locked" in updates:
            self.set_locked(
                ticket_id=ticket_id,
                is_locked=updates.pop("is_locked"),
                agent_id=agent_id,
                commit=False,
            )

        # Priority: log if changed.
        if "priority" in updates:
            new_priority = updates.pop("priority")
            if ticket.priority != new_priority and self.ticket_event_service is not None:
                self.ticket_event_service.add_event(
                    ticket_id=ticket.id,
                    agent_id=agent_id,
                    action_type=EventType.priority_changed,
                    field_name="priority",
                    old_value=str(old_priority.value if hasattr(old_priority, "value") else old_priority),
                    new_value=str(new_priority.value if hasattr(new_priority, "value") else new_priority),
                )
            ticket.priority = new_priority

        # Merge: log if changed.
        if "merged_into_id" in updates:
            new_merged_into_id = updates.pop("merged_into_id")
            if ticket.merged_into_id != new_merged_into_id and self.ticket_event_service is not None:
                self.ticket_event_service.add_event(
                    ticket_id=ticket.id,
                    agent_id=agent_id,
                    action_type=EventType.merged,
                    field_name="merged_into_id",
                    old_value=str(old_merged_into_id) if old_merged_into_id is not None else None,
                    new_value=str(new_merged_into_id) if new_merged_into_id is not None else None,
                )
            ticket.merged_into_id = new_merged_into_id

        # Archive: log if transitioning to archived or unarchived.
        if "is_archived" in updates:
            new_is_archived = updates.pop("is_archived")
            if (
                ticket.is_archived != new_is_archived
                and self.ticket_event_service is not None
            ):
                # Определяем тип события в зависимости от направления изменения
                if new_is_archived:
                    action_type = EventType.archived
                else:
                    action_type = EventType.unarchived
                
                self.ticket_event_service.add_event(
                    ticket_id=ticket.id,
                    agent_id=agent_id,
                    action_type=action_type,
                    field_name="is_archived",
                    old_value=str(old_is_archived),
                    new_value=str(new_is_archived),
                )
            ticket.is_archived = new_is_archived

        # Remaining “plain” fields (no extra domain events beyond the above).
        plain_fields = {
            "customer_name",
            "customer_email",
            "customer_ip",
            "language_id",
            "subject",
            "preview_message",
            "first_responded_at",
            "closed_at",
            "closed_by_id",
            "messages_count",
            "attachments_count",
        }
        for key, value in updates.items():
            if key not in plain_fields:
                raise ValidationFailed(f"Unsupported ticket update field: {key}")
            setattr(ticket, key, value)

        if commit:
            self.session.commit()
        else:
            self.session.flush()
        return ticket

    def delete_ticket(
        self,
        *,
        ticket_id: int,
        agent_id: int | None,
        commit: bool = True,
    ) -> DeleteResponse:
        # Проверка права на удаление тикетов
        self._check_permission(Permission.can_del_tickets)
        
        ticket = self.session.query(Ticket).filter(Ticket.id == ticket_id).one_or_none()
        if ticket is None:
            return DeleteResponse(success=False, deleted_id=None, detail="Ticket not found")

        # Soft delete to preserve `ticket_events` for audit.
        if not ticket.is_archived:
            old_is_archived = ticket.is_archived
            ticket.is_archived = True
            if self.ticket_event_service is not None:
                self.ticket_event_service.add_event(
                    ticket_id=ticket.id,
                    agent_id=agent_id,
                    action_type=EventType.archived,
                    field_name="is_archived",
                    old_value=str(old_is_archived),
                    new_value="true",
                    comment="Ticket archived (delete endpoint)",
                )

        if commit:
            self.session.commit()
        else:
            self.session.flush()

        return DeleteResponse(success=True, deleted_id=ticket_id)

    def hard_delete_ticket(
        self,
        *,
        ticket_id: int,
        agent_id: int | None,
        commit: bool = True,
    ) -> DeleteResponse:
        """
        Полное удаление тикета со всеми связанными данными:
        - Сообщения
        - События тикета
        - Сам тикет
        Вложения остаются в системе (но становятся недоступными).
        """
        ticket = self.session.query(Ticket).filter(Ticket.id == ticket_id).one_or_none()
        if ticket is None:
            return DeleteResponse(success=False, deleted_id=None, detail="Ticket not found")

        # Получаем все сообщения тикета
        messages = self.session.query(Message).filter(Message.ticket_id == ticket_id).all()
        message_ids = [m.id for m in messages]

        # Удаляем сообщения (вложения остаются, но становятся недоступными)
        if message_ids:
            self.session.query(Message).filter(Message.id.in_(message_ids)).delete(synchronize_session=False)
        
        # Удаляем события тикета
        self.session.query(TicketEvent).filter(TicketEvent.ticket_id == ticket_id).delete(synchronize_session=False)
        
        # Удаляем сам тикет
        self.session.delete(ticket)

        if commit:
            self.session.commit()
        else:
            self.session.flush()

        return DeleteResponse(success=True, deleted_id=ticket_id)

    def get_unread_count(self, *, ticket_id: int, exclude_internal: bool = True) -> int:
        """
        Получить количество непрочитанных сообщений в тикете.
        """
        if self.ticket_read_state_service is None:
            self.ticket_read_state_service = TicketReadStateService(self.session)
        
        return self.ticket_read_state_service.get_unread_count(
            ticket_id=ticket_id,
            exclude_internal=exclude_internal,
        )

    def mark_as_read(self, *, ticket_id: int) -> None:
        """
        Отметить все сообщения в тикете как прочитанные.
        """
        if self.ticket_read_state_service is None:
            self.ticket_read_state_service = TicketReadStateService(self.session)
        
        self.ticket_read_state_service.mark_as_read(ticket_id=ticket_id)

    def change_status(
        self,
        *,
        ticket_id: int,
        new_status_id: int,
        agent_id: int | None,
        commit: bool = True,
    ) -> Ticket:
        ticket = self.session.query(Ticket).filter(Ticket.id == ticket_id).one_or_none()
        if ticket is None:
            raise NotFound("Ticket not found")

        old_status_id = ticket.status_id
        if old_status_id == new_status_id:
            return ticket

        old_status = (
            self.session.query(TicketStatus)
            .filter(TicketStatus.id == old_status_id)
            .one_or_none()
        )
        new_status = (
            self.session.query(TicketStatus)
            .filter(TicketStatus.id == new_status_id)
            .one_or_none()
        )
        if old_status is None or new_status is None:
            raise NotFound("Ticket status not found")

        old_is_closed = bool(old_status.is_closed)
        new_is_closed = bool(new_status.is_closed)
        now = datetime.now(timezone.utc)

        ticket.status_id = new_status_id
        if new_is_closed:
            ticket.closed_at = now
            ticket.closed_by_id = agent_id
        else:
            ticket.closed_at = None
            ticket.closed_by_id = None

        if self.ticket_event_service is not None:
            self.ticket_event_service.add_event(
                ticket_id=ticket.id,
                agent_id=agent_id,
                action_type=EventType.status_changed,
                field_name="status_id",
                old_value=str(old_status_id),
                new_value=str(new_status_id),
            )

            if not old_is_closed and new_is_closed:
                self.ticket_event_service.add_event(
                    ticket_id=ticket.id,
                    agent_id=agent_id,
                    action_type=EventType.closed,
                    field_name="status_id",
                    old_value=str(old_status_id),
                    new_value=str(new_status_id),
                )
            elif old_is_closed and not new_is_closed:
                self.ticket_event_service.add_event(
                    ticket_id=ticket.id,
                    agent_id=agent_id,
                    action_type=EventType.reopened,
                    field_name="status_id",
                    old_value=str(old_status_id),
                    new_value=str(new_status_id),
                )

        if commit:
            self.session.commit()
        else:
            self.session.flush()

        try:
            from app.services.email_service import notify_status_changed
            notify_status_changed(
                to_email=ticket.customer_email,
                track_id=ticket.track_id,
                subject=ticket.subject,
                new_status=new_status.name,
                customer_name=ticket.customer_name,
            )
        except Exception:
            pass

        return ticket

    def assign_owner(
        self,
        *,
        ticket_id: int,
        new_owner_id: int | None,
        agent_id: int | None,
        commit: bool = True,
    ) -> Ticket:
        ticket = self.session.query(Ticket).filter(Ticket.id == ticket_id).one_or_none()
        if ticket is None:
            raise NotFound("Ticket not found")

        old_owner_id = ticket.owner_id
        if old_owner_id == new_owner_id:
            return ticket

        ticket.owner_id = new_owner_id

        # Сбросить состояние прочтения при смене владельца
        if self.ticket_read_state_service is not None:
            self.ticket_read_state_service.reset_on_reassign(ticket_id=ticket_id)

        if self.ticket_event_service is not None:
            action_type = EventType.assigned if new_owner_id is not None else EventType.unassigned
            self.ticket_event_service.add_event(
                ticket_id=ticket.id,
                agent_id=agent_id,
                action_type=action_type,
                field_name="owner_id",
                old_value=str(old_owner_id) if old_owner_id is not None else None,
                new_value=str(new_owner_id) if new_owner_id is not None else None,
            )

        if commit:
            self.session.commit()
        else:
            self.session.flush()
        return ticket

    def change_category(
        self,
        *,
        ticket_id: int,
        new_category_id: int | None,
        agent_id: int | None,
        commit: bool = True,
    ) -> Ticket:
        ticket = self.session.query(Ticket).filter(Ticket.id == ticket_id).one_or_none()
        if ticket is None:
            raise NotFound("Ticket not found")

        old_category_id = ticket.category_id
        if old_category_id == new_category_id:
            return ticket

        ticket.category_id = new_category_id

        if self.ticket_event_service is not None:
            self.ticket_event_service.add_event(
                ticket_id=ticket.id,
                agent_id=agent_id,
                action_type=EventType.category_changed,
                field_name="category_id",
                old_value=str(old_category_id) if old_category_id is not None else None,
                new_value=str(new_category_id) if new_category_id is not None else None,
            )

        if commit:
            self.session.commit()
        else:
            self.session.flush()
        return ticket

    def merge_tickets(
        self,
        *,
        source_ticket_id: int,
        target_ticket_id: int,
        agent_id: int | None,
        commit: bool = True,
    ) -> Ticket:
        #///В разработке
        if source_ticket_id == target_ticket_id:
            raise Conflict("Cannot merge a ticket into itself")

        source = self.session.query(Ticket).filter(Ticket.id == source_ticket_id).one_or_none()
        target = self.session.query(Ticket).filter(Ticket.id == target_ticket_id).one_or_none()
        if source is None or target is None:
            raise NotFound("Ticket not found")

        old_merged_into_id = source.merged_into_id
        source.merged_into_id = target.id

        if self.ticket_event_service is not None:
            self.ticket_event_service.add_event(
                ticket_id=source.id,
                agent_id=agent_id,
                action_type=EventType.merged,
                field_name="merged_into_id",
                old_value=str(old_merged_into_id) if old_merged_into_id is not None else None,
                new_value=str(target.id),
                comment=f"Merged into ticket_id={target.id}",
            )

        if commit:
            self.session.commit()
        else:
            self.session.flush()

        return source

    def set_locked(
        self,
        *,
        ticket_id: int,
        is_locked: bool,
        agent_id: int | None,
        commit: bool = True,
    ) -> Ticket:
        ticket = self.session.query(Ticket).filter(Ticket.id == ticket_id).one_or_none()
        if ticket is None:
            raise NotFound("Ticket not found")

        old_is_locked = ticket.is_locked
        if old_is_locked == is_locked:
            return ticket

        ticket.is_locked = is_locked

        if self.ticket_event_service is not None:
            self.ticket_event_service.add_event(
                ticket_id=ticket.id,
                agent_id=agent_id,
                action_type=EventType.locked if is_locked else EventType.unlocked,
                field_name="is_locked",
                old_value=str(old_is_locked),
                new_value=str(is_locked),
            )

        if commit:
            self.session.commit()
        else:
            self.session.flush()
        return ticket

    def anonymize_ticket(
        self,
        *,
        ticket_id: int,
        agent_id: int | None,
        commit: bool = True,
    ) -> Ticket:
        ticket = self.session.query(Ticket).filter(Ticket.id == ticket_id).one_or_none()
        if ticket is None:
            raise NotFound("Ticket not found")

        old_name = ticket.customer_name
        old_email = ticket.customer_email
        old_ip = ticket.customer_ip

        # Minimal anonymization preserving non-null constraints.
        ticket.customer_name = "Anonymous"
        ticket.customer_email = "anonymous@example.com"
        ticket.customer_ip = "0.0.0.0"

        if self.ticket_event_service is not None:
            self.ticket_event_service.add_event(
                ticket_id=ticket.id,
                agent_id=agent_id,
                action_type=EventType.anonymized,
                field_name="customer_data",
                old_value=f"name={old_name}; email={old_email}; ip={old_ip}",
                new_value="name=Anonymous; email=anonymous@example.com; ip=0.0.0.0",
                comment="Customer data anonymized",
            )

        if commit:
            self.session.commit()
        else:
            self.session.flush()

        return ticket

