from abc import ABC
from sqlalchemy.orm import Session
from app.models.agent import Agent
from app.core.errors import AccessDeniedError
from app.core.permissions import Permission, has_permission


class AgentBaseService(ABC):
    """Базовый класс для всех сервисов агентов."""
    
    def __init__(self, db: Session, current_agent_id: int | None = None):
        self.db = db
        self.current_agent_id = current_agent_id
        self._current_agent: Agent | None = None
    
    def _get_current_agent(self) -> Agent:
        """Получить текущего агента."""
        if self._current_agent is None:
            if not self.current_agent_id:
                raise ValueError("current_agent_id не указан")
            
            self._current_agent = (
                self.db.query(Agent)
                .filter(Agent.id == self.current_agent_id, Agent.is_active == True)
                .one_or_none()
            )
            
            if not self._current_agent:
                raise ValueError(f"Агент {self.current_agent_id} не найден")
        
        return self._current_agent
    
    def _get_agent(self, agent_id: int) -> Agent:
        """Получить агента по ID."""
        agent = self.db.query(Agent).filter(Agent.id == agent_id).one_or_none()
        if not agent:
            raise ValueError(f"Агент {agent_id} не найден")
        return agent
    
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
