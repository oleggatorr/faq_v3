from sqlalchemy.orm import Session
from app.models.agent import Agent
from app.core.permissions import Permission
from app.schemas.deletion import DeleteResponse
from app.services.agent.agent_base_service import AgentBaseService


class AgentDeleteService(AgentBaseService):
    """Сервис для удаления агентов."""
    
    def delete(
        self,
        agent_id: int,
        deleted_by_agent_id: int | None = None,
    ) -> DeleteResponse:
        """
        Удалить агента.
        Требуется: agent_delete.
        
        Args:
            agent_id: Кого удаляем
            deleted_by_agent_id: Кто удалил (для аудита)
        
        Returns:
            DeleteResponse с результатом
        """
        # Проверка права
        self._check_permission(Permission.agent_delete)
        
        # Получение агента
        agent = self.db.query(Agent).filter(Agent.id == agent_id).one_or_none()
        if not agent:
            return DeleteResponse(success=False, deleted_id=None, detail="Агент не найден")
        
        # Защита: нельзя удалить самого себя
        if agent.id == deleted_by_agent_id:
            return DeleteResponse(
                success=False,
                deleted_id=None,
                detail="Нельзя удалить самого себя"
            )
        
        # Защита: нельзя удалить последнего админа
        if agent.role == "admin":
            admin_count = self.db.query(Agent).filter(
                Agent.role == "admin",
                Agent.is_active == True
            ).count()
            
            if admin_count <= 1:
                return DeleteResponse(
                    success=False,
                    deleted_id=None,
                    detail="Нельзя удалить последнего администратора"
                )
        
        # Удаление
        agent_email = agent.email
        self.db.delete(agent)
        self.db.flush()
        
        return DeleteResponse(success=True, deleted_id=agent_id)
    
    def bulk_delete(
        self,
        agent_ids: list[int],
        deleted_by_agent_id: int | None = None,
    ) -> dict:
        """
        Массовое удаление агентов.
        Требуется: agent_delete.
        
        Returns:
            dict с результатами: {"deleted": [...], "failed": [...]}
        """
        self._check_permission(Permission.agent_delete)
        
        results = {"deleted": [], "failed": []}
        
        for agent_id in agent_ids:
            result = self.delete(agent_id, deleted_by_agent_id)
            if result.success:
                results["deleted"].append(agent_id)
            else:
                results["failed"].append({"id": agent_id, "reason": result.detail})
        
        return results
    
    def can_delete(self, agent_id: int) -> bool:
        """
        Проверить возможность удаления.
        Требуется: agent_delete.
        
        Returns:
            True если можно удалить, False если есть защиты
        """
        self._check_permission(Permission.agent_delete)
        
        # Нельзя удалить самого себя
        if agent_id == self.current_agent_id:
            return False
        
        agent = self._get_agent(agent_id)
        
        # Нельзя удалить последнего админа
        if agent.role == "admin":
            admin_count = self.db.query(Agent).filter(
                Agent.role == "admin",
                Agent.is_active == True
            ).count()
            
            if admin_count <= 1:
                return False
        
        return True
