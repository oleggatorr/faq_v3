# Сервисы агентов — полная структура

## 📁 Файловая структура

```
app/services/
├── agent_query_service.py       # Просмотр агентов (списки, детали)
├── agent_create_service.py      # Создание агентов
├── agent_edit_service.py        # Редактирование данных
├── agent_delete_service.py      # Удаление агентов
├── agent_privacy_service.py     # Управление приватностью
├── agent_role_service.py        # Смена роли
├── agent_permission_service.py  # Управление правами
└── agent_base_service.py        # Базовый класс для сервисов
```

---

## 1. AgentBaseService

**Файл:** `app/services/agent_base_service.py`

**Назначение:** Базовый класс для всех сервисов агентов.

```python
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
```

---

## 2. AgentQueryService

**Файл:** `app/services/agent_query_service.py`

**Назначение:** Просмотр списка агентов и деталей (только чтение).

| Метод | Право | Описание |
|-------|-------|----------|
| `list(filters, sort_by, limit, offset)` | `agent_view` | Список всех агентов с фильтрами |
| `get(agent_id)` | `agent_view` | Детали конкретного агента |
| `get_current()` | (без проверки) | Получить текущего агента |
| `list_by_department(department_id)` | `agent_view` | Агенты департамента |
| `list_active()` | `agent_view` | Только активные агенты |
| `search(query)` | `agent_view` | Поиск по имени/email |

**Пример использования:**
```python
query_service = AgentQueryService(db, current_agent_id=agent.id)

# Все агенты
agents = query_service.list(
    filters={"is_active": True, "department_id": 5},
    sort_by="full_name",
    limit=50,
)

# Поиск
results = query_service.search(query="Иванов")

# Агенты департамента
dept_agents = query_service.list_by_department(department_id=3)
```

**Пример реализации:**
```python
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
        """Список всех агентов. Требуется: agent_view."""
        self._check_permission(Permission.agent_view)
        
        query = self.db.query(Agent)
        
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
        
        column = getattr(Agent, sort_by, Agent.full_name)
        query = query.order_by(column.desc() if sort_desc else column.asc())
        
        agents = query.offset(offset).limit(limit).all()
        return [AgentRead.model_validate(a) for a in agents]
    
    def get(self, agent_id: int) -> AgentRead:
        """Детали агента. Требуется: agent_view."""
        self._check_permission(Permission.agent_view)
        
        agent = self.db.query(Agent).filter(Agent.id == agent_id).one_or_none()
        if not agent:
            raise ValueError(f"Агент {agent_id} не найден")
        
        return AgentRead.model_validate(agent)
    
    def get_current(self) -> AgentRead:
        """Получить текущего агента (без проверки прав)."""
        agent = self._get_current_agent()
        return AgentRead.model_validate(agent)
    
    def list_by_department(self, department_id: int) -> list[AgentRead]:
        """Агенты департамента. Требуется: agent_view."""
        self._check_permission(Permission.agent_view)
        
        agents = self.db.query(Agent).filter(
            Agent.department_id == department_id,
            Agent.is_active == True
        ).all()
        
        return [AgentRead.model_validate(a) for a in agents]
    
    def list_active(self) -> list[AgentRead]:
        """Только активные агенты. Требуется: agent_view."""
        self._check_permission(Permission.agent_view)
        
        agents = self.db.query(Agent).filter(
            Agent.is_active == True
        ).order_by(Agent.full_name).all()
        
        return [AgentRead.model_validate(a) for a in agents]
    
    def search(self, query: str, limit: int = 20) -> list[AgentRead]:
        """Поиск по имени/email. Требуется: agent_view."""
        self._check_permission(Permission.agent_view)
        
        search_term = f"%{query}%"
        agents = self.db.query(Agent).filter(
            (Agent.full_name.ilike(search_term)) |
            (Agent.email.ilike(search_term))
        ).limit(limit).all()
        
        return [AgentRead.model_validate(a) for a in agents]
```

---

## 3. AgentCreateService

**Файл:** `app/services/agent_create_service.py`

**Назначение:** Создание новых агентов.

| Метод | Право | Описание |
|-------|-------|----------|
| `create(agent_data, created_by_agent_id)` | `agent_create` | Создать агента |
| `create_with_defaults(agent_data, created_by_agent_id)` | `agent_create` | Создать с правами по умолчанию |

