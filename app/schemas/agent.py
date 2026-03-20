from pydantic import BaseModel, EmailStr, Field, ConfigDict
from datetime import datetime
from typing import Optional
from enum import Enum

# Переиспользуем enum для Pydantic
class AgentRole(str, Enum):
    admin = "admin"
    operator = "operator"
    readonly = "readonly"

# Базовые схемы
class AgentBase(BaseModel):
    """Базовые поля агента"""
    full_name: str = Field(..., min_length=1, max_length=200, description="Полное имя")
    email: EmailStr = Field(..., max_length=255, description="Email адрес")
    role: AgentRole = Field(default=AgentRole.operator, description="Роль агента")
    department_id: Optional[int] = Field(None, description="ID отдела")
    is_active: bool = Field(default=True, description="Активен ли агент")
    phone: Optional[str] = Field(None, max_length=50, description="Телефон")
    avatar_path: Optional[str] = Field(None, max_length=500, description="Путь к аватару")

# Схема для создания агента
class AgentCreate(AgentBase):
    """Создание нового агента"""
    password: str = Field(..., min_length=8, max_length=100, description="Пароль")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "full_name": "Иван Петров",
                "email": "ivan.petrov@example.com",
                "password": "secure_password123",
                "role": "operator",
                "department_id": 1,
                "phone": "+7 (999) 123-45-67"
            }
        }
    )

# Схема для обновления агента
class AgentUpdate(BaseModel):
    """Обновление данных агента (все поля опциональны)"""
    full_name: Optional[str] = Field(None, min_length=1, max_length=200)
    email: Optional[EmailStr] = Field(None, max_length=255)
    password: Optional[str] = Field(None, min_length=8, max_length=100)
    role: Optional[AgentRole] = None
    department_id: Optional[int] = Field(None)
    is_active: Optional[bool] = None
    phone: Optional[str] = Field(None, max_length=50)
    avatar_path: Optional[str] = Field(None, max_length=500)
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "full_name": "Иван Сидоров",
                "phone": "+7 (999) 765-43-21",
                "is_active": False
            }
        }
    )

# Схема для смены пароля
class AgentChangePassword(BaseModel):
    """Смена пароля"""
    current_password: str = Field(..., min_length=8, max_length=100)
    new_password: str = Field(..., min_length=8, max_length=100)
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "current_password": "old_password",
                "new_password": "new_secure_password"
            }
        }
    )

# Основная схема для ответа (чтение)
class AgentResponse(AgentBase):
    """Полная информация об агенте (для ответа API)"""
    id: int
    last_login_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    
    # Опционально: если нужно включать связанные данные
    # department: Optional['DepartmentResponse'] = None
    
    model_config = ConfigDict(
        from_attributes=True,  # В Pydantic v2 вместо orm_mode
        json_schema_extra={
            "example": {
                "id": 1,
                "full_name": "Иван Петров",
                "email": "ivan.petrov@example.com",
                "role": "operator",
                "department_id": 1,
                "is_active": True,
                "phone": "+7 (999) 123-45-67",
                "avatar_path": "/uploads/avatars/avatar_1.jpg",
                "last_login_at": "2024-01-15T10:30:00Z",
                "created_at": "2024-01-01T08:00:00Z",
                "updated_at": "2024-01-15T10:30:00Z"
            }
        }
    )

# Краткая схема для списков (без детальной информации)
class AgentBrief(BaseModel):
    """Краткая информация об агенте (для вложенных ответов)"""
    id: int
    full_name: str
    email: EmailStr
    role: AgentRole
    avatar_path: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)

# Схема для аутентификации
class AgentLogin(BaseModel):
    """Логин агента"""
    email: EmailStr
    password: str = Field(..., min_length=1)
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "email": "ivan.petrov@example.com",
                "password": "secure_password123"
            }
        }
    )

# Схема с токеном
class AgentToken(BaseModel):
    """Токен доступа"""
    access_token: str
    token_type: str = "bearer"
    agent: AgentBrief  # Возвращаем краткую информацию об агенте

# Схема для фильтрации списка агентов
class AgentFilter(BaseModel):
    """Параметры фильтрации агентов"""
    role: Optional[AgentRole] = None
    department_id: Optional[int] = None
    is_active: Optional[bool] = None
    search: Optional[str] = Field(None, description="Поиск по имени или email")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "role": "operator",
                "department_id": 1,
                "is_active": True,
                "search": "Иван"
            }
        }
    )

# Если нужно циклическое импортирование для department
# from typing import TYPE_CHECKING
# if TYPE_CHECKING:
#     from .department import DepartmentResponse
# else:
#     DepartmentResponse = Any

# Обновляем AgentResponse с department если нужно
# AgentResponse.model_config = ConfigDict(from_attributes=True)
# AgentResponse.model_rebuild()