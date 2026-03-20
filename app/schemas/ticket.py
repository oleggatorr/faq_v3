from pydantic import BaseModel, Field, ConfigDict, EmailStr, validator
from datetime import datetime
from typing import Optional, List, Any
from enum import Enum

# Перечисление для приоритета
class Priority(str, Enum):
    low = "low"
    normal = "normal"
    high = "high"
    urgent = "urgent"
    
    def get_color(self) -> str:
        colors = {
            "low": "#2ecc71",
            "normal": "#3498db",
            "high": "#e67e22",
            "urgent": "#e74c3c"
        }
        return colors[self.value]

# Базовые схемы
class TicketBase(BaseModel):
    """Базовые поля тикета"""
    customer_name: str = Field(..., min_length=1, max_length=200, description="Имя клиента")
    customer_email: EmailStr = Field(..., max_length=255, description="Email клиента")
    subject: str = Field(..., min_length=1, max_length=255, description="Тема тикета")
    preview_message: Optional[str] = Field(None, description="Предпросмотр сообщения")
    
    # Основные параметры
    department_id: int = Field(..., gt=0, description="ID отдела")
    status_id: int = Field(1, gt=0, description="ID статуса")
    priority: Priority = Field(Priority.normal, description="Приоритет")
    
    # Опциональные связи
    language_id: Optional[int] = Field(None, gt=0, description="ID языка")
    category_id: Optional[int] = Field(None, gt=0, description="ID категории")
    owner_id: Optional[int] = Field(None, gt=0, description="ID ответственного агента")
    
    @validator('customer_name')
    def validate_customer_name(cls, v):
        if not v.strip():
            raise ValueError('Имя клиента не может быть пустым')
        return v.strip()

# Схема для создания тикета
class TicketCreate(TicketBase):
    """Создание нового тикета"""
    customer_ip: str = Field(..., max_length=45, description="IP адрес клиента")
    message_body: str = Field(..., min_length=1, description="Текст первого сообщения")
    attachment_ids: Optional[List[int]] = Field(None, description="ID вложений")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "customer_name": "Иван Петров",
                "customer_email": "ivan@example.com",
                "customer_ip": "192.168.1.100",
                "subject": "Проблема с доступом",
                "message_body": "Не могу войти в систему, пишет 'неверный пароль'",
                "department_id": 1,
                "priority": "high",
                "language_id": 1,
                "category_id": 2,
                "attachment_ids": [1, 2]
            }
        }
    )

# Схема для обновления тикета
class TicketUpdate(BaseModel):
    """Обновление данных тикета"""
    subject: Optional[str] = Field(None, min_length=1, max_length=255)
    department_id: Optional[int] = Field(None, gt=0)
    category_id: Optional[int] = Field(None, gt=0)
    status_id: Optional[int] = Field(None, gt=0)
    priority: Optional[Priority] = None
    owner_id: Optional[int] = Field(None, gt=0)
    is_locked: Optional[bool] = None
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "priority": "urgent",
                "owner_id": 5,
                "status_id": 2
            }
        }
    )

# Краткая схема для тикета (для списков)
class TicketBrief(BaseModel):
    """Краткая информация о тикете"""
    id: int
    track_id: str
    subject: str
    customer_name: str
    priority: Priority
    status: 'TicketStatusBrief'
    created_at: datetime
    messages_count: int
    
    model_config = ConfigDict(from_attributes=True)