**Пример:**
```python
create_service = AgentCreateService(db, current_agent_id=agent.id)

# Создание агента
agent_data = AgentCreate(
    full_name="Иванов Иван",
    email="ivanov@example.com",
    password="SecurePass123",
    role="operator",
    department_id=5,
)
new_agent = create_service.create(agent_data)
```

**Пример реализации:**
```python
from sqlalchemy.orm import Session
from app.models.agent import Agent, AgentRole
from app.core.permissions import Permission
from app.core.security import hash_password
from app.schemas.agent import AgentCreate
from app.services.agent_base_service import AgentBaseService


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
        """
        # Проверка права
        self._check_permission(Permission.agent_create)
        
        # Проверка уникальности email
        existing = self.db.query(Agent).filter(
            Agent.email == agent_data.email.lower()
        ).one_or_none()
        
        if existing:
            raise ValueError(f"Агент с email {agent_data.email} уже существует")
        
        # Хэширование пароля
        password_hash = hash_password(agent_data.password)
        
        # Создание
        agent = Agent(
            email=agent_data.email.lower(),
            full_name=agent_data.full_name.strip(),
            password_hash=password_hash,
            role=agent_data.role or AgentRole.operator,
            department_id=agent_data.department_id,
            phone=agent_data.phone,
            category_access=agent_data.category_access or "",
            permissions=agent_data.permissions or "",
            is_active=agent_data.is_active if agent_data.is_active is not None else True,
        )
        
        self.db.add(agent)
        self.db.flush()
        
        # Аудит
        self._log_event(
            action="agent_created",
            target_agent_id=agent.id,
            created_by_agent_id=created_by_agent_id,
            details={
                "email": agent.email,
                "full_name": agent.full_name,
                "role": agent.role.value,
            },
        )
        
        return AgentRead.model_validate(agent)
    
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
    
    def _log_event(self, action: str, **kwargs) -> None:
        """Записать событие в аудит (опционально)."""
        # Здесь можно вызвать AuditLogService
        pass
```

---

## 4. AgentEditService

**Файл:** `app/services/agent_edit_service.py`

**Назначение:** Редактирование данных агента.

| Метод | Право | Описание |
|-------|-------|----------|
| `update(agent_id, agent_data)` | `agent_edit` | Обновить все поля |
| `update_profile(agent_id, full_name, phone)` | `agent_edit` | Обновить профиль |
| `update_email(agent_id, new_email)` | `agent_edit` | Сменить email |
| `change_password(agent_id, new_password)` | `agent_edit` | Сменить пароль |

**Пример:**
```python
edit_service = AgentEditService(db, current_agent_id=agent.id)

# Обновление данных
update_data = AgentUpdate(
    full_name="Новое Имя",
    email="new@example.com",
    phone="+1234567890",
)
updated_agent = edit_service.update(agent_id=5, agent_data=update_data)

# Смена пароля
edit_service.change_password(agent_id=5, new_password="NewSecurePass123")
```

**Пример реализации:**
```python
from sqlalchemy.orm import Session
from app.models.agent import Agent
from app.core.permissions import Permission
from app.core.security import hash_password
from app.schemas.agent import AgentUpdate
from app.services.agent_base_service import AgentBaseService


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
        """
        # Проверка права
        self._check_permission(Permission.agent_edit)
        
        # Получение агента
        agent = self._get_agent(agent_id)
        
        changes = {}
        updatable_fields = {
            "full_name": lambda v: v.strip() if v else None,
            "email": lambda v: v.lower().strip() if v else None,
            "phone": lambda v: v.strip() if v else None,
            "department_id": lambda v: v,
            "category_access": lambda v: v,
            "permissions": lambda v: v,
            "is_active": lambda v: v,
        }
        
        for field, processor in updatable_fields.items():
            value = getattr(agent_data, field, None)
            if value is not None:
                old_value = getattr(agent, field)
                new_value = processor(value)
                
                if old_value != new_value:
                    setattr(agent, field, new_value)
                    changes[field] = {"old": old_value, "new": new_value}
        
        # Пароль (отдельно, только если указан)
        if agent_data.password and agent_data.password.strip():
            agent.password_hash = hash_password(agent_data.password)
            changes["password"] = {"old": "****", "new": "****"}
        
        self.db.flush()
        
        # Аудит
        if changes:
            self._log_event(
                action="agent_updated",
                target_agent_id=agent.id,
                updated_by_agent_id=updated_by_agent_id,
                details={"changes": changes},
            )
        
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
        
        # Аудит
        self._log_event(
            action="agent_password_changed",
            target_agent_id=agent.id,
            updated_by_agent_id=updated_by_agent_id,
        )
        
        return True
```

