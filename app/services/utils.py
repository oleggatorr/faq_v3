from __future__ import annotations

import ipaddress
import json
from typing import Any, Iterable, List, Optional

from sqlalchemy.orm import Query


def parse_text_list(value: Optional[str]) -> List[str]:
    """
    Parse `Agent.category_access` / `Agent.permissions` which may be stored as:
    - JSON array string: "[1,2,5]" or "[\"a\",\"b\"]"
    - CSV: "1,2,5" or "ticket_read,ticket_update"
    - Empty string -> []
    """
    if value is None:
        return []
    raw = value.strip()
    if not raw:
        return []

    # Try JSON first.
    if raw.startswith("[") and raw.endswith("]"):
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, list):
                return [str(x).strip() for x in parsed if str(x).strip()]
        except json.JSONDecodeError:
            # Fall back to CSV.
            pass

    # CSV fallback.
    return [item.strip() for item in raw.split(",") if item.strip()]


def format_preview(body: str, limit: int = 200) -> str:
    if len(body) <= limit:
        return body
    return body[:limit] + "..."


def apply_filters(
    query: Query,
    model: Any,
    *,
    filters: dict[str, Any] | None = None,
    text_like_fields: set[str] | None = None,
) -> Query:
    """
    Apply equality or ILIKE filters to a SQLAlchemy query.

    - Only model attributes existing on `model` are allowed.
    - If a field name is listed in `text_like_fields`, string values are matched with ILIKE '%value%'.
    """
    if not filters:
        return query

    like_fields = text_like_fields or set()

    for field, value in filters.items():
        if value is None:
            continue

        if not hasattr(model, field):
            # Fail fast: prevents accidentally filtering by wrong keys.
            raise ValueError(f"Unknown filter field: {field}")

        column = getattr(model, field)
        if field in like_fields and isinstance(value, str):
            query = query.filter(column.ilike(f"%{value}%"))
        else:
            query = query.filter(column == value)

    return query


def apply_sort(
    query: Query,
    model: Any,
    *,
    sort_by: str | None = None,
    sort_desc: bool = False,
    allowed_sort_fields: set[str] | None = None,
) -> Query:
    if not sort_by:
        return query

    if allowed_sort_fields is not None and sort_by not in allowed_sort_fields:
        raise ValueError(f"Sort field is not allowed: {sort_by}")

    if not hasattr(model, sort_by):
        raise ValueError(f"Unknown sort field: {sort_by}")

    column = getattr(model, sort_by)
    return query.order_by(column.desc() if sort_desc else column.asc())


# =============================================================================
# Утилиты для работы с IP-адресами (для банов)
# =============================================================================

def ip_to_int(ip: str) -> int:
    """
    Преобразовать IPv4-адрес в integer (аналог MySQL INET_ATON).
    Пример: '192.168.1.1' -> 3232235777
    """
    return int(ipaddress.IPv4Address(ip))


def int_to_ip(ip_int: int) -> str:
    """
    Преобразовать integer обратно в IPv4-адрес (аналог MySQL INET_NTOA).
    Пример: 3232235777 -> '192.168.1.1'
    """
    return str(ipaddress.IPv4Address(ip_int))


def ip_in_range(ip: str, ip_from: int, ip_to: int) -> bool:
    """
    Проверить, попадает ли IP-адрес в диапазон [ip_from, ip_to].
    """
    ip_int = ip_to_int(ip)
    return ip_from <= ip_int <= ip_to


def ip_to_display(ip: str, mask: int | None = None) -> str:
    """
    Преобразовать IP в человекочитаемое представление.
    Если указан mask (количество октетов), заменить остальные на '*'.
    
    Примеры:
    - ip_to_display('192.168.1.1') -> '192.168.1.1'
    - ip_to_display('192.168.1.1', mask=3) -> '192.168.1.*'
    - ip_to_display('192.168.1.1', mask=2) -> '192.168.*.*'
    """
    octets = ip.split(".")
    if mask is None:
        return ip
    result = octets[:mask] + ["*"] * (4 - mask)
    return ".".join(result)

