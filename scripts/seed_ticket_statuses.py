"""
Seed справочника `ticket_statuses`.

Идемпотентный: не создаёт дубликаты по `name` (и дополнительно по `code`).
"""

from __future__ import annotations

import pathlib
import sys
from typing import Dict, List, Tuple

from dotenv import load_dotenv
from sqlalchemy import select

project_root = pathlib.Path(__file__).resolve().parents[1]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from app.models import Base, SessionLocal, engine  # noqa: E402
from app.models.ticket_status import TicketStatus  # noqa: E402


STATUSES: List[Dict] = [
    {
        "code": "awaiting_reply",
        "name": "Ожидание ответа",
        "color": "#1E90FF",
        "is_closed": False,
        "is_default": False,
        "sort_order": 30,
    },
    {
        "code": "reply_sent",
        "name": "Ответ отправлен",
        "color": "#20B2AA",
        "is_closed": False,
        "is_default": False,
        "sort_order": 40,
    },
    {
        "code": "paused",
        "name": "Приостановлена",
        "color": "#FF8C00",
        "is_closed": False,
        "is_default": False,
        "sort_order": 50,
    },
    {
        "code": "resolved",
        "name": "Решена",
        "color": "#2E8B57",
        "is_closed": True,
        "is_default": False,
        "sort_order": 60,
    },
]


def main() -> Tuple[int, int]:
    load_dotenv()
    Base.metadata.create_all(bind=engine)

    desired_names = {s["name"] for s in STATUSES}
    desired_codes = {s["code"] for s in STATUSES}

    added = 0
    skipped = 0

    with SessionLocal() as session:
        existing_by_name = {
            row.name: row
            for row in session.execute(
                select(TicketStatus).where(TicketStatus.name.in_(desired_names))
            ).scalars().all()
        }
        existing_by_code = {
            row.code: row
            for row in session.execute(
                select(TicketStatus).where(TicketStatus.code.in_(desired_codes))
            ).scalars().all()
        }

        for st in STATUSES:
            if st["name"] in existing_by_name or st["code"] in existing_by_code:
                skipped += 1
                continue

            session.add(TicketStatus(**st))
            added += 1

        session.commit()

    print(f"Added ticket statuses: {added}")
    print(f"Skipped (already exists): {skipped}")
    return added, skipped


if __name__ == "__main__":
    main()

