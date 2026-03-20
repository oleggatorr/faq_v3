from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import enum
from .base import Base

class Priority(str, enum.Enum):
    low = "low"
    normal = "normal"
    high = "high"
    urgent = "urgent"

class Ticket(Base):
    __tablename__ = "tickets"

    id = Column(Integer, primary_key=True, autoincrement=True)
    track_id = Column(String(20), unique=True, nullable=False, index=True)
    
    customer_name = Column(String(200), nullable=False)
    customer_email = Column(String(255), nullable=False, index=True)
    customer_ip = Column(String(45), nullable=False)
    
    department_id = Column(Integer, ForeignKey("departments.id", ondelete="RESTRICT", onupdate="CASCADE"), nullable=False, index=True)
    language_id = Column(Integer, ForeignKey("languages.id", ondelete="SET NULL", onupdate="CASCADE"), nullable=True, index=True)
    category_id = Column(Integer, ForeignKey("question_categories.id", ondelete="SET NULL", onupdate="CASCADE"), nullable=True, index=True)
    status_id = Column(Integer, ForeignKey("ticket_statuses.id", ondelete="RESTRICT", onupdate="CASCADE"), nullable=False, default=1, index=True)
    
    priority = Column(SQLEnum(Priority), nullable=False, default=Priority.normal, index=True)
    subject = Column(String(255), nullable=False)
    preview_message = Column(Text, nullable=True)
    
    owner_id = Column(Integer, ForeignKey("agents.id", ondelete="SET NULL", onupdate="CASCADE"), nullable=True, index=True)
    opened_by_id = Column(Integer, ForeignKey("agents.id", ondelete="SET NULL", onupdate="CASCADE"), nullable=True, index=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), index=True)
    
    first_responded_at = Column(DateTime(timezone=True), nullable=True)
    closed_at = Column(DateTime(timezone=True), nullable=True)
    closed_by_id = Column(Integer, ForeignKey("agents.id", ondelete="SET NULL", onupdate="CASCADE"), nullable=True)
    
    is_archived = Column(Boolean, default=False, nullable=False, index=True)
    is_locked = Column(Boolean, default=False, nullable=False)
    merged_into_id = Column(Integer, ForeignKey("tickets.id", ondelete="SET NULL", onupdate="CASCADE"), nullable=True, index=True)
    
    messages_count = Column(Integer, default=0, nullable=False)
    attachments_count = Column(Integer, default=0, nullable=False)

    department = relationship("Department", back_populates="tickets")
    language = relationship("Language", back_populates="tickets")
    category = relationship("QuestionCategory", back_populates="tickets")
    status = relationship("TicketStatus", back_populates="tickets")
    
    owner = relationship("Agent", foreign_keys=[owner_id], back_populates="owned_tickets")
    opened_by = relationship("Agent", foreign_keys=[opened_by_id], back_populates="opened_tickets")
    closed_by = relationship("Agent", foreign_keys=[closed_by_id], back_populates="closed_tickets")
    
    messages = relationship("Message", back_populates="ticket", cascade="all, delete-orphan")
    events = relationship("TicketEvent", back_populates="ticket", cascade="all, delete-orphan")
    
    merged_into = relationship("Ticket", remote_side=[id], backref="merged_tickets")