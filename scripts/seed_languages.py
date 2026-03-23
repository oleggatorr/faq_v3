"""
Seed языков в таблицу `languages`.

Идемпотентный: повторный запуск не создаёт дубликаты по `code`.
"""

from __future__ import annotations

import pathlib
import sys
from typing import List, Tuple

from dotenv import load_dotenv
from sqlalchemy import select

project_root = pathlib.Path(__file__).resolve().parents[1]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from app.models import Base, SessionLocal, engine  # noqa: E402
from app.models.language import Language  # noqa: E402


LANGUAGES: List[dict] = [
    {
        "code": "ru",
        "name": "Русский",
        "native_name": "русский",
        "locale": "ru-RU",
        "is_active": True,
        "is_default": False,
        "sort_order": 0,
    },
    {
        "code": "zh",
        "name": "Китайский",
        "native_name": "中文",
        "locale": "zh-CN",
        "is_active": True,
        "is_default": False,
        "sort_order": 0,
    },
    {
        "code": "en",
        "name": "Английский",
        "native_name": "English",
        "locale": "en-US",
        "is_active": True,
        "is_default": False,
        "sort_order": 0,
    },
]


def main() -> Tuple[int, int]:
    load_dotenv()
    Base.metadata.create_all(bind=engine)

    added = 0
    skipped = 0

    with SessionLocal() as session:
        for lang in LANGUAGES:
            existing = session.execute(
                select(Language).where(Language.code == lang["code"])
            ).scalar_one_or_none()

            if existing is not None:
                skipped += 1
                continue

            session.add(Language(**lang))
            added += 1

        session.commit()

    print(f"Added languages: {added}")
    print(f"Skipped (already exists): {skipped}")
    return added, skipped


if __name__ == "__main__":
    main()

