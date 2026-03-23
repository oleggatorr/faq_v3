from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.agent import Agent
from app.schemas.agent import AgentCreate, AgentRead

from .errors import NotFound


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
            password_hash=agent_data.password_hash,
            role=agent_data.role,
            category_access=agent_data.category_access,
            permissions=agent_data.permissions,
            department_id=agent_data.department_id,
            is_active=agent_data.is_active,
            phone=agent_data.phone,
            avatar_path=agent_data.avatar_path,
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

