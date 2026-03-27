from sqlalchemy.orm import Session
from app.models.agent import Agent
from app.core.permissions import Permission
from app.core.security import hash_password
from app.schemas.agent import AgentUpdate, AgentRead
from app.services.agent.agent_base_service import AgentBaseService


class AgentEditService(AgentBaseService):
    """Сервис для редактирования агентов."""
    
    def update(
        self,
        agent_id: int,
        agent_data: AgentUpdate,
        updated_by_agent_id: int | None = None,
    ) -> AgentRead:
        """
        Обновить данные агента.
        Требуется: agent_edit.
        
        Args:
            agent_id: Кого обновляем
            agent_data: Новые данные
            updated_by_agent_id: Кто обновил (для аудита)
        """
        # Проверка права
        self._check_permission(Permission.agent_edit)
        
        # Получение агента
        agent = self._get_agent(agent_id)
        
        # Защита: нельзя редактировать самого себя (опционально)
        # if agent.id == updated_by_agent_id:
        #     raise BusinessRuleError("Нельзя редактировать самого себя")
        
        # Поля для обновления
        updatable_fields = {
            "full_name": lambda v: v.strip() if v else None,
            "email": lambda v: v.lower().strip() if v else None,
            "phone": lambda v: v.strip() if v else None,
            "department_id": lambda v: v,
            "category_access": lambda v: v,
            "permissions": lambda v: v,
            "is_active": lambda v: v,
            "role": lambda v: v,
        }
        
        # Добавляем login если есть
        if hasattr(agent_data, 'login') and hasattr(agent, 'login'):
            updatable_fields["login"] = lambda v: v.strip() if v else None
        
        changes = {}
        
        for field, processor in updatable_fields.items():
            if hasattr(agent_data, field):
                value = getattr(agent_data, field, None)
                if value is not None:
                    old_value = getattr(agent, field)
                    new_value = processor(value)
                    
                    if old_value != new_value:
                        setattr(agent, field, new_value)
                        changes[field] = {"old": old_value, "new": new_value}
        
        # Пароль (отдельно, только если указан)
        if hasattr(agent_data, 'password') and agent_data.password and agent_data.password.strip():
            agent.password_hash = hash_password(agent_data.password)
            changes["password"] = {"old": "****", "new": "****"}
        
        self.db.flush()
        
        return AgentRead.model_validate(agent)
    
    def update_profile(
        self,
        agent_id: int,
        full_name: str | None = None,
        phone: str | None = None,
        updated_by_agent_id: int | None = None,
    ) -> AgentRead:
        """Обновить профиль (имя, телефон). Требуется: agent_edit."""
        update_data = AgentUpdate(
            full_name=full_name,
            phone=phone,
        )
        return self.update(agent_id, update_data, updated_by_agent_id)
    
    def update_email(
        self,
        agent_id: int,
        new_email: str,
        updated_by_agent_id: int | None = None,
    ) -> AgentRead:
        """Сменить email. Требуется: agent_edit."""
        # Проверка уникальности
        existing = self.db.query(Agent).filter(
            Agent.email == new_email.lower(),
            Agent.id != agent_id
        ).one_or_none()
        
        if existing:
            raise ValueError(f"Email {new_email} уже используется")
        
        update_data = AgentUpdate(email=new_email)
        return self.update(agent_id, update_data, updated_by_agent_id)
    
    def change_password(
        self,
        agent_id: int,
        new_password: str,
        updated_by_agent_id: int | None = None,
    ) -> bool:
        """Сменить пароль. Требуется: agent_edit."""
        self._check_permission(Permission.agent_edit)
        
        agent = self._get_agent(agent_id)
        agent.password_hash = hash_password(new_password)
        self.db.flush()
        
        return True
