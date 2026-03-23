from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.models.attachment import Attachment
from app.models.message import Message
from app.models.ticket import Ticket
from app.models.ticket_event import EventType
from app.schemas.attachment import AttachmentCreate, AttachmentRead, AttachmentUpdate
from app.schemas.deletion import DeleteResponse

from .errors import NotFound
from .ticket_event_service import TicketEventService
from .utils import apply_filters, apply_sort


class AttachmentService:
    """
    Attachment domain operations.

    File handling responsibilities usually split into:
    - storing binary content (filesystem/object storage)
    - persisting metadata in `attachments`
    - updating counters: `tickets.attachments_count`
    - audit: `TicketEvent` (action_type=attachment_added)
    """

    def __init__(
        self,
        session: Session,
        *,
        ticket_event_service: TicketEventService | None = None,
    ):
        self.session = session
        self.ticket_event_service = ticket_event_service

    def add_attachments(
        self,
        *,
        message: Message,
        uploaded_by_agent_id: int | None,
        files: list[dict],
        commit: bool = True,
    ) -> list[Attachment]:
        """
        Add attachments for a message.

        `files` is a list of metadata dicts, e.g.:
        - original_filename
        - stored_filename
        - file_path
        - file_size
        - mime_type
        - file_hash (optional)
        """
        ticket = self.session.query(Ticket).filter(Ticket.id == message.ticket_id).one_or_none()
        if ticket is None:
            raise NotFound("Ticket not found")

        created: list[Attachment] = []
        for f in files:
            attachment = Attachment(
                message_id=message.id,
                original_filename=f["original_filename"],
                stored_filename=f["stored_filename"],
                file_path=f["file_path"],
                file_size=int(f["file_size"]),
                mime_type=f["mime_type"],
                file_hash=f.get("file_hash"),
                uploaded_by_agent_id=uploaded_by_agent_id,
            )
            self.session.add(attachment)
            created.append(attachment)

        self.session.flush()

        ticket.attachments_count = (ticket.attachments_count or 0) + len(created)

        if self.ticket_event_service is not None:
            for att in created:
                self.ticket_event_service.add_event(
                    ticket_id=ticket.id,
                    agent_id=uploaded_by_agent_id,
                    action_type=EventType.attachment_added,
                    field_name="attachment",
                    old_value=None,
                    new_value=(att.original_filename or "")[:200],
                    comment=f"attachment_id={att.id}",
                )

        if commit:
            self.session.commit()
        else:
            self.session.flush()

        return created

    def get(self, *, attachment_id: int) -> AttachmentRead:
        att = self.session.query(Attachment).filter(Attachment.id == attachment_id).one_or_none()
        if att is None:
            raise NotFound("Attachment not found")
        return AttachmentRead.model_validate(att)

    def list(
        self,
        *,
        filters: dict[str, Any] | None = None,
        sort_by: str = "id",
        sort_desc: bool = False,
        limit: int = 100,
        offset: int = 0,
    ) -> list[AttachmentRead]:
        allowed_filters = {
            "id",
            "message_id",
            "uploaded_by_agent_id",
            "original_filename",
            "stored_filename",
            "mime_type",
            "file_hash",
            "download_count",
        }
        allowed_sort = {
            "id",
            "message_id",
            "uploaded_by_agent_id",
            "uploaded_at",
            "download_count",
            "file_size",
        }

        if filters:
            unknown = set(filters.keys()) - allowed_filters
            if unknown:
                raise ValueError(f"Unknown filter fields: {', '.join(sorted(unknown))}")

        query = self.session.query(Attachment)
        query = apply_filters(
            query,
            Attachment,
            filters=filters,
            text_like_fields={"original_filename", "stored_filename", "mime_type", "file_hash"},
        )
        query = apply_sort(
            query,
            Attachment,
            sort_by=sort_by,
            sort_desc=sort_desc,
            allowed_sort_fields=allowed_sort,
        )
        items = query.offset(offset).limit(limit).all()
        return [AttachmentRead.model_validate(a) for a in items]

    def create(
        self,
        *,
        attachment_data: AttachmentCreate,
        commit: bool = True,
    ) -> Attachment:
        att = Attachment(
            message_id=attachment_data.message_id,
            original_filename=attachment_data.original_filename,
            stored_filename=attachment_data.stored_filename,
            file_path=attachment_data.file_path,
            file_size=attachment_data.file_size,
            mime_type=attachment_data.mime_type,
            file_hash=attachment_data.file_hash,
            uploaded_by_agent_id=attachment_data.uploaded_by_agent_id,
            download_count=attachment_data.download_count,
        )
        self.session.add(att)
        self.session.flush()

        # Keep ticket counter in sync.
        ticket_id = self.session.query(Message.ticket_id).filter(Message.id == att.message_id).scalar()
        if ticket_id is not None:
            ticket = self.session.query(Ticket).filter(Ticket.id == ticket_id).one_or_none()
            if ticket is not None:
                ticket.attachments_count = (ticket.attachments_count or 0) + 1

        if self.ticket_event_service is not None and ticket_id is not None:
            self.ticket_event_service.add_event(
                ticket_id=ticket_id,
                agent_id=attachment_data.uploaded_by_agent_id,
                action_type=EventType.attachment_added,
                field_name="attachment",
                old_value=None,
                new_value=(att.original_filename or "")[:200],
                comment=f"attachment_id={att.id}",
            )

        if commit:
            self.session.commit()
        else:
            self.session.flush()
        return att

    def update(
        self,
        *,
        attachment_id: int,
        attachment_data: AttachmentUpdate,
        commit: bool = True,
    ) -> Attachment:
        att = self.session.query(Attachment).filter(Attachment.id == attachment_id).one_or_none()
        if att is None:
            raise NotFound("Attachment not found")

        updates = attachment_data.model_dump(exclude_none=True)
        for k, v in updates.items():
            setattr(att, k, v)

        if commit:
            self.session.commit()
        else:
            self.session.flush()
        return att

    def delete(
        self,
        *,
        attachment_id: int,
        commit: bool = True,
    ) -> DeleteResponse:
        att = self.session.query(Attachment).filter(Attachment.id == attachment_id).one_or_none()
        if att is None:
            return DeleteResponse(success=False, deleted_id=None, detail="Attachment not found")

        ticket_id = self.session.query(Message.ticket_id).filter(Message.id == att.message_id).scalar()
        if ticket_id is not None:
            ticket = self.session.query(Ticket).filter(Ticket.id == ticket_id).one_or_none()
            if ticket is not None:
                ticket.attachments_count = max((ticket.attachments_count or 0) - 1, 0)

        self.session.delete(att)
        if commit:
            self.session.commit()
        else:
            self.session.flush()
        return DeleteResponse(success=True, deleted_id=attachment_id)

