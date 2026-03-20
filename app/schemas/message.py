from pydantic import BaseModel, Field, ConfigDict, EmailStr, validator
from datetime import datetime
from typing import Optional, List
from enum import Enum
import re

# Перечисление для типа сообщения
class MessageType(str, Enum):
    EMAIL = "email"
    CHAT = "chat"
    PHONE = "phone"
    API = "api"
    SYSTEM = "system"

# Перечисление для статуса отправки
class MessageStatus(str, Enum):
    DRAFT = "draft"
    SENT = "sent"
    DELIVERED = "delivered"
    READ = "read"
    FAILED = "failed"
    BOUNCED = "bounced"

# Базовые схемы
class MessageBase(BaseModel):
    """Базовые поля сообщения"""
    subject: Optional[str] = Field(None, max_length=255, description="Тема сообщения")
    body: str = Field(..., min_length=1, description="Текст сообщения")
    is_internal: bool = Field(False, description="Внутреннее сообщение (только для агентов)")
    is_automatic: bool = Field(False, description="Автоматическое сообщение (системное)")
    
    # Информация о клиенте (если сообщение от клиента)
    customer_name: Optional[str] = Field(None, max_length=200, description="Имя клиента")
    customer_email: Optional[EmailStr] = Field(None, max_length=255, description="Email клиента")
    
    # Метаданные
    ip_address: Optional[str] = Field(None, max_length=45, description="IP адрес отправителя")
    message_type: MessageType = Field(MessageType.EMAIL, description="Тип сообщения")
    status: MessageStatus = Field(MessageStatus.SENT, description="Статус отправки")
    
    @validator('body')
    def validate_body(cls, v):
        if not v or not v.strip():
            raise ValueError('Тело сообщения не может быть пустым')
        return v.strip()
    
    @validator('ip_address')
    def validate_ip(cls, v):
        if v:
            # Простая валидация IPv4 или IPv6
            if not re.match(r'^([0-9]{1,3}\.){3}[0-9]{1,3}$|^([0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}$', v):
                raise ValueError('Некорректный IP адрес')
        return v

# Схема для создания сообщения
class MessageCreate(MessageBase):
    """Создание нового сообщения"""
    ticket_id: int = Field(..., gt=0, description="ID тикета")
    agent_id: Optional[int] = Field(None, gt=0, description="ID агента (если сообщение от агента)")
    
    # Для прикрепленных файлов
    attachment_ids: Optional[List[int]] = Field(None, description="ID уже загруженных вложений")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "ticket_id": 123,
                "agent_id": 5,
                "subject": "Проблема с доступом к системе",
                "body": "Здравствуйте! Не могу войти в систему, пишет 'неверный пароль'.",
                "is_internal": False,
                "is_automatic": False,
                "customer_name": "Иван Петров",
                "customer_email": "ivan@example.com",
                "ip_address": "192.168.1.100",
                "message_type": "email",
                "status": "sent",
                "attachment_ids": [1, 2]
            }
        }
    )

# Схема для ответа на сообщение
class MessageReply(BaseModel):
    """Ответ на сообщение"""
    body: str = Field(..., min_length=1, description="Текст ответа")
    is_internal: bool = Field(False, description="Внутренний ответ (только для агентов)")
    attachment_ids: Optional[List[int]] = Field(None, description="ID вложений")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "body": "Здравствуйте! Пароль был сброшен. Попробуйте войти с новым паролем.",
                "is_internal": False,
                "attachment_ids": [3]
            }
        }
    )

# Схема для обновления сообщения
class MessageUpdate(BaseModel):
    """Обновление сообщения"""
    subject: Optional[str] = Field(None, max_length=255)
    body: Optional[str] = Field(None, min_length=1)
    is_internal: Optional[bool] = None
    status: Optional[MessageStatus] = None
    
    # Только для системных сообщений
    is_automatic: Optional[bool] = None
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "body": "Обновленный текст сообщения",
                "status": "read"
            }
        }
    )

# Краткая схема для сообщения (для списков)
class MessageBrief(BaseModel):
    """Краткая информация о сообщении"""
    id: int
    subject: Optional[str] = None
    body_preview: str = Field(..., description="Превью текста (первые 200 символов)")
    is_internal: bool
    created_at: datetime
    author_type: str = Field(..., description="Тип автора: agent или customer")
    author_name: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)
    
    @validator('body_preview', always=True)
    def set_body_preview(cls, v, values):
        if 'body' in values and values['body']:
            body = values['body']
            return body[:200] + ('...' if len(body) > 200 else '')
        return v

# Полная схема для ответа
class MessageResponse(MessageBase):
    """Полная информация о сообщении"""
    id: int
    ticket_id: int
    agent_id: Optional[int] = None
    created_at: datetime
    
    # Связанные данные
    agent: Optional['AgentBrief'] = Field(None, description="Агент (если сообщение от агента)")
    attachments: List['AttachmentBrief'] = Field(default_factory=list, description="Вложения")
    
    # Форматированные поля
    formatted_body: Optional[str] = Field(None, description="HTML форматированный текст")
    has_attachments: bool = Field(False, description="Есть ли вложения")
    
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": 1,
                "ticket_id": 123,
                "agent_id": 5,
                "subject": "Проблема с доступом к системе",
                "body": "Здравствуйте! Не могу войти в систему, пишет 'неверный пароль'.",
                "is_internal": False,
                "is_automatic": False,
                "customer_name": "Иван Петров",
                "customer_email": "ivan@example.com",
                "ip_address": "192.168.1.100",
                "message_type": "email",
                "status": "sent",
                "created_at": "2024-01-15T10:30:00Z",
                "agent": {
                    "id": 5,
                    "full_name": "Анна Сидорова",
                    "email": "anna@example.com"
                },
                "attachments": [
                    {
                        "id": 1,
                        "original_filename": "screenshot.png",
                        "file_size": 102400
                    }
                ],
                "has_attachments": True
            }
        }
    )

