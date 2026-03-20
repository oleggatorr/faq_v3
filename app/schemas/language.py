from pydantic import BaseModel, Field, ConfigDict, validator
from datetime import datetime
from typing import Optional, List
import re

# Перечисление для направления текста
class TextDirection(str, Enum):
    LTR = "ltr"
    RTL = "rtl"

# Базовые схемы
class LanguageBase(BaseModel):
    """Базовые поля языка"""
    code: str = Field(..., min_length=2, max_length=10, pattern=r'^[a-z]{2}(-[A-Z]{2})?$', 
                      description="Код языка (например: ru, en, zh-CN)")
    name: str = Field(..., min_length=1, max_length=100, description="Название языка (на английском)")
    native_name: Optional[str] = Field(None, max_length=100, description="Название на родном языке")
    locale: Optional[str] = Field(None, max_length=20, description="Локаль (например: ru_RU, en_US)")
    is_active: bool = Field(default=True, description="Активен ли язык")
    is_default: bool = Field(default=False, description="Язык по умолчанию")
    sort_order: int = Field(default=0, ge=0, description="Порядок сортировки")
    direction: TextDirection = Field(default=TextDirection.LTR, description="Направление текста")
    flag_icon: Optional[str] = Field(None, max_length=100, description="Иконка флага")
    date_format: Optional[str] = Field(None, max_length=50, description="Формат даты (например: DD.MM.YYYY)")
    time_format: Optional[str] = Field(None, max_length=50, description="Формат времени (например: HH:mm)")
    
    @validator('code')
    def validate_code(cls, v):
        """Валидация кода языка (ISO 639-1 или BCP47)"""
        if not re.match(r'^[a-z]{2}(-[A-Z]{2})?$', v):
            raise ValueError('Код языка должен быть в формате: ru, en, zh-CN')
        return v
    
    @validator('locale')
    def validate_locale(cls, v):
        """Валидация локали"""
        if v and not re.match(r'^[a-z]{2}_[A-Z]{2}$', v):
            raise ValueError('Локаль должна быть в формате: ru_RU, en_US')
        return v

# Схема для создания языка
class LanguageCreate(LanguageBase):
    """Создание нового языка"""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "code": "ru",
                "name": "Russian",
                "native_name": "Русский",
                "locale": "ru_RU",
                "is_active": True,
                "is_default": True,
                "sort_order": 10,
                "direction": "ltr",
                "flag_icon": "🇷🇺",
                "date_format": "DD.MM.YYYY",
                "time_format": "HH:mm"
            }
        }
    )

# Схема для обновления языка
class LanguageUpdate(BaseModel):
    """Обновление данных языка (все поля опциональны)"""
    code: Optional[str] = Field(None, min_length=2, max_length=10, pattern=r'^[a-z]{2}(-[A-Z]{2})?$')
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    native_name: Optional[str] = Field(None, max_length=100)
    locale: Optional[str] = Field(None, max_length=20)
    is_active: Optional[bool] = None
    is_default: Optional[bool] = None
    sort_order: Optional[int] = Field(None, ge=0)
    direction: Optional[TextDirection] = None
    flag_icon: Optional[str] = Field(None, max_length=100)
    date_format: Optional[str] = Field(None, max_length=50)
    time_format: Optional[str] = Field(None, max_length=50)
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "is_active": True,
                "is_default": False,
                "sort_order": 20
            }
        }
    )

# Краткая схема для языка (для вложенных ответов)
class LanguageBrief(BaseModel):
    """Краткая информация о языке"""
    id: int
    code: str
    name: str
    native_name: Optional[str] = None
    is_default: bool
    direction: TextDirection
    flag_icon: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)

# Полная схема для ответа
class LanguageResponse(LanguageBase):
    """Полная информация о языке"""
    id: int
    created_at: datetime
    
    # Статистика использования
    tickets_count: Optional[int] = Field(None, description="Количество тикетов на этом языке")
    
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": 1,
                "code": "ru",
                "name": "Russian",
                "native_name": "Русский",
                "locale": "ru_RU",
                "is_active": True,
                "is_default": True,
                "sort_order": 10,
                "direction": "ltr",
                "flag_icon": "🇷🇺",
                "date_format": "DD.MM.YYYY",
                "time_format": "HH:mm",
                "created_at": "2024-01-01T08:00:00Z",
                "tickets_count": 1250
            }
        }
    )

# Схема для установки языка по умолчанию
class LanguageSetDefault(BaseModel):
    """Установка языка по умолчанию"""
    language_id: int = Field(..., gt=0, description="ID языка")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "language_id": 1
            }
        }
    )