---

## 5. AgentDeleteService

**Файл:** `app/services/agent_delete_service.py`

**Назначение:** Удаление агентов.

| Метод | Право | Описание |
|-------|-------|----------|
| `delete(agent_id, deleted_by_agent_id)` | `agent_delete` | Удалить агента |
| `bulk_delete(agent_ids, deleted_by_agent_id)` | `agent_delete` | Массовое удаление |
| `can_delete(agent_id)` | `agent_delete` | Проверка возможности удаления |

**Пример:**
```python
delete_service = AgentDeleteService(db, current_agent_id=agent.id)

# Удаление одного агента
deleted = delete_service.delete(agent_id=5, deleted_by_agent_id=agent.id)

# Проверка возможности удаления
if delete_service.can_delete(agent_id=5):
    delete_service.delete(agent_id=5, deleted_by_agent_id=agent.id)
```

**Пример реализации:**
```python
from sqlalchemy.orm import Session
from app.models.agent import Agent
from app.core.permissions import Permission
from app.services.agent_base_service import AgentBaseService


class AgentDeleteService(AgentBaseService):
    """Сервис для удаления агентов."""
    
    def delete(
        self,
        agent_id: int,
        deleted_by_agent_id: int | None = None,
    ) -> bool:
        """
        Удалить агента.
        Требуется: agent_delete.
        
        Returns:
            True если удалён, False если не найден
        """
        # Проверка права
        self._check_permission(Permission.agent_delete)
        
        # Получение агента
        agent = self.db.query(Agent).filter(Agent.id == agent_id).one_or_none()
        if not agent:
            return False
        
        # Защита: нельзя удалить самого себя
        if agent.id == deleted_by_agent_id:
            raise BusinessRuleError("Нельзя удалить самого себя")
        
        # Защита: нельзя удалить последнего админа
        if agent.role == "admin":
            admin_count = self.db.query(Agent).filter(
                Agent.role == "admin",
                Agent.is_active == True
            ).count()
            
            if admin_count <= 1:
                raise BusinessRuleError(
                    "Нельзя удалить последнего администратора"
                )
        
        # Удаление
        agent_email = agent.email
        self.db.delete(agent)
        self.db.flush()
        
        # Аудит
        self._log_event(
            action="agent_deleted",
            target_agent_id=agent_id,
            deleted_by_agent_id=deleted_by_agent_id,
            details={"deleted_email": agent_email},
        )
        
        return True
    
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
            try:
                if self.delete(agent_id, deleted_by_agent_id):
                    results["deleted"].append(agent_id)
                else:
                    results["failed"].append({"id": agent_id, "reason": "not_found"})
            except Exception as e:
                results["failed"].append({"id": agent_id, "reason": str(e)})
        
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
```

---

## 6. AgentPrivacyService

**Файл:** `app/services/agent_privacy_service.py`

**Назначение:** Управление приватностью и доступом агентов.

| Метод | Право | Описание |
|-------|-------|----------|
| `update_privacy(agent_id, is_active, category_access, permissions)` | `can_privacy` | Обновить настройки приватности |
| `activate(agent_id)` | `can_privacy` | Активировать агента |
| `deactivate(agent_id)` | `can_privacy` | Деактивировать агента |
| `update_category_access(agent_id, categories)` | `can_privacy` | Изменить доступ к категориям |
| `update_permissions(agent_id, permissions)` | `can_privacy` | Изменить права |

**Пример:**
```python
privacy_service = AgentPrivacyService(db, current_agent_id=agent.id)

# Деактивировать агента
privacy_service.deactivate(agent_id=5)

# Изменить права
privacy_service.update_permissions(
    agent_id=5,
    permissions="can_view_tickets,can_reply_tickets",
)
```

