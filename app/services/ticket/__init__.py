"""
Сервисы для работы с тикетами.

Импорт из корневого пакета services:
    from app.services import TicketService, TicketEventService
    from app.services import MessageService, AttachmentService
"""

from app.services.ticket.ticket_base_service import TicketBaseService
from app.services.ticket.ticket_service import TicketService
from app.services.ticket.ticket_event_service import TicketEventService
from app.services.ticket.message_service import MessageService
from app.services.ticket.attachment_service import AttachmentService

__all__ = [
    "TicketBaseService",
    "TicketService",
    "TicketEventService",
    "MessageService",
    "AttachmentService",
]
