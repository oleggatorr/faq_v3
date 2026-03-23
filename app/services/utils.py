from __future__ import annotations

import json
from typing import Iterable, List, Optional


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

