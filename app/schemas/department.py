from pydantic import BaseModel, Field, ConfigDict, EmailStr, validator
from datetime import datetime
from typing import Optional, List
from enum import Enum

# Базовые схемы
class DepartmentBase(BaseModel):
    """Базовые поля отдела"""
    name: str = Field(..., min_length=1, max_length=150, description="Название отдела")
    description: Optional[str] = Field(None, max_length=5000, description="Описание отдела")
    email: Optional[EmailStr] = Field(None, max_length=255, description="Email отдела")
    is_active: bool = Field(default=True, description="Активен ли отдел")
    sort_order: int = Field(default=0, ge=0, description="Порядок сортировки (меньше = выше)")
    
    @validator('name')
    def validate_name(cls, v):
        if not v.strip():
            raise ValueError('Название не может быть пустым')
        return v.strip()

# Схема для создания отдела
class DepartmentCreate(DepartmentBase):
    """Создание нового отдела"""
    # Опционально: можно добавить head_agent_id
    head_agent_id: Optional[int] = Field(None, gt=0, description="ID руководителя отдела")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "Техническая поддержка",
                "description": "Отдел технической поддержки первого уровня",
                "email": "support@example.com",
                "is_active": True,
                "sort_order": 10,
                "head_agent_id": 5
            }
        }
    )

# Схема для обновления отдела
class DepartmentUpdate(BaseModel):
    """Обновление данных отдела (все поля опциональны)"""
    name: Optional[str] = Field(None, min_length=1, max_length=150)
    description: Optional[str] = Field(None, max_length=5000)
    email: Optional[EmailStr] = Field(None, max_length=255)
    is_active: Optional[bool] = None
    sort_order: Optional[int] = Field(None, ge=0)
    head_agent_id: Optional[int] = Field(None, gt=0)
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "Техническая поддержка (2-й уровень)",
                "sort_order": 5,
                "is_active": True
            }
        }
    )

# Краткая схема для отдела (для вложенных ответов)
class DepartmentBrief(BaseModel):
    """Краткая информация об отделе"""
    id: int
    name: str
    email: Optional[str] = None
    is_active: bool
    sort_order: int
    
    model_config = ConfigDict(from_attributes=True)

# Полная схема для ответа
class DepartmentResponse(DepartmentBase):
    """Полная информация об отделе"""
    id: int
    created_at: datetime
    updated_at: datetime
    
    # Опционально: статистика и связанные данные
    agents_count: Optional[int] = Field(None, description="Количество агентов в отделе")
    tickets_count: Optional[int] = Field(None, description="Количество тикетов в отделе")
    categories_count: Optional[int] = Field(None, description="Количество категорий")
    
    # Связанные данные (если нужны)
    head_agent: Optional['AgentBrief'] = Field(None, description="Руководитель отдела")
    agents: Optional[List['AgentBrief']] = Field(None, description="Список агентов")
    
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": 1,
                "name": "Техническая поддержка",
                "description": "Отдел технической поддержки первого уровня",
                "email": "support@example.com",
                "is_active": True,
                "sort_order": 10,
                "created_at": "2024-01-01T08:00:00Z",
                "updated_at": "2024-01-15T10:30:00Z",
                "agents_count": 15,
                "tickets_count": 234,
                "categories_count": 5
            }
        }
    )

# Схема для списка отделов с иерархией
class DepartmentHierarchy(DepartmentBrief):
    """Отдел с иерархией подотделов"""
    children: List['DepartmentHierarchy'] = Field(default_factory=list, description="Дочерние отделы")
    level: int = Field(0, description="Уровень вложенности")
    
    model_config = ConfigDict(from_attributes=True)

# Схема для фильтрации отделов
class DepartmentFilter(BaseModel):
    """Параметры фильтрации отделов"""
    is_active: Optional[bool] = None
    search: Optional[str] = Field(None, description="Поиск по названию или описанию")
    has_agents: Optional[bool] = Field(None, description="Отделы с агентами")
    has_tickets: Optional[bool] = Field(None, description="Отделы с тикетами")
    sort_by: Optional[str] = Field("sort_order", description="Поле для сортировки")
    sort_desc: bool = Field(False, description="Обратный порядок")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "is_active": True,
                "search": "поддержка",
                "has_agents": True,
                "sort_by": "name",
                "sort_desc": False
            }
        }
    )

