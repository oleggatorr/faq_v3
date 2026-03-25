"""
Исключение для отказа в доступе.
Используется вместо HTTPException(403) для возврата HTML-страницы.
"""


class AccessDeniedError(Exception):
    """
    Исключение вызывается при отсутствии прав доступа.
    
    Args:
        detail: Сообщение об ошибке
        required_permission: Право, которого не хватило (опционально)
    """
    
    def __init__(
        self,
        detail: str = "Доступ запрещён",
        required_permission: str | None = None,
    ):
        self.detail = detail
        self.required_permission = required_permission
        super().__init__(detail)
