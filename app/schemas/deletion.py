from __future__ import annotations

from pydantic import BaseModel


class DeleteResponse(BaseModel):
    """
    Универсальный ответ API для DELETE-операций.
    Обычно возвращается вместе со статусом 200/204 (если 200).
    """

    success: bool = True
    deleted_id: int | None = None
    detail: str | None = None