# Полная схема для ответа
class TicketResponse(TicketBase):
    """Полная информация о тикете"""
    id: int
    track_id: str
    customer_ip: str
    
    # Временные метки
    created_at: datetime
    updated_at: datetime
    first_responded_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None
    
    # Счетчики
    messages_count: int
    attachments_count: int
    
    # Флаги
    is_archived: bool
    is_locked: bool
    merged_into_id: Optional[int] = None
    
    # Агенты
    owner_id: Optional[int] = None
    opened_by_id: Optional[int] = None
    closed_by_id: Optional[int] = None
    
    # Связанные данные (опционально)
    department: Optional['DepartmentBrief'] = None
    language: Optional['LanguageBrief'] = None
    category: Optional['QuestionCategoryBrief'] = None
    status: Optional['TicketStatusBrief'] = None
    owner: Optional['AgentBrief'] = None
    opened_by: Optional['AgentBrief'] = None
    closed_by: Optional['AgentBrief'] = None
    
    # Последнее сообщение
    last_message: Optional['MessageBrief'] = None
    
    # Статистика
    time_to_first_response_hours: Optional[float] = Field(None, description="Время до первого ответа (часы)")
    time_to_resolution_hours: Optional[float] = Field(None, description="Время до закрытия (часы)")
    
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": 123,
                "track_id": "TKT-2024-00123",
                "customer_name": "Иван Петров",
                "customer_email": "ivan@example.com",
                "customer_ip": "192.168.1.100",
                "subject": "Проблема с доступом",
                "department_id": 1,
                "status_id": 2,
                "priority": "high",
                "created_at": "2024-01-15T10:30:00Z",
                "updated_at": "2024-01-15T11:45:00Z",
                "messages_count": 3,
                "attachments_count": 1,
                "is_archived": False,
                "is_locked": False,
                "time_to_first_response_hours": 1.25,
                "status": {
                    "id": 2,
                    "name": "В работе",
                    "color": "#3498db"
                }
            }
        }
    )

# Схема для фильтрации тикетов
class TicketFilter(BaseModel):
    """Параметры фильтрации тикетов"""
    track_id: Optional[str] = None
    customer_email: Optional[EmailStr] = None
    customer_name: Optional[str] = None
    
    department_id: Optional[int] = None
    category_id: Optional[int] = None
    status_id: Optional[int] = None
    priority: Optional[Priority] = None
    language_id: Optional[int] = None
    
    owner_id: Optional[int] = None
    opened_by_id: Optional[int] = None
    
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    created_from: Optional[datetime] = None
    created_to: Optional[datetime] = None
    closed_from: Optional[datetime] = None
    closed_to: Optional[datetime] = None
    
    is_archived: Optional[bool] = False
    is_locked: Optional[bool] = None
    has_owner: Optional[bool] = None
    
    search: Optional[str] = Field(None, description="Поиск по теме, имени, email")
    
    sort_by: Optional[str] = Field("created_at", description="Поле для сортировки")
    sort_desc: bool = Field(True, description="Обратный порядок")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "status_id": 2,
                "priority": "high",
                "date_from": "2024-01-01T00:00:00Z",
                "date_to": "2024-01-31T23:59:59Z",
                "search": "доступ"
            }
        }
    )

# Схема для ответа со списком тикетов и пагинацией
class TicketListResponse(BaseModel):
    """Список тикетов с пагинацией"""
    items: List[TicketResponse]
    total: int
    page: int
    per_page: int
    has_next: bool
    has_prev: bool
    
    # Дополнительная статистика
    stats: Optional[dict] = None
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "items": [],
                "total": 150,
                "page": 1,
                "per_page": 20,
                "has_next": True,
                "has_prev": False
            }
        }
    )

# Схема для назначения тикета
class TicketAssign(BaseModel):
    """Назначение тикета агенту"""
    ticket_id: int
    agent_id: int
    comment: Optional[str] = None
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "ticket_id": 123,
                "agent_id": 5,
                "comment": "Назначаю на Анну как эксперта по этой категории"
            }
        }
    )

# Схема для объединения тикетов
class TicketMerge(BaseModel):
    """Объединение тикетов"""
    master_ticket_id: int = Field(..., description="Главный тикет")
    merged_ticket_ids: List[int] = Field(..., min_length=1, description="Тикеты для объединения")
    comment: Optional[str] = None
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "master_ticket_id": 123,
                "merged_ticket_ids": [124, 125],
                "comment": "Дубликаты, объединяю с основным тикетом"
            }
        }
    )

# Схема для массовых операций
class TicketBulkAction(BaseModel):
    """Массовая операция с тикетами"""
    ticket_ids: List[int] = Field(..., min_length=1, max_length=100)
    action: str = Field(..., pattern="^(assign|close|archive|lock|change_status)$")
    
    # Параметры для конкретных действий
    assign_agent_id: Optional[int] = None
    new_status_id: Optional[int] = None
    comment: Optional[str] = None

