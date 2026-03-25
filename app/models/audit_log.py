from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, BigInteger
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from .base import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    
    # Кто выполнил действие
    agent_id = Column(Integer, ForeignKey("agents.id", ondelete="SET NULL"), nullable=True, index=True)
    
    # Тип действия
    action = Column(String(50), nullable=False, index=True)
    
    # Тип объекта (ticket, agent, department и т.д.)
    entity_type = Column(String(50), nullable=False, index=True)
    
    # ID объекта
    entity_id = Column(Integer, nullable=True)
    
    # Дополнительные данные (JSON как текст)
    details = Column(Text, nullable=True)
    
    # IP-адрес
    ip_address = Column(String(45), nullable=True)
    
    # User-Agent
    user_agent = Column(String(500), nullable=True)
    
    # Время события
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    
    # Связи
    agent = relationship("Agent", back_populates="audit_logs")