**Пример реализации:**
```python
from sqlalchemy.orm import Session
from app.models.agent import Agent
from app.core.permissions import Permission
from app.services.agent_base_service import AgentBaseService


class AgentPrivacyService(AgentBaseService):
    """Сервис для управления приватностью агентов."""
    
    def update_privacy(
        self,
        agent_id: int,
        is_active: bool | None = None,
        category_access: str | None = None,
        permissions: str | None = None,
        updated_by_agent_id: int | None = None,
    ) -> AgentRead:
        """
        Изменить настройки приватности агента.
        Требуется: can_privacy.
        """
        # Проверка права
        self._check_permission(Permission.can_privacy)
        
        agent = self._get_agent(agent_id)
        changes = {}
        
        if is_active is not None:
            old_value = agent.is_active
            agent.is_active = is_active
            changes["is_active"] = {"old": old_value, "new": is_active}
        
        if category_access is not None:
            old_value = agent.category_access
            agent.category_access = category_access
            changes["category_access"] = {"old": old_value, "new": category_access}
        
        if permissions is not None:
            old_value = agent.permissions
            agent.permissions = permissions
            changes["permissions"] = {"old": old_value, "new": permissions}
        
        self.db.flush()
        
        # Аудит
        if changes:
            self._log_event(
                action="agent_privacy_updated",
                target_agent_id=agent.id,
                updated_by_agent_id=updated_by_agent_id,
                details={"changes": changes},
            )
        
        return AgentRead.model_validate(agent)
    
    def activate(self, agent_id: int, updated_by_agent_id: int | None = None) -> AgentRead:
        """Активировать агента. Требуется: can_privacy."""
        return self.update_privacy(agent_id, is_active=True, updated_by_agent_id=updated_by_agent_id)
    
    def deactivate(self, agent_id: int, updated_by_agent_id: int | None = None) -> AgentRead:
        """Деактивировать агента. Требуется: can_privacy."""
        return self.update_privacy(agent_id, is_active=False, updated_by_agent_id=updated_by_agent_id)
    
    def update_category_access(
        self,
        agent_id: int,
        categories: list[str] | str,
        updated_by_agent_id: int | None = None,
    ) -> AgentRead:
        """
        Изменить доступ к категориям.
        Требуется: can_privacy.
        
        Args:
            categories: Список ID категорий или строка через запятую
        """
        if isinstance(categories, list):
            category_access = ",".join(str(c) for c in categories)
        else:
            category_access = categories
        
        return self.update_privacy(
            agent_id,
            category_access=category_access,
            updated_by_agent_id=updated_by_agent_id,
        )
    
    def update_permissions(
        self,
        agent_id: int,
        permissions: list[Permission] | str,
        updated_by_agent_id: int | None = None,
    ) -> AgentRead:
        """
        Изменить права агента.
        Требуется: can_privacy.
        
        Args:
            permissions: Список прав или строка через запятую
        """
        if isinstance(permissions, list):
            perm_str = ",".join(p.value for p in permissions)
        else:
            perm_str = permissions
        
        return self.update_privacy(
            agent_id,
            permissions=perm_str,
            updated_by_agent_id=updated_by_agent_id,
        )
```

---

## 7. AgentRoleService

**Файл:** `app/services/agent_role_service.py`

**Назначение:** Изменение роли агента.

| Метод | Право | Описание |
|-------|-------|----------|
| `change_role(agent_id, new_role)` | `can_man_users` | Изменить роль |
| `promote_to_admin(agent_id)` | `can_man_users` | Повысить до админа |
| `demote_to_operator(agent_id)` | `can_man_users` | Понизить до оператора |

**Пример:**
```python
role_service = AgentRoleService(db, current_agent_id=agent.id)

# Изменить роль
role_service.change_role(agent_id=5, new_role="admin")

# Повысить до админа
role_service.promote_to_admin(agent_id=5)
```

