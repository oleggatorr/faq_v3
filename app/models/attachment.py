from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from .base import Base

class Attachment(Base):
    __tablename__ = "attachments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    message_id = Column(Integer, ForeignKey("messages.id", ondelete="CASCADE"), nullable=False, index=True)
    
    original_filename = Column(String(255), nullable=False)
    stored_filename = Column(String(100), nullable=False, index=True)
    file_path = Column(String(500), nullable=False)
    file_size = Column(Integer, nullable=False)
    mime_type = Column(String(100), nullable=False)
    file_hash = Column(String(64), nullable=True, index=True)
    
    uploaded_by_agent_id = Column(Integer, ForeignKey("agents.id", ondelete="SET NULL", onupdate="CASCADE"), nullable=True, index=True)
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now())
    download_count = Column(Integer, default=0, nullable=False)

    message = relationship("Message", back_populates="attachments")
    uploader = relationship("Agent", back_populates="attachments")