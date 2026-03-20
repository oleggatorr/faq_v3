from pydantic import BaseModel, Field, ConfigDict, HttpUrl, validator
from datetime import datetime
from typing import Optional, List
import mimetypes

# Базовые схемы
class AttachmentBase(BaseModel):
    """Базовые поля вложения"""
    original_filename: str = Field(..., min_length=1, max_length=255, description="Оригинальное имя файла")
    file_size: int = Field(..., gt=0, le=100*1024*1024, description="Размер файла в байтах (max 100MB)")
    mime_type: str = Field(..., max_length=100, description="MIME тип файла")
    
    @validator('mime_type')
    def validate_mime_type(cls, v):
        allowed_types = [
            'image/', 'application/pdf', 'text/plain', 
            'application/msword', 'application/vnd.openxmlformats-officedocument'
        ]
        if not any(v.startswith(allowed) for allowed in allowed_types):
            raise ValueError(f'Неподдерживаемый MIME тип: {v}')
        return v

# Схема для создания вложения (при загрузке файла)
class AttachmentCreate(BaseModel):
    """Создание нового вложения"""
    message_id: int = Field(..., gt=0, description="ID сообщения")
    original_filename: str = Field(..., min_length=1, max_length=255)
    stored_filename: str = Field(..., min_length=1, max_length=100, description="Уникальное имя в хранилище")
    file_path: str = Field(..., min_length=1, max_length=500, description="Путь к файлу")
    file_size: int = Field(..., gt=0)
    mime_type: str = Field(..., max_length=100)
    file_hash: Optional[str] = Field(None, min_length=32, max_length=64, description="SHA256 или MD5 хеш")
    uploaded_by_agent_id: Optional[int] = Field(None, gt=0, description="ID загрузившего агента")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "message_id": 123,
                "original_filename": "document.pdf",
                "stored_filename": "a1b2c3d4e5f6.pdf",
                "file_path": "/uploads/2024/01/15/a1b2c3d4e5f6.pdf",
                "file_size": 1024000,
                "mime_type": "application/pdf",
                "file_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
                "uploaded_by_agent_id": 1
            }
        }
    )

