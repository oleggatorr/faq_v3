from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.models.agent import Agent
from app.schemas.agent import AgentCreate, AgentRead, AgentUpdate
from app.schemas.deletion import DeleteResponse

from .errors import NotFound
from .utils import apply_filters, apply_sort


class AgentService:
    """
    Agent CRUD and validations.
    """

    def __init__(self, session: Session):
        self.session = session

    def create(self, *, agent_data: AgentCreate, commit: bool = True) -> Agent:
        agent = Agent(
            full_name=agent_data.full_name,
            email=agent_data.email,
            login=agent_data.login,
            password_hash=agent_data.password_hash,
            role=agent_data.role,
            category_access=agent_data.category_access,
            permissions=agent_data.permissions,
            department_id=agent_data.department_id,
            is_active=agent_data.is_active,
            phone=agent_data.phone,
            avatar_path=agent_data.avatar_path,
            auto_assign=agent_data.auto_assign,
            email_notifications=agent_data.email_notifications,
            signature=agent_data.signature,
        )
        self.session.add(agent)
        if commit:
            self.session.commit()
        else:
            self.session.flush()
        return agent

    def get(self, *, agent_id: int) -> AgentRead:
        agent = self.session.query(Agent).filter(Agent.id == agent_id).one_or_none()
        if agent is None:
            raise NotFound("Agent not found")
        return AgentRead.model_validate(agent)

    def list(
        self,
        *,
        filters: dict[str, Any] | None = None,
        sort_by: str = "id",
        sort_desc: bool = False,
        limit: int = 100,
        offset: int = 0,
    ) -> list[AgentRead]:
        allowed_filters = {
            "id",
            "login",
            "full_name",
            "email",
            "role",
            "department_id",
            "is_active",
            "phone",
            "last_login_at",
            "search",  # Специальный параметр для поиска по login + full_name
            "category_id",  # Фильтр по категории (вхождение в category_access)
            "auto_assign",  # Фильтр по автоназначению
            "email_notifications",  # Фильтр по email-уведомлениям
        }
        allowed_sort = {
            "id",
            "login",
            "full_name",
            "email",
            "role",
            "department_id",
            "is_active",
            "last_login_at",
            "created_at",
            "updated_at",
            "auto_assign",
            "email_notifications",
        }

        if filters:
            unknown = set(filters.keys()) - allowed_filters
            if unknown:
                raise ValueError(f"Unknown filter fields: {', '.join(sorted(unknown))}")

        query = self.session.query(Agent)

        # Обработка специального параметра search (поиск по login + full_name)
        if filters and "search" in filters:
            search_term = filters.pop("search")
            if search_term:
                query = query.filter(
                    (Agent.login.ilike(f"%{search_term}%")) |
                    (Agent.full_name.ilike(f"%{search_term}%"))
                )
        
        # Обработка фильтра по категории (вхождение в category_access)
        if filters and "category_id" in filters:
            category_id = filters.pop("category_id")
            if category_id:
                # category_access хранится как строка с ID через запятую: "1,3,5"
                query = query.filter(
                    (Agent.category_access.like(f"{category_id},%")) |
                    (Agent.category_access.like(f"%,{category_id},%")) |
                    (Agent.category_access.like(f"%,{category_id}")) |
                    (Agent.category_access == str(category_id))
                )

        query = apply_filters(
            query,
            Agent,
            filters=filters,
            text_like_fields={"full_name", "email", "phone", "login"},
        )
        query = apply_sort(query, Agent, sort_by=sort_by, sort_desc=sort_desc, allowed_sort_fields=allowed_sort)
        agents = query.offset(offset).limit(limit).all()
        return [AgentRead.model_validate(a) for a in agents]

    def update(
        self,
        *,
        agent_id: int,
        agent_data: AgentUpdate,
        commit: bool = True,
    ) -> Agent:
        agent = self.session.query(Agent).filter(Agent.id == agent_id).one_or_none()
        if agent is None:
            raise NotFound("Agent not found")

        updates = agent_data.model_dump(exclude_none=True)
        for k, v in updates.items():
            setattr(agent, k, v)

        if commit:
            self.session.commit()
        else:
            self.session.flush()
        return agent

    def delete(
        self,
        *,
        agent_id: int,
        commit: bool = True,
    ) -> DeleteResponse:
        agent = self.session.query(Agent).filter(Agent.id == agent_id).one_or_none()
        if agent is None:
            return DeleteResponse(success=False, deleted_id=None, detail="Agent not found")

        self.session.delete(agent)
        if commit:
            self.session.commit()
        else:
            self.session.flush()
        return DeleteResponse(success=True, deleted_id=agent_id)

