from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, SmallInteger
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from .base import Base

class QuestionCategory(Base):
    __tablename__ = "question_categories"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(150), nullable=False)
    description = Column(Text, nullable=True)
    
    department_id = Column(Integer, ForeignKey("departments.id", ondelete="SET NULL", onupdate="CASCADE"), nullable=True, index=True)
    parent_id = Column(Integer, ForeignKey("question_categories.id", ondelete="CASCADE", onupdate="CASCADE"), nullable=True, index=True)
    
    icon = Column(String(100), nullable=True)
    color = Column(String(7), default='#999999')
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    sort_order = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    department = relationship("Department", back_populates="categories")
    parent = relationship("QuestionCategory", remote_side=[id], backref="children")
    tickets = relationship("Ticket", back_populates="category")