from pydantic import BaseModel, Field, ConfigDict, validator
from datetime import datetime
from typing import Optional, List, Any, Dict
from enum import Enum
import json

# Переиспользуем enum для Pydantic
class EventType(str, Enum):
    created = "created"
    replied = "replied"
    status_changed = "status_changed"
    priority_changed = "priority_changed"
    assigned = "assigned"
    unassigned = "unassigned"
    category_changed = "category_changed"
    merged = "merged"
    closed = "closed"
    reopened = "reopened"
    locked = "locked"
    unlocked = "unlocked"
    note_added = "note_added"
    attachment_added = "attachment_added"
    customer_replied = "customer_replied"
    
    # Дополнительные типы событий
    tag_added = "tag_added"
    tag_removed = "tag_removed"
    due_date_changed = "due_date_changed"
    escalated = "escalated"
    satisfaction_rated = "satisfaction_rated"

# Поля, которые могут изменяться (для типизации)
class EventField(str, Enum):
    STATUS = "status"
    PRIORITY = "priority"
    ASSIGNEE = "assignee"
    CATEGORY = "category"
    DEPARTMENT = "department"
    SUBJECT = "subject"
    DESCRIPTION = "description"
    DUE_DATE = "due_date"
    TAGS = "tags"
    SATISFACTION = "satisfaction"

# Базовые схемы
class TicketEventBase(BaseModel):
    """Базовые поля события"""
    action_type: EventType = Field(..., description="Тип события")
    field_name: Optional[str] = Field(None, max_length=100, description="Название измененного поля")
    old_value: Optional[str] = Field(None, description="Старое значение")
    new_value: Optional[str] = Field(None, description="Новое значение")
    comment: Optional[str] = Field(None, description="Комментарий к событию")
    
    # Дополнительные поля
    ip_address: Optional[str] = Field(None, max_length=45, description="IP адрес инициатора")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Дополнительные метаданные")
    is_system: bool = Field(False, description="Системное событие")
    
    @validator('metadata', pre=True)
    def validate_metadata(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except:
                return None
        return v

# Схема для создания события
class TicketEventCreate(TicketEventBase):
    """Создание нового события"""
    ticket_id: int = Field(..., gt=0, description="ID тикета")
    agent_id: Optional[int] = Field(None, gt=0, description="ID агента")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "ticket_id": 123,
                "agent_id": 5,
                "action_type": "status_changed",
                "field_name": "status",
                "old_value": "open",
                "new_value": "in_progress",
                "comment": "Агент начал обработку тикета",
                "ip_address": "192.168.1.100",
                "is_system": False
            }
        }
    )

# Схема для ответа
class TicketEventResponse(TicketEventBase):
    """Полная информация о событии"""
    id: int
    ticket_id: int
    agent_id: Optional[int] = None
    occurred_at: datetime
    
    # Связанные данные
    agent: Optional['AgentBrief'] = Field(None, description="Агент, выполнивший действие")
    
    # Форматированные поля
    formatted_change: Optional[str] = Field(None, description="Человекочитаемое описание изменения")
    time_ago: Optional[str] = Field(None, description="Время в человекочитаемом формате")
    
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": 1,
                "ticket_id": 123,
                "agent_id": 5,
                "action_type": "status_changed",
                "field_name": "status",
                "old_value": "open",
                "new_value": "in_progress",
                "comment": "Агент начал обработку тикета",
                "occurred_at": "2024-01-15T10:30:00Z",
                "agent": {
                    "id": 5,
                    "full_name": "Анна Сидорова",
                    "email": "anna@example.com"
                },
                "formatted_change": "Изменил статус с 'open' на 'in_progress'",
                "time_ago": "5 минут назад"
            }
        }
    )

# Краткая схема для события
class TicketEventBrief(BaseModel):
    """Краткая информация о событии"""
    id: int
    action_type: EventType
    occurred_at: datetime
    agent_name: Optional[str] = None
    description: str
    
    model_config = ConfigDict(from_attributes=True)

# Схема для фильтрации событий
class TicketEventFilter(BaseModel):
    """Параметры фильтрации событий"""
    ticket_id: Optional[int] = None
    agent_id: Optional[int] = None
    action_type: Optional[EventType] = None
    field_name: Optional[str] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    is_system: Optional[bool] = None
    search: Optional[str] = Field(None, description="Поиск по комментарию или значениям")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "ticket_id": 123,
                "action_type": "status_changed",
                "date_from": "2024-01-01T00:00:00Z",
                "date_to": "2024-01-31T23:59:59Z"
            }
        }
    )

