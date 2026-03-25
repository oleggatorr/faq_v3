"""
Утилиты для аудиторского логирования.

Использование:
    from app.core.audit import log_action, get_client_info
    
    # В роутах:
    client_info = get_client_info(request)
    log_action(db, agent_id=agent.id, action="create", entity_type="ticket", **client_info)
"""
from __future__ import annotations

from typing import Optional, Dict, Any
from fastapi import Request


def get_client_info(request: Request) -> Dict[str, Optional[str]]:
    """
    Получить информацию о клиенте из запроса.
    
    Returns:
        dict с ключами: ip_address, user_agent
    """
    # Получаем реальный IP (с учётом прокси)
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        ip_address = forwarded_for.split(",")[0].strip()
    else:
        # Для прямого подключения
        client_host = request.client.host if request.client else None
        ip_address = client_host
    
    user_agent = request.headers.get("User-Agent")
    
    return {
        "ip_address": ip_address,
        "user_agent": user_agent,
    }


def get_entity_type_from_route(route_path: str) -> str:
    """
    Определить тип объекта по пути роута.
    
    Примеры:
        /agents/add → "agent"
        /tickets/123/edit → "ticket"
        /departments/5/delete → "department"
    """
    # Убираем ведущий слэш и разбиваем на части
    parts = route_path.strip("/").split("/")
    
    if len(parts) >= 1:
        # Первый сегмент — обычно тип объекта
        entity = parts[0].rstrip("s")  # agents → agent, tickets → ticket
        return entity
    
    return "unknown"
