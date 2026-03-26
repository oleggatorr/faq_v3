from __future__ import annotations

from typing import Any

from fastapi import Request


def _parse_int(value: str | None) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except ValueError:
        return None


def _parse_bool(value: str | None) -> bool | None:
    if value is None or value == "":
        return None
    v = value.lower()
    if v in ("1", "true", "yes", "on"):
        return True
    if v in ("0", "false", "no", "off"):
        return False
    return None


def _ticket_filters(request: Request) -> dict[str, Any]:
    """Extract ticket filters from query params (whitelist)."""
    params = request.query_params
    filters: dict[str, Any] = {}
    int_keys = {
        "id", "department_id", "language_id", "category_id", "status_id",
        "owner_id", "opened_by_id", "merged_into_id", "messages_count", "attachments_count",
    }
    bool_keys = {"is_archived", "is_locked"}
    str_keys = {"track_id", "customer_name", "customer_email", "subject"}

    for key in int_keys:
        val = _parse_int(params.get(key))
        if val is not None:
            filters[key] = val
    for key in bool_keys:
        val = _parse_bool(params.get(key))
        if val is not None:
            filters[key] = val
    for key in str_keys:
        val = params.get(key)
        if val:
            filters[key] = val

    if "priority" in params and params["priority"]:
        filters["priority"] = params["priority"]
    return filters


def _agent_filters(request: Request) -> dict[str, Any]:
    params = request.query_params
    filters: dict[str, Any] = {}
    if _parse_int(params.get("id")) is not None:
        filters["id"] = _parse_int(params.get("id"))
    if params.get("search"):
        filters["search"] = params["search"]
    if params.get("role"):
        filters["role"] = params["role"]
    if _parse_int(params.get("category_id")) is not None:
        filters["category_id"] = _parse_int(params.get("category_id"))
    val = _parse_bool(params.get("is_active"))
    if val is not None:
        filters["is_active"] = val
    return filters


def _department_filters(request: Request) -> dict[str, Any]:
    params = request.query_params
    filters: dict[str, Any] = {}
    if _parse_int(params.get("id")) is not None:
        filters["id"] = _parse_int(params.get("id"))
    if params.get("name"):
        filters["name"] = params["name"]
    val = _parse_bool(params.get("is_active"))
    if val is not None:
        filters["is_active"] = val
    return filters


def _language_filters(request: Request) -> dict[str, Any]:
    params = request.query_params
    filters: dict[str, Any] = {}
    if _parse_int(params.get("id")) is not None:
        filters["id"] = _parse_int(params.get("id"))
    if params.get("code"):
        filters["code"] = params["code"]
    if params.get("name"):
        filters["name"] = params["name"]
    val = _parse_bool(params.get("is_active"))
    if val is not None:
        filters["is_active"] = val
    return filters
