from sqlalchemy.orm import Session
from app.models.agent import Agent
from app.core.permissions import Permission
from app.schemas.agent import AgentRead
from app.services.agent.agent_base_service import AgentBaseService
from app.services.utils import apply_filters


class AgentQueryService(AgentBaseService):
    """Сервис для просмотра агентов (только чтение)."""
    
    def list(
        self,
        filters: dict | None = None,
        sort_by: str = "full_name",
        sort_desc: bool = False,
        limit: int = 50,
        offset: int = 0,
    ) -> list[AgentRead]:
        """
        Список всех агентов.
        Требуется: agent_view.
        """
        # Проверка права
        self._check_permission(Permission.agent_view)
        
        query = self.db.query(Agent)
        
        # Применяем фильтры
        if filters:
            if "is_active" in filters:
                query = query.filter(Agent.is_active == filters["is_active"])
            if "department_id" in filters:
                query = query.filter(Agent.department_id == filters["department_id"])
            if "role" in filters:
                query = query.filter(Agent.role == filters["role"])
            if "search" in filters:
                search = f"%{filters['search']}%"
                query = query.filter(
                    (Agent.full_name.ilike(search)) |
                    (Agent.email.ilike(search))
                )
        
        # Сортировка
        column = getattr(Agent, sort_by, Agent.full_name)
        query = query.order_by(column.desc() if sort_desc else column.asc())
        
        # Пагинация
        agents = query.offset(offset).limit(limit).all()
        return [AgentRead.model_validate(a) for a in agents]
    
    def get(self, agent_id: int) -> AgentRead:
        """
        Детали агента.
        Требуется: agent_view.
        """
        self._check_permission(Permission.agent_view)
        
        agent = self._get_agent(agent_id)
        return AgentRead.model_validate(agent)
    
    def get_current(self) -> AgentRead:
        """Получить текущего агента (без проверки прав)."""
        agent = self._get_current_agent()
        return AgentRead.model_validate(agent)
    
    def list_by_department(self, department_id: int) -> list[AgentRead]:
        """
        Агенты департамента.
        Требуется: agent_view.
        """
        self._check_permission(Permission.agent_view)
        
        agents = self.db.query(Agent).filter(
            Agent.department_id == department_id,
            Agent.is_active == True
        ).order_by(Agent.full_name).all()
        
        return [AgentRead.model_validate(a) for a in agents]
    
    def list_active(self) -> list[AgentRead]:
        """
        Только активные агенты.
        Требуется: agent_view.
        """
        self._check_permission(Permission.agent_view)
        
        agents = self.db.query(Agent).filter(
            Agent.is_active == True
        ).order_by(Agent.full_name).all()
        
        return [AgentRead.model_validate(a) for a in agents]
    
    def search(self, query: str, limit: int = 20) -> list[AgentRead]:
        """
        Поиск по имени/email.
        Требуется: agent_view.
        """
        self._check_permission(Permission.agent_view)
        
        search_term = f"%{query}%"
        agents = self.db.query(Agent).filter(
            (Agent.full_name.ilike(search_term)) |
            (Agent.email.ilike(search_term))
        ).limit(limit).all()
        
        return [AgentRead.model_validate(a) for a in agents]
