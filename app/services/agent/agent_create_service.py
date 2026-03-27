from sqlalchemy.orm import Session
from app.models.agent import Agent, AgentRole
from app.core.permissions import Permission
from app.core.security import hash_password
from app.schemas.agent import AgentCreate, AgentRead
from app.services.agent.agent_base_service import AgentBaseService


class AgentCreateService(AgentBaseService):
    """Сервис для создания агентов."""
    
    def create(
        self,
        agent_data: AgentCreate,
        created_by_agent_id: int | None = None,
    ) -> AgentRead:
        """
        Создать нового агента.
        Требуется: agent_create.
        
        Args:
            agent_data: Данные агента (email, password_hash, full_name, role, ...)
            created_by_agent_id: Кто создал (для аудита)
        """
        # Проверка права
        self._check_permission(Permission.agent_create)
        
        # Проверка уникальности email
        existing = self.db.query(Agent).filter(
            Agent.email == agent_data.email.lower()
        ).one_or_none()
        
        if existing:
            raise ValueError(f"Агент с email {agent_data.email} уже существует")
        
        # Проверка уникальности login (если есть такое поле)
        if hasattr(Agent, 'login') and hasattr(agent_data, 'login'):
            existing_login = self.db.query(Agent).filter(
                Agent.login == agent_data.login.strip()
            ).one_or_none()
            
            if existing_login:
                raise ValueError(f"Агент с логином {agent_data.login} уже существует")
        
        # Подготовка данных
        agent_dict = {
            "email": agent_data.email.lower(),
            "full_name": agent_data.full_name.strip(),
            "password_hash": agent_data.password_hash,  # Ожидаем уже захэшированный пароль
            "role": agent_data.role or AgentRole.operator,
            "department_id": agent_data.department_id,
            "phone": agent_data.phone.strip() if agent_data.phone else None,
            "category_access": agent_data.category_access or "",
            "permissions": agent_data.permissions or "",
            "is_active": agent_data.is_active if agent_data.is_active is not None else True,
        }
        
        # Добавляем login если есть
        if hasattr(agent_data, 'login') and agent_data.login:
            agent_dict["login"] = agent_data.login.strip()
        
        # Создание
        agent = Agent(**agent_dict)
        self.db.add(agent)
        self.db.flush()
        
        return AgentRead.model_validate(agent)
    
    def create_with_password(
        self,
        email: str,
        full_name: str,
        password: str,
        role: str | AgentRole = "operator",
        department_id: int | None = None,
        login: str | None = None,
        phone: str | None = None,
        category_access: str = "",
        permissions: str = "",
        is_active: bool = True,
        created_by_agent_id: int | None = None,
    ) -> AgentRead:
        """
        Создать агента с паролем (сервис сам захэширует).
        Требуется: agent_create.
        """
        # Хэширование пароля
        password_hash = hash_password(password)
        
        agent_data = AgentCreate(
            email=email,
            full_name=full_name,
            password_hash=password_hash,
            role=role if isinstance(role, AgentRole) else AgentRole(role),
            department_id=department_id,
            login=login or "",
            phone=phone,
            category_access=category_access,
            permissions=permissions,
            is_active=is_active,
        )
        
        return self.create(agent_data, created_by_agent_id)
    
    def create_with_defaults(
        self,
        agent_data: AgentCreate,
        created_by_agent_id: int | None = None,
    ) -> AgentRead:
        """
        Создать агента с правами по умолчанию.
        Требуется: agent_create.
        """
        # Если не указаны права — установить по умолчанию
        if not agent_data.permissions:
            from app.core.permissions import DEFAULT_OPERATOR_PERMISSIONS
            agent_data.permissions = ",".join(p.value for p in DEFAULT_OPERATOR_PERMISSIONS)
        
        return self.create(agent_data, created_by_agent_id)