# Схема для массового обновления
class DepartmentBulkUpdate(BaseModel):
    """Массовое обновление отделов"""
    department_ids: List[int] = Field(..., min_length=1)
    is_active: Optional[bool] = None
    sort_order_increment: Optional[int] = Field(None, description="Увеличить sort_order на значение")

# Схема для переупорядочивания отделов
class DepartmentReorder(BaseModel):
    """Переупорядочивание списка отделов"""
    department_orders: List[dict] = Field(..., description="Список {id: sort_order}")
    
    @validator('department_orders')
    def validate_orders(cls, v):
        if not v:
            raise ValueError('Список не может быть пустым')
        for item in v:
            if 'id' not in item or 'sort_order' not in item:
                raise ValueError('Каждый элемент должен содержать id и sort_order')
        return v
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "department_orders": [
                    {"id": 1, "sort_order": 10},
                    {"id": 2, "sort_order": 20},
                    {"id": 3, "sort_order": 30}
                ]
            }
        }
    )

# Схема для аналитики по отделам
class DepartmentAnalytics(BaseModel):
    """Аналитика по отделу"""
    department: DepartmentBrief
    stats: dict = Field(..., description="Статистика отдела")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "department": {
                    "id": 1,
                    "name": "Техническая поддержка",
                    "email": "support@example.com",
                    "is_active": True,
                    "sort_order": 10
                },
                "stats": {
                    "total_agents": 15,
                    "active_agents": 12,
                    "total_tickets": 234,
                    "open_tickets": 45,
                    "resolved_tickets": 180,
                    "avg_response_time": "2.5 hours",
                    "avg_resolution_time": "24 hours",
                    "satisfaction_rate": 4.5
                }
            }
        }
    )

# Схема для экспорта отделов
class DepartmentExport(BaseModel):
    """Параметры экспорта отделов"""
    format: str = Field(..., pattern="^(csv|xlsx|json)$")
    fields: Optional[List[str]] = Field(None, description="Список полей для экспорта")
    filters: Optional[DepartmentFilter] = None
    include_agents: bool = Field(False, description="Включить список агентов")
    include_tickets: bool = Field(False, description="Включить статистику по тикетам")

# Схема для создания отдела с иерархией
class DepartmentCreateHierarchy(DepartmentCreate):
    """Создание отдела с иерархией"""
    parent_id: Optional[int] = Field(None, gt=0, description="ID родительского отдела")
    
    @validator('parent_id')
    def prevent_self_parent(cls, v, values):
        if v and 'id' in values and v == values['id']:
            raise ValueError('Отдел не может быть родителем самого себя')
        return v

# Расширенная схема для ответа с иерархией
class DepartmentWithHierarchy(DepartmentResponse):
    """Отдел с иерархией и полной информацией"""
    parent_id: Optional[int] = None
    parent: Optional['DepartmentBrief'] = None
    children: List['DepartmentBrief'] = Field(default_factory=list)
    path: str = Field("", description="Путь в иерархии (например: /IT/Support)")

# Схема для валидации email отдела
class DepartmentEmailCheck(BaseModel):
    """Проверка email отдела"""
    email: EmailStr
    exclude_id: Optional[int] = Field(None, description="ID отдела для исключения при проверке")

# Схема для перемещения агентов между отделами
class DepartmentMoveAgents(BaseModel):
    """Перемещение агентов между отделами"""
    agent_ids: List[int] = Field(..., min_length=1)
    from_department_id: Optional[int] = Field(None, description="Исходный отдел (опционально)")
    to_department_id: int = Field(..., gt=0, description="Целевой отдел")

# Схема для ответа с ошибками валидации
class DepartmentValidationError(BaseModel):
    """Ошибка валидации отдела"""
    field: str
    message: str
    value: Optional[any] = None