# Схема для статистики по тикетам
class TicketStatistics(BaseModel):
    """Статистика по тикетам"""
    total_tickets: int
    tickets_by_status: Dict[str, int]
    tickets_by_priority: Dict[str, int]
    tickets_by_department: Dict[str, int]
    tickets_by_category: Dict[str, int]
    
    tickets_created_today: int
    tickets_created_this_week: int
    tickets_created_this_month: int
    
    tickets_closed_today: int
    tickets_closed_this_week: int
    tickets_closed_this_month: int
    
    average_resolution_time_hours: float
    average_first_response_time_hours: float
    
    # SLA метрики
    sla_breaches: int = 0
    sla_compliance_rate: float = 100.0
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "total_tickets": 1250,
                "tickets_by_status": {
                    "new": 45,
                    "in_progress": 67,
                    "resolved": 112,
                    "closed": 1026
                },
                "tickets_by_priority": {
                    "low": 450,
                    "normal": 600,
                    "high": 150,
                    "urgent": 50
                },
                "average_resolution_time_hours": 24.5,
                "average_first_response_time_hours": 2.3
            }
        }
    )

# Схема для экспорта тикетов
class TicketExport(BaseModel):
    """Параметры экспорта тикетов"""
    format: str = Field(..., pattern="^(csv|xlsx|json|pdf)$")
    filters: Optional[TicketFilter] = None
    fields: Optional[List[str]] = None
    include_messages: bool = Field(False)
    include_attachments: bool = Field(False)
    include_events: bool = Field(False)
    date_range: Optional[tuple[datetime, datetime]] = None

# Схема для импорта тикетов
class TicketImport(BaseModel):
    """Импорт тикетов из внешнего источника"""
    source: str = Field(..., description="Источник импорта")
    data: List[dict] = Field(..., description="Данные для импорта")
    create_missing_customers: bool = Field(True)
    skip_duplicates: bool = Field(True)

# Схема для SLA политики
class SLAPolicy(BaseModel):
    """SLA политика для тикетов"""
    priority: Priority
    first_response_time_hours: int = Field(..., gt=0)
    resolution_time_hours: int = Field(..., gt=0)
    escalation_time_hours: Optional[int] = None
    escalation_status_id: Optional[int] = None
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "priority": "urgent",
                "first_response_time_hours": 1,
                "resolution_time_hours": 4,
                "escalation_time_hours": 2,
                "escalation_status_id": 3
            }
        }
    )

# Схема для проверки SLA
class SLACheck(BaseModel):
    """Проверка SLA для тикета"""
    ticket_id: int
    first_response_deadline: Optional[datetime] = None
    resolution_deadline: Optional[datetime] = None
    is_breached: bool = False
    breach_reason: Optional[str] = None
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "ticket_id": 123,
                "first_response_deadline": "2024-01-15T11:30:00Z",
                "resolution_deadline": "2024-01-15T14:30:00Z",
                "is_breached": False
            }
        }
    )

# Схема для уведомлений
class TicketNotification(BaseModel):
    """Уведомление по тикету"""
    ticket_id: int
    notification_type: str = Field(..., pattern="^(created|updated|assigned|resolved|closed)$")
    recipients: List[str] = Field(..., description="Email получателей")
    subject: str
    message: str
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "ticket_id": 123,
                "notification_type": "assigned",
                "recipients": ["agent@example.com"],
                "subject": "Назначен новый тикет",
                "message": "Вам назначен тикет #TKT-2024-00123"
            }
        }
    )

# Схема для аналитики по времени
class TimeAnalytics(BaseModel):
    """Аналитика времени по тикетам"""
    ticket_id: int
    created_at: datetime
    first_response_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None
    
    wait_time_minutes: Optional[float] = None
    response_time_minutes: Optional[float] = None
    resolution_time_minutes: Optional[float] = None
    total_lifetime_minutes: Optional[float] = None
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "ticket_id": 123,
                "created_at": "2024-01-15T08:00:00Z",
                "first_response_at": "2024-01-15T09:30:00Z",
                "resolved_at": "2024-01-15T14:00:00Z",
                "closed_at": "2024-01-15T15:00:00Z",
                "wait_time_minutes": 90,
                "response_time_minutes": 270,
                "resolution_time_minutes": 360,
                "total_lifetime_minutes": 420
            }
        }
    )