# Схема для списка сообщений с пагинацией
class MessageListResponse(BaseModel):
    """Список сообщений с пагинацией"""
    items: List[MessageResponse]
    total: int
    page: int
    per_page: int
    has_next: bool
    has_prev: bool
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "items": [],
                "total": 50,
                "page": 1,
                "per_page": 20,
                "has_next": True,
                "has_prev": False
            }
        }
    )

# Схема для фильтрации сообщений
class MessageFilter(BaseModel):
    """Параметры фильтрации сообщений"""
    ticket_id: Optional[int] = None
    agent_id: Optional[int] = None
    is_internal: Optional[bool] = None
    is_automatic: Optional[bool] = None
    message_type: Optional[MessageType] = None
    status: Optional[MessageStatus] = None
    customer_email: Optional[EmailStr] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    search: Optional[str] = Field(None, description="Поиск по теме или тексту")
    has_attachments: Optional[bool] = None
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "ticket_id": 123,
                "is_internal": False,
                "date_from": "2024-01-01T00:00:00Z",
                "date_to": "2024-01-31T23:59:59Z",
                "search": "пароль",
                "has_attachments": True
            }
        }
    )

# Схема для массовой отправки сообщений
class MessageBulkSend(BaseModel):
    """Массовая отправка сообщений"""
    ticket_ids: List[int] = Field(..., min_length=1, max_length=100)
    body: str = Field(..., min_length=1)
    subject: Optional[str] = Field(None, max_length=255)
    is_internal: bool = False
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "ticket_ids": [123, 124, 125],
                "subject": "Важное уведомление",
                "body": "Уважаемые клиенты! Проводятся технические работы...",
                "is_internal": False
            }
        }
    )

# Схема для импорта сообщений
class MessageImport(BaseModel):
    """Импорт сообщений из внешнего источника"""
    ticket_id: int
    messages: List[MessageCreate]
    source: str = Field(..., description="Источник импорта (email, chat, etc)")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "ticket_id": 123,
                "source": "email",
                "messages": []
            }
        }
    )

# Схема для статистики сообщений
class MessageStatistics(BaseModel):
    """Статистика по сообщениям"""
    total_messages: int
    messages_by_type: dict[str, int]
    messages_by_status: dict[str, int]
    internal_vs_public: dict[str, int]
    daily_stats: List[dict] = Field(..., description="Статистика по дням")
    avg_messages_per_ticket: float
    top_agents: List[dict] = Field(..., description="Самые активные агенты")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "total_messages": 1500,
                "messages_by_type": {
                    "email": 1200,
                    "chat": 250,
                    "phone": 50
                },
                "messages_by_status": {
                    "sent": 1400,
                    "read": 100,
                    "failed": 0
                },
                "internal_vs_public": {
                    "internal": 300,
                    "public": 1200
                },
                "daily_stats": [
                    {"date": "2024-01-15", "count": 45},
                    {"date": "2024-01-16", "count": 52}
                ],
                "avg_messages_per_ticket": 3.5,
                "top_agents": [
                    {"agent_id": 5, "name": "Анна Сидорова", "count": 450}
                ]
            }
        }
    )

# Схема для шаблона сообщения
class MessageTemplate(BaseModel):
    """Шаблон сообщения"""
    id: int
    name: str = Field(..., min_length=1, max_length=100)
    subject: Optional[str] = Field(None, max_length=255)
    body: str
    category: Optional[str] = None
    is_shared: bool = Field(False, description="Общий шаблон для всех агентов")
    created_by_agent_id: int
    
    model_config = ConfigDict(from_attributes=True)

class MessageTemplateCreate(BaseModel):
    """Создание шаблона"""
    name: str = Field(..., min_length=1, max_length=100)
    subject: Optional[str] = Field(None, max_length=255)
    body: str
    category: Optional[str] = None
    is_shared: bool = False

# Схема для экспорта сообщений
class MessageExport(BaseModel):
    """Параметры экспорта сообщений"""
    format: str = Field(..., pattern="^(csv|xlsx|json|pdf)$")
    filters: Optional[MessageFilter] = None
    fields: Optional[List[str]] = None
    include_attachments: bool = Field(False)
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "format": "csv",
                "include_attachments": False,
                "filters": {
                    "ticket_id": 123
                }
            }
        }
    )

# Схема для просмотра сообщения (с маркировкой прочитанного)
class MessageReadStatus(BaseModel):
    """Статус прочтения сообщения"""
    message_id: int
    agent_id: int
    read_at: datetime
    is_read: bool = True
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "message_id": 1,
                "agent_id": 5,
                "read_at": "2024-01-15T10:35:00Z",
                "is_read": True
            }
        }
    )

# Схема для черновика сообщения
class MessageDraft(BaseModel):
    """Черновик сообщения"""
    id: Optional[int] = None
    ticket_id: int
    agent_id: int
    subject: Optional[str] = None
    body: Optional[str] = None
    attachment_ids: Optional[List[int]] = None
    saved_at: datetime
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "ticket_id": 123,
                "agent_id": 5,
                "subject": "Черновик ответа",
                "body": "Здравствуйте! Я сейчас изучаю ваш вопрос...",
                "saved_at": "2024-01-15T09:00:00Z"
            }
        }
    )