# Схема для ленты событий
class TicketEventTimeline(BaseModel):
    """Лента событий тикета"""
    ticket_id: int
    events: List[TicketEventResponse]
    grouped_by_date: Dict[str, List[TicketEventResponse]]
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "ticket_id": 123,
                "events": [],
                "grouped_by_date": {
                    "2024-01-15": [],
                    "2024-01-14": []
                }
            }
        }
    )

# Схема для статистики событий
class EventStatistics(BaseModel):
    """Статистика по событиям"""
    total_events: int
    events_by_type: Dict[str, int]
    events_by_agent: Dict[str, int]
    events_by_hour: Dict[int, int]
    events_by_day: Dict[str, int]
    average_events_per_ticket: float
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "total_events": 1500,
                "events_by_type": {
                    "status_changed": 450,
                    "replied": 300,
                    "assigned": 200
                },
                "events_by_agent": {
                    "Анна Сидорова": 500,
                    "Иван Петров": 400
                },
                "events_by_hour": {
                    "9": 100,
                    "10": 150,
                    "11": 120
                },
                "events_by_day": {
                    "2024-01-15": 45,
                    "2024-01-16": 52
                },
                "average_events_per_ticket": 3.5
            }
        }
    )

# Схема для изменений значений
class ValueChange(BaseModel):
    """Модель изменения значения"""
    field: str
    old: Any
    new: Any
    
    @classmethod
    def from_event(cls, event: TicketEvent):
        return cls(
            field=event.field_name,
            old=event.old_value,
            new=event.new_value
        )

# Схема для сложных изменений
class ComplexEventCreate(BaseModel):
    """Создание сложного события с несколькими изменениями"""
    ticket_id: int
    agent_id: Optional[int] = None
    changes: List[ValueChange] = Field(..., min_length=1)
    comment: Optional[str] = None
    is_system: bool = False
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "ticket_id": 123,
                "agent_id": 5,
                "changes": [
                    {"field": "status", "old": "open", "new": "in_progress"},
                    {"field": "priority", "old": "medium", "new": "high"}
                ],
                "comment": "Повысил приоритет и начал обработку"
            }
        }
    )

# Схема для экспорта событий
class EventExport(BaseModel):
    """Параметры экспорта событий"""
    format: str = Field(..., pattern="^(csv|xlsx|json|pdf)$")
    filters: Optional[TicketEventFilter] = None
    include_agent_details: bool = Field(True)
    date_range: Optional[tuple[datetime, datetime]] = None

# Схема для аналитики времени ответа
class ResponseTimeAnalytics(BaseModel):
    """Аналитика времени ответа"""
    ticket_id: int
    created_at: datetime
    first_response_at: Optional[datetime] = None
    first_response_time_minutes: Optional[float] = None
    resolution_time_minutes: Optional[float] = None
    status_changes_count: int = 0
    reassignments_count: int = 0
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "ticket_id": 123,
                "created_at": "2024-01-15T08:00:00Z",
                "first_response_at": "2024-01-15T09:30:00Z",
                "first_response_time_minutes": 90,
                "resolution_time_minutes": 360,
                "status_changes_count": 3,
                "reassignments_count": 1
            }
        }
    )

# Схема для уведомлений на основе событий
class EventNotification(BaseModel):
    """Уведомление на основе события"""
    event_id: int
    notification_type: str
    recipients: List[str]
    message: str
    sent_at: datetime
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "event_id": 1,
                "notification_type": "email",
                "recipients": ["agent@example.com"],
                "message": "Тикет #123 был изменен",
                "sent_at": "2024-01-15T10:30:00Z"
            }
        }
    )

# Схема для построения графа событий
class EventGraph(BaseModel):
    """Графовая структура событий"""
    nodes: List[dict] = Field(..., description="Узлы графа (события)")
    edges: List[dict] = Field(..., description="Связи между событиями")
    timeline: List[datetime] = Field(..., description="Временная шкала")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "nodes": [
                    {"id": 1, "type": "created", "timestamp": "2024-01-15T08:00:00Z"},
                    {"id": 2, "type": "assigned", "timestamp": "2024-01-15T08:30:00Z"}
                ],
                "edges": [
                    {"from": 1, "to": 2, "relationship": "next"}
                ],
                "timeline": ["2024-01-15T08:00:00Z", "2024-01-15T08:30:00Z"]
            }
        }
    )

# Схема для шаблона события (для автоматического логирования)
class EventTemplate(BaseModel):
    """Шаблон для автоматического создания событий"""
    action_type: EventType
    message_template: str
    requires_comment: bool = False
    auto_create: bool = True
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "action_type": "status_changed",
                "message_template": "Статус изменен с {old} на {new}",
                "requires_comment": False,
                "auto_create": True
            }
        }
    )