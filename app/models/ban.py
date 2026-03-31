from sqlalchemy import Column, Integer, BigInteger, String, Text, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from .base import Base


class BannedEmail(Base):
    """Заблокированные email-адреса."""
    
    __tablename__ = "banned_emails"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String(255), nullable=False, unique=True, index=True)
    banned_by = Column(Integer, ForeignKey("agents.id", ondelete="SET NULL", onupdate="CASCADE"), nullable=True)
    reason = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Связь с агентом, который забанил
    banned_by_agent = relationship("Agent", foreign_keys=[banned_by])


class BannedIP(Base):
    """Заблокированные IP-адреса (поддерживает диапазоны)."""
    
    __tablename__ = "banned_ips"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    ip_from = Column(BigInteger, nullable=False)  # BIGINT UNSIGNED: начало диапазона
    ip_to = Column(BigInteger, nullable=False)  # BIGINT UNSIGNED: конец диапазона
    ip_display = Column(String(100), nullable=False)  # Человекочитаемое представление (напр. "192.168.1.*")
    banned_by = Column(Integer, ForeignKey("agents.id", ondelete="SET NULL", onupdate="CASCADE"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Связь с агентом, который забанил
    banned_by_agent = relationship("Agent", foreign_keys=[banned_by])
