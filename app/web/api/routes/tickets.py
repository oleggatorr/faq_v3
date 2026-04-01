"""API для работы с тикетами."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.models import get_db
from app.services.ticket.ticket_service import TicketService

router = APIRouter(prefix="/tickets", tags=["tickets_api"])


@router.get("/by-track/{track_id}")
def get_ticket_by_track(track_id: str, db: Session = Depends(get_db)):
    """Получить тикет по трек-номеру (для API)."""
    ticket_service = TicketService(db)
    try:
        ticket = ticket_service.get_by_track_id(track_id)
        return {
            "id": ticket.id,
            "track_id": ticket.track_id,
            "subject": ticket.subject,
            "status_id": ticket.status_id,
            "owner_id": ticket.owner_id,
            "merged_into_id": ticket.merged_into_id,
        }
    except Exception:
        raise HTTPException(status_code=404, detail="Ticket not found")
