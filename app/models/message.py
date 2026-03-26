from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from .base import Base

class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ticket_id = Column(Integer, ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False, index=True)
    agent_id = Column(Integer, ForeignKey("agents.id", ondelete="SET NULL", onupdate="CASCADE"), nullable=True, index=True)

    # ФИО отправителя (заполняется при создании)
    # - Если от агента → agent.full_name
    # - Если от клиента → customer_name
    sender_name = Column(String(200), nullable=True)

    customer_name = Column(String(200), nullable=True)
    customer_email = Column(String(255), nullable=True)
    subject = Column(String(255), nullable=True)
    body = Column(Text, nullable=False)

    is_internal = Column(Boolean, default=False, nullable=False, index=True)
    is_automatic = Column(Boolean, default=False, nullable=False)
    ip_address = Column(String(45), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    ticket = relationship("Ticket", back_populates="messages")
    agent = relationship("Agent", back_populates="messages")
    attachments = relationship("Attachment", back_populates="message", cascade="all, delete-orphan")