**Пример реализации:**
```python
from sqlalchemy.orm import Session
from app.models.agent import Agent, AgentRole
from app.core.permissions import Permission
from app.services.agent_base_service import AgentBaseService


class AgentRoleService(AgentBaseService):
    """Сервис для изменения роли агента."""
    
    def change_role(
        self,
        agent_id: int,
        new_role: str | AgentRole,
        updated_by_agent_id: int | None = None,
    ) -> AgentRead:
        """
        Изменить роль агента.
        Требуется: can_man_users.
        """
        # Проверка права
        self._check_permission(Permission.can_man_users)
        
        agent = self._get_agent(agent_id)
        old_role = agent.role
        
        # Валидация роли
        if isinstance(new_role, str):
            try:
                new_role = AgentRole(new_role)
            except ValueError:
                raise ValueError(f"Неверная роль: {new_role}")
        
        if old_role == new_role:
            return AgentRead.model_validate(agent)
        
        # Защита: нельзя снять последнего админа
        if old_role == AgentRole.admin:
            admin_count = self.db.query(Agent).filter(
                Agent.role == AgentRole.admin,
                Agent.is_active == True
            ).count()
            
            if admin_count <= 1:
                raise BusinessRuleError(
                    "Нельзя снять последнего администратора"
                )
        
        # Изменение роли
        agent.role = new_role
        
        # При повышении до админа — дать все права
        if new_role == AgentRole.admin:
            agent.permissions = ""  # Админ имеет все права автоматически
        
        self.db.flush()
        
        # Аудит
        self._log_event(
            action="agent_role_changed",
            target_agent_id=agent.id,
            updated_by_agent_id=updated_by_agent_id,
            details={
                "old_role": old_role.value,
                "new_role": new_role.value,
            },
        )
        
        return AgentRead.model_validate(agent)
    
    def promote_to_admin(
        self,
        agent_id: int,
        updated_by_agent_id: int | None = None,
    ) -> AgentRead:
        """Повысить до админа. Требуется: can_man_users."""
        return self.change_role(agent_id, AgentRole.admin, updated_by_agent_id)
    
    def demote_to_operator(
        self,
        agent_id: int,
        updated_by_agent_id: int | None = None,
    ) -> AgentRead:
        """Понизить до оператора. Требуется: can_man_users."""
        return self.change_role(agent_id, AgentRole.operator, updated_by_agent_id)
```

---

## 8. AgentPermissionService

**Файл:** `app/services/agent_permission_service.py`

**Назначение:** Управление правами агента.

| Метод | Право | Описание |
|-------|-------|----------|
| `update_permissions(agent_id, permissions)` | `can_man_users` | Установить права |
| `add_permission(agent_id, permission)` | `can_man_users` | Добавить право |
| `remove_permission(agent_id, permission)` | `can_man_users` | Отозвать право |
| `reset_to_defaults(agent_id)` | `can_man_users` | Сбросить к правам по умолчанию |

**Пример:**
```python
perm_service = AgentPermissionService(db, current_agent_id=agent.id)

# Установить права
perm_service.update_permissions(
    agent_id=5,
    permissions=[Permission.can_view_tickets, Permission.can_reply_tickets],
)

# Добавить право
perm_service.add_permission(agent_id=5, permission=Permission.can_edit_tickets)
```

**Пример реализации:**
```python
from sqlalchemy.orm import Session
from app.models.agent import Agent
from app.core.permissions import Permission
from app.services.agent_base_service import AgentBaseService


class AgentPermissionService(AgentBaseService):
    """Сервис для управления правами агентов."""
    
    def update_permissions(
        self,
        agent_id: int,
        permissions: list[Permission] | str,
        updated_by_agent_id: int | None = None,
    ) -> AgentRead:
        """
        Установить права агента.
        Требуется: can_man_users.
        
        Args:
            permissions: Список прав или строка через запятую
        """
        # Проверка права
        self._check_permission(Permission.can_man_users)
        
        agent = self._get_agent(agent_id)
        old_permissions = agent.permissions
        
        # Преобразование в строку
        if isinstance(permissions, list):
            perm_str = ",".join(p.value for p in permissions)
        else:
            perm_str = permissions
        
        agent.permissions = perm_str
        self.db.flush()
        
        # Аудит
        self._log_event(
            action="agent_permissions_updated",
            target_agent_id=agent.id,
            updated_by_agent_id=updated_by_agent_id,
            details={
                "old_permissions": old_permissions,
                "new_permissions": perm_str,
            },
        )
        
        return AgentRead.model_validate(agent)
    
    def add_permission(
        self,
        agent_id: int,
        permission: Permission,
        updated_by_agent_id: int | None = None,
    ) -> AgentRead:
        """
        Добавить право агенту.
        Требуется: can_man_users.
        """
        self._check_permission(Permission.can_man_users)
        
        agent = self._get_agent(agent_id)
        
        # Получение текущих прав
        current_perms = set(agent.permissions.split(",")) if agent.permissions else set()
        
        # Добавление нового права
        current_perms.add(permission.value)
        
        return self.update_permissions(
            agent_id,
            list(Permission(p) for p in current_perms),
            updated_by_agent_id,
        )
    
    def remove_permission(
        self,
        agent_id: int,
        permission: Permission,
        updated_by_agent_id: int | None = None,
    ) -> AgentRead:
        """
        Отозвать право агента.
        Требуется: can_man_users.
        """
        self._check_permission(Permission.can_man_users)
        
        agent = self._get_agent(agent_id)
        
        # Получение текущих прав
        current_perms = set(agent.permissions.split(",")) if agent.permissions else set()
        
        # Удаление права
        current_perms.discard(permission.value)
        
        return self.update_permissions(
            agent_id,
            list(Permission(p) for p in current_perms) if current_perms else "",
            updated_by_agent_id,
        )
    
    def reset_to_defaults(
        self,
        agent_id: int,
        updated_by_agent_id: int | None = None,
    ) -> AgentRead:
        """
        Сбросить права к правам по умолчанию.
        Требуется: can_man_users.
        """
        from app.core.permissions import DEFAULT_OPERATOR_PERMISSIONS
        
        return self.update_permissions(
            agent_id,
            DEFAULT_OPERATOR_PERMISSIONS,
            updated_by_agent_id,
        )
```