# Схема для фильтрации языков
class LanguageFilter(BaseModel):
    """Параметры фильтрации языков"""
    is_active: Optional[bool] = None
    is_default: Optional[bool] = None
    direction: Optional[TextDirection] = None
    search: Optional[str] = Field(None, description="Поиск по коду или названию")
    sort_by: Optional[str] = Field("sort_order", description="Поле для сортировки")
    sort_desc: bool = Field(False, description="Обратный порядок")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "is_active": True,
                "search": "russian",
                "sort_by": "name",
                "sort_desc": False
            }
        }
    )

# Схема для перевода (локализация)
class TranslationBase(BaseModel):
    """Базовая схема перевода"""
    key: str = Field(..., min_length=1, max_length=255, description="Ключ перевода")
    language_code: str = Field(..., min_length=2, max_length=10, description="Код языка")
    value: str = Field(..., description="Текст перевода")
    context: Optional[str] = Field(None, max_length=255, description="Контекст использования")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "key": "welcome_message",
                "language_code": "ru",
                "value": "Добро пожаловать в систему!",
                "context": "user_greeting"
            }
        }
    )

class TranslationCreate(TranslationBase):
    """Создание перевода"""
    pass

class TranslationUpdate(BaseModel):
    """Обновление перевода"""
    value: Optional[str] = None
    context: Optional[str] = None

class TranslationResponse(TranslationBase):
    """Ответ с переводом"""
    id: int
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

# Схема для пакета переводов
class TranslationPackage(BaseModel):
    """Пакет переводов для языка"""
    language_code: str
    translations: dict[str, str] = Field(..., description="Словарь ключ-значение")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "language_code": "ru",
                "translations": {
                    "welcome_message": "Добро пожаловать",
                    "logout": "Выйти",
                    "settings": "Настройки"
                }
            }
        }
    )

# Схема для аналитики по языкам
class LanguageAnalytics(BaseModel):
    """Аналитика использования языков"""
    language: LanguageBrief
    stats: dict = Field(..., description="Статистика использования")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "language": {
                    "id": 1,
                    "code": "ru",
                    "name": "Russian",
                    "native_name": "Русский",
                    "is_default": True,
                    "direction": "ltr",
                    "flag_icon": "🇷🇺"
                },
                "stats": {
                    "total_tickets": 1250,
                    "open_tickets": 45,
                    "resolved_tickets": 1205,
                    "percentage": 62.5,
                    "avg_response_time": "2.3 hours"
                }
            }
        }
    )

# Схема для массового управления языками
class LanguageBulkAction(BaseModel):
    """Массовое действие с языками"""
    language_ids: List[int] = Field(..., min_length=1)
    action: str = Field(..., pattern="^(activate|deactivate|delete)$")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "language_ids": [1, 2, 3],
                "action": "activate"
            }
        }
    )

# Схема для импорта/экспорта переводов
class TranslationImport(BaseModel):
    """Импорт переводов"""
    format: str = Field(..., pattern="^(json|csv|po)$")
    data: str = Field(..., description="Данные для импорта")
    replace_existing: bool = Field(False, description="Заменять существующие переводы")
    
class TranslationExport(BaseModel):
    """Экспорт переводов"""
    format: str = Field(..., pattern="^(json|csv|po)$")
    language_codes: Optional[List[str]] = Field(None, description="Список языков (все, если не указан)")
    keys: Optional[List[str]] = Field(None, description="Список ключей (все, если не указан)")

# Схема для обнаружения недостающих переводов
class MissingTranslations(BaseModel):
    """Недостающие переводы"""
    language_code: str
    missing_keys: List[str] = Field(..., description="Ключи без перевода")
    total_missing: int = Field(..., description="Всего недостающих")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "language_code": "ru",
                "missing_keys": ["new_feature", "beta_warning"],
                "total_missing": 2
            }
        }
    )

# Схема для выбора языка в интерфейсе
class LanguageOption(LanguageBrief):
    """Опция языка для выпадающего списка"""
    selected: bool = False
    model_config = ConfigDict(from_attributes=True)

# Схема для ответа с локализованным контентом
class LocalizedContent(BaseModel):
    """Локализованный контент"""
    default_language: LanguageBrief
    current_language: LanguageBrief
    translations: dict[str, str] = Field(..., description="Локализованные строки")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "default_language": {
                    "id": 1,
                    "code": "en",
                    "name": "English",
                    "is_default": True
                },
                "current_language": {
                    "id": 2,
                    "code": "ru",
                    "name": "Russian"
                },
                "translations": {
                    "title": "Заголовок",
                    "description": "Описание"
                }
            }
        }
    )