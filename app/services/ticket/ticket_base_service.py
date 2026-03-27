from abc import ABC
from sqlalchemy.orm import Session
from app.models.agent import Agent
from app.models.ticket import Ticket
from app.core.errors import AccessDeniedError
from app.core.permissions import Permission, has_permission


class TicketBaseService(ABC):
    """Базовый класс для всех сервисов тикетов."""
    
    def __init__(self, db: Session, agent_id: int | None = None):
        self.db = db
        self.session = db  # Алиас для совместимости с существующим кодом
        self.agent_id = agent_id
        self._current_agent: Agent | None = None
    
    def _get_current_agent(self) -> Agent:
        """Получить текущего агента."""
        if self._current_agent is None:
            if not self.agent_id:
                raise ValueError("agent_id не указан")
            
            self._current_agent = (
                self.db.query(Agent)
                .filter(Agent.id == self.agent_id, Agent.is_active == True)
                .one_or_none()
            )
            
            if not self._current_agent:
                raise ValueError(f"Агент {self.agent_id} не найден")
        
        return self._current_agent
    
    def _get_ticket(self, ticket_id: int) -> Ticket:
        """Получить тикет по ID."""
        ticket = self.db.query(Ticket).filter(Ticket.id == ticket_id).one_or_none()
        if not ticket:
            raise ValueError(f"Тикет {ticket_id} не найден")
        return ticket
    
    def _check_permission(self, permission: Permission) -> None:
        """Проверить право доступа."""
        agent = self._get_current_agent()
        if not has_permission(agent, permission):
            raise AccessDeniedError(
                detail=f"Нет прав: {permission.value}",
                required_permission=permission.value,
            )
    
    def _has_permission(self, permission: Permission) -> bool:
        """Проверить право (возвращает bool)."""
        agent = self._get_current_agent()
        return has_permission(agent, permission)
