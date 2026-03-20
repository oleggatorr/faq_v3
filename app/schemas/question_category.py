from pydantic import BaseModel, Field, ConfigDict, validator
from datetime import datetime
from typing import Optional, List
import re

# Перечисление для видимости категории
class CategoryVisibility(str, Enum):
    PUBLIC = "public"
    INTERNAL = "internal"
    TEAM = "team"

# Базовые схемы
class QuestionCategoryBase(BaseModel):
    """Базовые поля категории"""
    name: str = Field(..., min_length=1, max_length=150, description="Название категории")
    description: Optional[str] = Field(None, max_length=5000, description="Описание категории")
    
    # Визуальное оформление
    icon: Optional[str] = Field(None, max_length=100, description="Иконка (CSS класс или emoji)")
    color: str = Field('#999999', pattern=r'^#[0-9a-fA-F]{6}$', description="Цвет в HEX формате")
    
    # Организация
    is_active: bool = Field(default=True, description="Активна ли категория")
    sort_order: int = Field(default=0, ge=0, description="Порядок сортировки")
    
    # Метаданные
    slug: Optional[str] = Field(None, max_length=150, description="URL-дружественный идентификатор")
    keywords: Optional[str] = Field(None, max_length=500, description="Ключевые слова для поиска")
    visibility: CategoryVisibility = Field(CategoryVisibility.PUBLIC, description="Видимость категории")
    
    @validator('name')
    def validate_name(cls, v):
        if not v.strip():
            raise ValueError('Название не может быть пустым')
        return v.strip()
    
    @validator('slug')
    def validate_slug(cls, v):
        if v:
            if not re.match(r'^[a-z0-9]+(?:-[a-z0-9]+)*$', v):
                raise ValueError('Slug должен содержать только латинские буквы, цифры и дефисы')
        return v

# Схема для создания категории
class QuestionCategoryCreate(QuestionCategoryBase):
    """Создание новой категории"""
    department_id: Optional[int] = Field(None, gt=0, description="ID отдела")
    parent_id: Optional[int] = Field(None, gt=0, description="ID родительской категории")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "Технические вопросы",
                "description": "Категория для технических проблем и вопросов",
                "department_id": 1,
                "parent_id": None,
                "icon": "fa fa-cogs",
                "color": "#3498db",
                "is_active": True,
                "sort_order": 10,
                "slug": "technical-issues",
                "keywords": "техника, проблемы, ошибки",
                "visibility": "public"
            }
        }
    )

# Схема для обновления категории
class QuestionCategoryUpdate(BaseModel):
    """Обновление категории (все поля опциональны)"""
    name: Optional[str] = Field(None, min_length=1, max_length=150)
    description: Optional[str] = Field(None, max_length=5000)
    department_id: Optional[int] = Field(None, gt=0)
    parent_id: Optional[int] = Field(None, gt=0)
    icon: Optional[str] = Field(None, max_length=100)
    color: Optional[str] = Field(None, pattern=r'^#[0-9a-fA-F]{6}$')
    is_active: Optional[bool] = None
    sort_order: Optional[int] = Field(None, ge=0)
    slug: Optional[str] = Field(None, max_length=150)
    keywords: Optional[str] = Field(None, max_length=500)
    visibility: Optional[CategoryVisibility] = None
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "Техническая поддержка",
                "sort_order": 5,
                "is_active": True,
                "color": "#e74c3c"
            }
        }
    )

# Краткая схема для категории (для вложенных ответов)
class QuestionCategoryBrief(BaseModel):
    """Краткая информация о категории"""
    id: int
    name: str
    icon: Optional[str] = None
    color: str
    slug: Optional[str] = None
    is_active: bool
    
    model_config = ConfigDict(from_attributes=True)

# Схема для ответа с иерархией
class QuestionCategoryNode(BaseModel):
    """Узел категории для иерархического представления"""
    id: int
    name: str
    description: Optional[str] = None
    icon: Optional[str] = None
    color: str
    slug: Optional[str] = None
    sort_order: int
    level: int = Field(0, description="Уровень вложенности")
    children: List['QuestionCategoryNode'] = Field(default_factory=list, description="Дочерние категории")
    
    # Статистика
    tickets_count: Optional[int] = Field(None, description="Количество тикетов в категории")
    children_count: int = Field(0, description="Количество дочерних категорий")
    
    model_config = ConfigDict(from_attributes=True)

# Полная схема для ответа
class QuestionCategoryResponse(QuestionCategoryBase):
    """Полная информация о категории"""
    id: int
    department_id: Optional[int] = None
    parent_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    
    # Связанные данные
    department: Optional['DepartmentBrief'] = Field(None, description="Отдел")
    parent: Optional['QuestionCategoryBrief'] = Field(None, description="Родительская категория")
    children: List['QuestionCategoryBrief'] = Field(default_factory=list, description="Дочерние категории")
    
    # Статистика
    tickets_count: Optional[int] = Field(None, description="Количество тикетов")
    depth: int = Field(0, description="Глубина вложенности")
    full_path: str = Field("", description="Полный путь категории")
    
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": 1,
                "name": "Технические вопросы",
                "description": "Категория для технических проблем и вопросов",
                "department_id": 1,
                "parent_id": None,
                "icon": "fa fa-cogs",
                "color": "#3498db",
                "is_active": True,
                "sort_order": 10,
                "slug": "technical-issues",
                "keywords": "техника, проблемы, ошибки",
                "visibility": "public",
                "created_at": "2024-01-01T08:00:00Z",
                "updated_at": "2024-01-15T10:30:00Z",
                "department": {
                    "id": 1,
                    "name": "Техническая поддержка"
                },
                "children": [],
                "tickets_count": 125,
                "depth": 0,
                "full_path": "Технические вопросы"
            }
        }
    )

