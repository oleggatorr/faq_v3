from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, BigInteger, Enum as SQLEnum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import enum
from .base import Base

class EventType(str, enum.Enum):
    created = "created"
    replied = "replied"
    status_changed = "status_changed"
    priority_changed = "priority_changed"
    assigned = "assigned"
    unassigned = "unassigned"
    category_changed = "category_changed"
    merged = "merged"
    closed = "closed"
    reopened = "reopened"
    locked = "locked"
    unlocked = "unlocked"
    note_added = "note_added"
    attachment_added = "attachment_added"
    customer_replied = "customer_replied"

class TicketEvent(Base):
    __tablename__ = "ticket_events"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    ticket_id = Column(BigInteger, ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False, index=True)
    agent_id = Column(BigInteger, ForeignKey("agents.id", ondelete="SET NULL", onupdate="CASCADE"), nullable=True, index=True)
    
    action_type = Column(SQLEnum(EventType), nullable=False, index=True)
    field_name = Column(String(100), nullable=True)
    old_value = Column(Text, nullable=True)
    new_value = Column(Text, nullable=True)
    comment = Column(Text, nullable=True)
    
    occurred_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    ticket = relationship("Ticket", back_populates="events")
    agent = relationship("Agent", back_populates="events")