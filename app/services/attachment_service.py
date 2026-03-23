from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.attachment import Attachment
from app.models.message import Message

from .ticket_event_service import TicketEventService


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
        raise NotImplementedError

