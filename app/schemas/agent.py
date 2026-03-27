from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.core.permissions import Permission
from app.models.agent import AgentRole


class AgentBase(BaseModel):
    full_name: str
    email: str
    login: str
    role: AgentRole = AgentRole.operator
    category_access: str = ""
    permissions: str = ""
    department_id: int | None = None
    is_active: bool = True
    phone: str | None = None
    avatar_path: str | None = None


class AgentCreate(AgentBase):
    password_hash: str


class AgentUpdate(BaseModel):
    full_name: str | None = None
    email: str | None = None
    login: str | None = None
    password_hash: str | None = None
    role: AgentRole | None = None
    category_access: str | None = None
    permissions: str | None = None
    department_id: int | None = None
    is_active: bool | None = None
    phone: str | None = None
    avatar_path: str | None = None
    last_login_at: datetime | None = None


class AgentRead(AgentBase):
    id: int
    last_login_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)
    
    def _get_permissions_set(self) -> set[str]:
        """Получить набор прав агента."""
        if not self.permissions:
            return set()
        return set(p.strip() for p in self.permissions.split(",") if p.strip())
    
    def has_permission(self, permission: Permission) -> bool:
        """
        Проверить наличие права у агента.
        Администратор всегда имеет все права.
        """
        # Админ всегда имеет все права (сравниваем и со строкой, и с AgentRole)
        if self.role == AgentRole.admin or str(self.role) == "admin":
            return True
        return permission.value in self._get_permissions_set()
    
    def has_any_permission(self, *permissions: Permission) -> bool:
        """Проверить наличие хотя бы одного из указанных прав."""
        # Админ всегда имеет все права
        if self.role == AgentRole.admin or str(self.role) == "admin":
            return True
        user_perms = self._get_permissions_set()
        return any(p.value in user_perms for p in permissions)

    def has_all_permissions(self, *permissions: Permission) -> bool:
        """Проверить наличие всех указанных прав."""
        # Админ всегда имеет все права
        if self.role == AgentRole.admin or str(self.role) == "admin":
            return True
        user_perms = self._get_permissions_set()
        return all(p.value in user_perms for p in permissions)

    def get_permissions_dict(self) -> dict[str, bool]:
        """
        Вернуть dict {can_permission_name: bool} для всех прав.
        Используется для передачи в шаблоны.
        """
        # Админ всегда имеет все права (сравниваем и со строкой, и с AgentRole)
        is_admin = self.role == AgentRole.admin or str(self.role) == "admin"

        if is_admin:
            return {perm.value: True for perm in Permission}

        user_perms = self._get_permissions_set()
        return {perm.value: perm.value in user_perms for perm in Permission}
    
    @property
    def role_name(self) -> str:
        """Возвращает имя роли как строку."""
        if isinstance(self.role, AgentRole):
            return self.role.value
        return str(self.role)
