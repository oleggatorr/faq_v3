from pydantic import BaseModel, Field, ConfigDict, validator
from datetime import datetime
from typing import Optional, List
import re

# Перечисление для категорий статусов
class StatusCategory(str, Enum):
    NEW = "new"
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    PENDING = "pending"
    RESOLVED = "resolved"
    CLOSED = "closed"
    CANCELLED = "cancelled"
    ON_HOLD = "on_hold"
    ESCALATED = "escalated"

# Базовые схемы
class TicketStatusBase(BaseModel):
    """Базовые поля статуса"""
    code: str = Field(..., min_length=2, max_length=50, 
                      pattern=r'^[a-z][a-z0-9_]*$',
                      description="Уникальный код статуса (латиница, цифры, подчеркивание)")
    name: str = Field(..., min_length=1, max_length=100, description="Название статуса")
    color: str = Field('#999999', description="Цвет статуса (HEX, RGB, или название)")
    is_closed: bool = Field(False, description="Является ли статус закрывающим")
    is_default: bool = Field(False, description="Статус по умолчанию для новых тикетов")
    sort_order: int = Field(default=0, ge=0, description="Порядок сортировки")
    
    # Дополнительные поля
    category: Optional[StatusCategory] = Field(None, description="Категория статуса")
    description: Optional[str] = Field(None, max_length=500, description="Описание статуса")
    requires_comment: bool = Field(False, description="Требуется комментарий при переходе")
    transition_timeout_hours: Optional[int] = Field(None, ge=0, description="Автоматический переход через N часов")
    next_status_id: Optional[int] = Field(None, description="Следующий статус в workflow")
    
    @validator('code')
    def validate_code(cls, v):
        if not re.match(r'^[a-z][a-z0-9_]*$', v):
            raise ValueError('Код должен начинаться с буквы и содержать только латиницу, цифры и подчеркивание')
        return v
    
    @validator('color')
    def validate_color(cls, v):
        # Поддерживаем HEX, RGB и базовые названия цветов
        if not (re.match(r'^#[0-9a-fA-F]{6}$', v) or 
                re.match(r'^rgb\((\d{1,3},\s*){2}\d{1,3}\)$', v) or
                v in ['red', 'green', 'blue', 'yellow', 'orange', 'purple', 'gray', 'black']):
            raise ValueError('Цвет должен быть в формате HEX (#RRGGBB), RGB или базовым названием')
        return v

# Схема для создания статуса
class TicketStatusCreate(TicketStatusBase):
    """Создание нового статуса"""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "code": "in_progress",
                "name": "В работе",
                "color": "#3498db",
                "is_closed": False,
                "is_default": False,
                "sort_order": 20,
                "category": "in_progress",
                "description": "Тикет находится в процессе обработки",
                "requires_comment": False,
                "transition_timeout_hours": None,
                "next_status_id": 4
            }
        }
    )

# Схема для обновления статуса
class TicketStatusUpdate(BaseModel):
    """Обновление статуса (все поля опциональны)"""
    code: Optional[str] = Field(None, min_length=2, max_length=50, 
                                pattern=r'^[a-z][a-z0-9_]*$')
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    color: Optional[str] = None
    is_closed: Optional[bool] = None
    is_default: Optional[bool] = None
    sort_order: Optional[int] = Field(None, ge=0)
    category: Optional[StatusCategory] = None
    description: Optional[str] = Field(None, max_length=500)
    requires_comment: Optional[bool] = None
    transition_timeout_hours: Optional[int] = Field(None, ge=0)
    next_status_id: Optional[int] = None
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "Активно",
                "color": "#e67e22",
                "sort_order": 15
            }
        }
    )

# Краткая схема для статуса (для вложенных ответов)
class TicketStatusBrief(BaseModel):
    """Краткая информация о статусе"""
    id: int
    code: str
    name: str
    color: str
    is_closed: bool
    
    model_config = ConfigDict(from_attributes=True)

# Полная схема для ответа
class TicketStatusResponse(TicketStatusBase):
    """Полная информация о статусе"""
    id: int
    
    # Статистика использования
    tickets_count: Optional[int] = Field(None, description="Количество тикетов в этом статусе")
    is_used: bool = Field(False, description="Используется ли статус в тикетах")
    
    # Связанные данные
    next_status: Optional['TicketStatusBrief'] = Field(None, description="Следующий статус")
    previous_statuses: List['TicketStatusBrief'] = Field(default_factory=list, description="Предыдущие статусы")
    
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": 1,
                "code": "new",
                "name": "Новый",
                "color": "#95a5a6",
                "is_closed": False,
                "is_default": True,
                "sort_order": 10,
                "category": "new",
                "description": "Только что созданный тикет",
                "requires_comment": False,
                "transition_timeout_hours": None,
                "next_status_id": 2,
                "tickets_count": 45,
                "is_used": True,
                "next_status": {
                    "id": 2,
                    "code": "in_progress",
                    "name": "В работе",
                    "color": "#3498db",
                    "is_closed": False
                }
            }
        }
    )