# Схема для ответа (чтение)
class AttachmentResponse(AttachmentBase):
    """Полная информация о вложении"""
    id: int
    message_id: int
    stored_filename: str
    file_path: str
    file_hash: Optional[str] = None
    uploaded_by_agent_id: Optional[int] = None
    uploaded_at: datetime
    download_count: int = Field(..., ge=0)
    
    # Опционально: URL для скачивания (формируется на уровне API)
    download_url: Optional[str] = Field(None, description="Ссылка для скачивания")
    thumbnail_url: Optional[str] = Field(None, description="Ссылка на миниатюру (для изображений)")
    
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": 1,
                "message_id": 123,
                "original_filename": "document.pdf",
                "stored_filename": "a1b2c3d4e5f6.pdf",
                "file_path": "/uploads/2024/01/15/a1b2c3d4e5f6.pdf",
                "file_size": 1024000,
                "mime_type": "application/pdf",
                "file_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
                "uploaded_by_agent_id": 1,
                "uploaded_at": "2024-01-15T10:30:00Z",
                "download_count": 5,
                "download_url": "/api/attachments/1/download",
                "thumbnail_url": None
            }
        }
    )
    
    def get_extension(self) -> str:
        """Получить расширение файла"""
        return self.original_filename.rsplit('.', 1)[-1].lower() if '.' in self.original_filename else ''
    
    def is_image(self) -> bool:
        """Проверить, является ли файл изображением"""
        return self.mime_type.startswith('image/')
    
    def get_formatted_size(self) -> str:
        """Получить размер файла в человекочитаемом формате"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if self.file_size < 1024.0:
                return f"{self.file_size:.1f} {unit}"
            self.file_size /= 1024.0
        return f"{self.file_size:.1f} TB"

# Краткая схема для вложений (для списков)
class AttachmentBrief(BaseModel):
    """Краткая информация о вложении"""
    id: int
    original_filename: str
    file_size: int
    mime_type: str
    download_url: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)
    
    def is_image(self) -> bool:
        return self.mime_type.startswith('image/')

# Схема для обновления (только download_count обычно)
class AttachmentUpdate(BaseModel):
    """Обновление информации о вложении"""
    download_count: Optional[int] = Field(None, ge=0)
    
    # Опционально: если нужен soft delete
    is_deleted: Optional[bool] = None

# Схема для загрузки файла (multipart/form-data)
class AttachmentUpload(BaseModel):
    """Загрузка файла через форму"""
    message_id: int = Field(..., description="ID сообщения")
    file: bytes = Field(..., description="Файл для загрузки")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "message_id": 123
            }
        }
    )

# Схема для массовой загрузки
class AttachmentsBulkUpload(BaseModel):
    """Массовая загрузка файлов"""
    message_id: int
    files: List[bytes] = Field(..., min_items=1, max_items=10, description="Список файлов")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "message_id": 123,
                "files": ["file1.pdf", "file2.jpg"]
            }
        }
    )

# Схема для фильтрации вложений
class AttachmentFilter(BaseModel):
    """Параметры фильтрации вложений"""
    message_id: Optional[int] = None
    uploaded_by_agent_id: Optional[int] = None
    mime_type: Optional[str] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    search: Optional[str] = Field(None, description="Поиск по имени файла")
    is_image: Optional[bool] = Field(None, description="Только изображения")
    
    @validator('mime_type')
    def validate_mime_type_filter(cls, v):
        if v and not v.startswith(('image/', 'application/', 'text/')):
            raise ValueError('Некорректный MIME тип для фильтрации')
        return v

# Схема для статистики по вложениям
class AttachmentStats(BaseModel):
    """Статистика по вложениям"""
    total_count: int = Field(..., description="Общее количество")
    total_size_bytes: int = Field(..., description="Общий размер в байтах")
    total_size_formatted: str = Field(..., description="Общий размер в читаемом формате")
    avg_size_bytes: float = Field(..., description="Средний размер")
    by_mime_type: dict[str, int] = Field(..., description="Группировка по MIME типам")
    by_agent: dict[int, int] = Field(..., description="Количество по агентам")
    most_downloaded: List['AttachmentBrief'] = Field(..., description="Самые скачиваемые")
    
    model_config = ConfigDict(from_attributes=True)

# Схема для ответа при дубликате файла
class AttachmentDuplicateResponse(BaseModel):
    """Ответ при обнаружении дубликата файла"""
    is_duplicate: bool
    existing_attachment: Optional[AttachmentBrief] = None
    message: str
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "is_duplicate": True,
                "existing_attachment": {
                    "id": 5,
                    "original_filename": "document.pdf",
                    "file_size": 1024000,
                    "mime_type": "application/pdf"
                },
                "message": "Файл уже существует в системе"
            }
        }
    )

# Схема для безопасного скачивания
class AttachmentDownloadResponse(BaseModel):
    """Ответ для скачивания файла"""
    filename: str
    content_type: str
    content_length: int
    download_url: str
    expires_at: datetime
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "filename": "document.pdf",
                "content_type": "application/pdf",
                "content_length": 1024000,
                "download_url": "/api/attachments/1/download?token=abc123",
                "expires_at": "2024-01-15T11:00:00Z"
            }
        }
    )

# Импорты для forward references
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .message import MessageResponse
    from .agent import AgentBrief
else:
    MessageResponse = None
    AgentBrief = None

# Расширенная схема с вложенными данными (опционально)
class AttachmentWithRelations(AttachmentResponse):
    """Вложение с информацией о связанных объектах"""
    message: Optional['MessageResponse'] = None
    uploader: Optional['AgentBrief'] = None
    
    model_config = ConfigDict(from_attributes=True)