# Схема для фильтрации категорий
class QuestionCategoryFilter(BaseModel):
    """Параметры фильтрации категорий"""
    department_id: Optional[int] = None
    parent_id: Optional[int] = None
    is_active: Optional[bool] = None
    visibility: Optional[CategoryVisibility] = None
    search: Optional[str] = Field(None, description="Поиск по названию или описанию")
    has_tickets: Optional[bool] = Field(None, description="Категории с тикетами")
    sort_by: Optional[str] = Field("sort_order", description="Поле для сортировки")
    sort_desc: bool = Field(False, description="Обратный порядок")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "department_id": 1,
                "is_active": True,
                "search": "технические",
                "has_tickets": True
            }
        }
    )

# Схема для перемещения категории
class CategoryMove(BaseModel):
    """Перемещение категории"""
    category_id: int
    new_parent_id: Optional[int] = Field(None, description="Новый родитель (None - корневая)")
    
    @validator('new_parent_id')
    def prevent_self_parent(cls, v, values):
        if v and 'category_id' in values and v == values['category_id']:
            raise ValueError('Категория не может быть родителем самой себя')
        return v
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "category_id": 5,
                "new_parent_id": 2
            }
        }
    )

# Схема для массового обновления
class CategoryBulkUpdate(BaseModel):
    """Массовое обновление категорий"""
    category_ids: List[int] = Field(..., min_length=1)
    is_active: Optional[bool] = None
    department_id: Optional[int] = None
    visibility: Optional[CategoryVisibility] = None

# Схема для переупорядочивания категорий
class CategoryReorder(BaseModel):
    """Переупорядочивание категорий в рамках родителя"""
    parent_id: Optional[int] = Field(None, description="ID родительской категории")
    category_orders: List[dict] = Field(..., description="Список {id: sort_order}")
    
    @validator('category_orders')
    def validate_orders(cls, v):
        if not v:
            raise ValueError('Список не может быть пустым')
        for item in v:
            if 'id' not in item or 'sort_order' not in item:
                raise ValueError('Каждый элемент должен содержать id и sort_order')
        return v

# Схема для экспорта категорий
class CategoryExport(BaseModel):
    """Параметры экспорта категорий"""
    format: str = Field(..., pattern="^(csv|xlsx|json)$")
    include_hierarchy: bool = Field(True, description="Включить иерархическую структуру")
    include_statistics: bool = Field(True, description="Включить статистику")
    filters: Optional[QuestionCategoryFilter] = None

# Схема для аналитики по категориям
class CategoryAnalytics(BaseModel):
    """Аналитика по категории"""
    category: QuestionCategoryBrief
    stats: dict = Field(..., description="Статистика категории")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "category": {
                    "id": 1,
                    "name": "Технические вопросы",
                    "icon": "fa fa-cogs",
                    "color": "#3498db"
                },
                "stats": {
                    "total_tickets": 125,
                    "open_tickets": 15,
                    "resolved_tickets": 105,
                    "closed_tickets": 5,
                    "avg_resolution_time": "4.2 hours",
                    "satisfaction_rate": 4.6
                }
            }
        }
    )

# Схема для создания пути категории
class CategoryPath(BaseModel):
    """Путь категории в иерархии"""
    category_id: int
    path: List[QuestionCategoryBrief] = Field(..., description="Путь от корня до категории")
    depth: int
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "category_id": 3,
                "path": [
                    {"id": 1, "name": "Технические вопросы"},
                    {"id": 2, "name": "Сеть и интернет"},
                    {"id": 3, "name": "WiFi проблемы"}
                ],
                "depth": 2
            }
        }
    )

# Схема для импорта категорий
class CategoryImport(BaseModel):
    """Импорт категорий из внешнего источника"""
    data: List[dict] = Field(..., description="Данные для импорта")
    replace_existing: bool = Field(False, description="Заменять существующие категории")
    validate_only: bool = Field(False, description="Только валидация без сохранения")

# Схема для шаблона категории
class CategoryTemplate(BaseModel):
    """Шаблон для быстрого создания категорий"""
    name: str
    description: Optional[str] = None
    icon: Optional[str] = None
    color: str = '#999999'
    keywords: Optional[str] = None
    visibility: CategoryVisibility = CategoryVisibility.PUBLIC

# Схема для поиска категорий
class CategorySearch(BaseModel):
    """Поиск категорий"""
    query: str = Field(..., min_length=2, description="Поисковый запрос")
    limit: int = Field(10, ge=1, le=50)
    include_inactive: bool = Field(False, description="Включать неактивные категории")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "query": "технические",
                "limit": 20,
                "include_inactive": False
            }
        }
    )

# Схема для дерева категорий с отделами
class DepartmentCategoryTree(BaseModel):
    """Дерево категорий сгруппированное по отделам"""
    department: 'DepartmentBrief'
    categories: List[QuestionCategoryNode] = Field(..., description="Дерево категорий")
    
    model_config = ConfigDict(from_attributes=True)

# Схема для валидации уникальности имени
class CategoryNameCheck(BaseModel):
    """Проверка уникальности имени категории"""
    name: str
    department_id: Optional[int] = None
    parent_id: Optional[int] = None
    exclude_id: Optional[int] = Field(None, description="ID для исключения при проверке")