# Схема для перехода между статусами
class StatusTransition(BaseModel):
    """Переход между статусами"""
    from_status_id: int
    to_status_id: int
    transition_name: Optional[str] = None
    requires_permission: bool = True
    requires_comment: bool = False
    allowed_roles: List[str] = Field(default_factory=list)
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "from_status_id": 1,
                "to_status_id": 2,
                "transition_name": "Начать обработку",
                "requires_permission": True,
                "requires_comment": False,
                "allowed_roles": ["operator", "admin"]
            }
        }
    )

# Схема для изменения статуса тикета
class TicketStatusChange(BaseModel):
    """Изменение статуса тикета"""
    ticket_id: int
    status_id: int
    comment: Optional[str] = Field(None, description="Комментарий к изменению статуса")
    notify_customer: bool = Field(True, description="Уведомить клиента")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "ticket_id": 123,
                "status_id": 2,
                "comment": "Начинаю обработку тикета",
                "notify_customer": True
            }
        }
    )

# Схема для фильтрации статусов
class TicketStatusFilter(BaseModel):
    """Параметры фильтрации статусов"""
    is_closed: Optional[bool] = None
    is_default: Optional[bool] = None
    category: Optional[StatusCategory] = None
    search: Optional[str] = Field(None, description="Поиск по коду или названию")
    has_tickets: Optional[bool] = Field(None, description="Статусы с тикетами")
    sort_by: Optional[str] = Field("sort_order", description="Поле для сортировки")
    sort_desc: bool = Field(False, description="Обратный порядок")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "is_closed": False,
                "category": "in_progress",
                "search": "работа",
                "has_tickets": True
            }
        }
    )

# Схема для workflow статусов
class StatusWorkflow(BaseModel):
    """Workflow статусов"""
    statuses: List[TicketStatusResponse]
    transitions: List[StatusTransition]
    initial_status: TicketStatusBrief
    final_statuses: List[TicketStatusBrief]
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "statuses": [],
                "transitions": [],
                "initial_status": {"id": 1, "code": "new", "name": "Новый", "color": "#95a5a6"},
                "final_statuses": [
                    {"id": 4, "code": "closed", "name": "Закрыт", "color": "#2ecc71"}
                ]
            }
        }
    )

# Схема для статистики по статусам
class StatusStatistics(BaseModel):
    """Статистика по статусам"""
    status: TicketStatusBrief
    tickets_count: int
    average_time_in_status_hours: Optional[float] = None
    percentage_of_total: float
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "status": {
                    "id": 1,
                    "code": "new",
                    "name": "Новый",
                    "color": "#95a5a6",
                    "is_closed": False
                },
                "tickets_count": 45,
                "average_time_in_status_hours": 2.5,
                "percentage_of_total": 15.5
            }
        }
    )

# Схема для массового обновления статусов
class StatusBulkUpdate(BaseModel):
    """Массовое обновление статусов"""
    status_ids: List[int] = Field(..., min_length=1)
    is_closed: Optional[bool] = None
    sort_order_increment: Optional[int] = Field(None, description="Увеличить sort_order на значение")
    category: Optional[StatusCategory] = None

# Схема для импорта статусов
class StatusImport(BaseModel):
    """Импорт статусов"""
    data: List[dict] = Field(..., description="Данные для импорта")
    replace_existing: bool = Field(False, description="Заменять существующие статусы")
    validate_only: bool = Field(False, description="Только валидация без сохранения")

# Схема для экспорта статусов
class StatusExport(BaseModel):
    """Параметры экспорта статусов"""
    format: str = Field(..., pattern="^(csv|xlsx|json)$")
    include_statistics: bool = Field(True, description="Включить статистику")
    include_transitions: bool = Field(True, description="Включить правила переходов")
    filters: Optional[TicketStatusFilter] = None

# Схема для автоматического перехода статуса
class AutoStatusTransition(BaseModel):
    """Автоматический переход статуса по времени"""
    status_id: int
    timeout_hours: int
    next_status_id: int
    is_active: bool = True
    last_executed_at: Optional[datetime] = None
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "status_id": 3,
                "timeout_hours": 24,
                "next_status_id": 4,
                "is_active": True
            }
        }
    )

# Схема для валидации перехода
class TransitionValidation(BaseModel):
    """Результат валидации перехода"""
    is_allowed: bool
    message: str
    requires_comment: bool = False
    required_permissions: List[str] = Field(default_factory=list)
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "is_allowed": True,
                "message": "Переход разрешен",
                "requires_comment": False,
                "required_permissions": []
            }
        }
    )

# Схема для матрицы переходов
class TransitionMatrix(BaseModel):
    """Матрица переходов между статусами"""
    matrix: List[List[bool]] = Field(..., description="Матрица разрешенных переходов")
    statuses: List[TicketStatusBrief]
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "matrix": [
                    [False, True, True, False],
                    [False, False, True, False],
                    [False, False, False, True],
                    [False, False, False, False]
                ],
                "statuses": [
                    {"id": 1, "name": "Новый"},
                    {"id": 2, "name": "В работе"},
                    {"id": 3, "name": "Решен"},
                    {"id": 4, "name": "Закрыт"}
                ]
            }
        }
    )