from sqlalchemy import Column, Integer, String, Boolean
from .base import Base
from sqlalchemy.orm import relationship

class TicketStatus(Base):
    __tablename__ = "ticket_statuses"

    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(50), unique=True, nullable=False)
    name = Column(String(100), nullable=False)
    color = Column(String(20), default='#999999')
    is_closed = Column(Boolean, default=False, nullable=False)
    is_default = Column(Boolean, default=False, nullable=False)
    sort_order = Column(Integer, default=0, nullable=False)

    tickets = relationship("Ticket", back_populates="status")