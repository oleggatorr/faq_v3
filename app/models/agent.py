from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Enum as SQLEnum, Text
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import enum
from .base import Base

class AgentRole(str, enum.Enum):
    admin = "admin"
    operator = "operator"
    readonly = "readonly"

class Agent(Base):
    __tablename__ = "agents"

    id = Column(Integer, primary_key=True, autoincrement=True)
    full_name = Column(String(200), nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    login = Column(String(100), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(SQLEnum(AgentRole), nullable=False, default=AgentRole.operator, index=True)

    category_access = Column(Text, nullable=False, default="")
    permissions = Column(Text, nullable=False, default="")

    department_id = Column(Integer, ForeignKey("departments.id", ondelete="SET NULL", onupdate="CASCADE"), nullable=True, index=True)

    is_active = Column(Boolean, default=True, nullable=False, index=True)
    phone = Column(String(50), nullable=True)
    avatar_path = Column(String(500), nullable=True)
    last_login_at = Column(DateTime(timezone=True), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Составные индексы для ускорения частых запросов
    __table_args__ = (
        # Индекс для входа: логин + активный статус
        # Индекс для списка агентов: активность + роль + департамент
        # Индекс для поиска по ФИО (частичный, для активных)
    )

    department = relationship("Department", back_populates="agents")
    owned_tickets = relationship("Ticket", foreign_keys="Ticket.owner_id", back_populates="owner")
    opened_tickets = relationship("Ticket", foreign_keys="Ticket.opened_by_id", back_populates="opened_by")
    closed_tickets = relationship("Ticket", foreign_keys="Ticket.closed_by_id", back_populates="closed_by")
    messages = relationship("Message", back_populates="agent")
    attachments = relationship("Attachment", back_populates="uploader")
    events = relationship("TicketEvent", back_populates="agent")
    audit_logs = relationship("AuditLog", back_populates="agent")