---

## 📊 Сводная таблица прав

| Право | Сервисы используют |
|-------|-------------------|
| `agent_view` | AgentQueryService.list(), get() |
| `agent_create` | AgentCreateService.create() |
| `agent_edit` | AgentEditService.update() |
| `agent_delete` | AgentDeleteService.delete() |
| `can_privacy` | AgentPrivacyService.update_privacy() |
| `can_man_users` | AgentRoleService.change_role(), AgentPermissionService.update_permissions() |

---

## 🚀 Использование в роутах

```python
# app/web/jinja/routes/agents/routes.py

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from app.core.auth import CurrentAgent
from app.models import get_db
from app.schemas.agent import AgentCreate, AgentUpdate
from app.services import (
    AgentQueryService,
    AgentCreateService,
    AgentEditService,
    AgentDeleteService,
)

router = APIRouter(prefix="/agents", tags=["agents"])


@router.get("", response_class=HTMLResponse)
def agents_list(
    request: Request,
    agent: CurrentAgent,
    db: Session = Depends(get_db),
):
    """Список агентов."""
    query_service = AgentQueryService(db, current_agent_id=agent.id)
    agents = query_service.list(
        filters={"search": request.query_params.get("search")},
        limit=50,
    )
    return templates.TemplateResponse("agents/list.html", {
        "agents": agents,
        "agent": agent,
    })


@router.get("/add", response_class=HTMLResponse)
def add_agent_form(request: Request, agent: CurrentAgent):
    """Форма создания агента."""
    return templates.TemplateResponse("agents/add.html", {"agent": agent})


@router.post("/add", response_class=RedirectResponse)
def add_agent_submit(
    request: Request,
    agent: CurrentAgent,
    db: Session = Depends(get_db),
    full_name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    role: str = Form("operator"),
):
    """Создание агента."""
    create_service = AgentCreateService(db, current_agent_id=agent.id)
    agent_data = AgentCreate(
        full_name=full_name,
        email=email,
        password=password,
        role=role,
    )
    create_service.create(agent_data, created_by_agent_id=agent.id)
    return RedirectResponse(url="/agents")


@router.post("/{agent_id}/delete", response_class=RedirectResponse)
def delete_agent(
    agent_id: int,
    agent: CurrentAgent,
    db: Session = Depends(get_db),
):
    """Удаление агента."""
    delete_service = AgentDeleteService(db, current_agent_id=agent.id)
    delete_service.delete(agent_id, deleted_by_agent_id=agent.id)
    return RedirectResponse(url="/agents")
```

---

## 📁 Структура файлов

```
app/
├── core/
│   └── permissions.py          # Permission enum, PERMISSION_LABELS
├── models/
│   └── agent.py                # Agent модель
├── schemas/
│   └── agent.py                # AgentCreate, AgentUpdate, AgentRead
├── services/
│   ├── agent_base_service.py
│   ├── agent_query_service.py
│   ├── agent_create_service.py
│   ├── agent_edit_service.py
│   ├── agent_delete_service.py
│   ├── agent_privacy_service.py
│   ├── agent_role_service.py
│   └── agent_permission_service.py
└── web/jinja/routes/
    └── agents/
        └── routes.py           # Роуты агентов
```

---

## Контакты

По вопросам расширения системы агентов обращайтесь к:
- Разработчик: команда разработки
- Дата последнего обновления: 2026-03-27
