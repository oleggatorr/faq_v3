"""
Seed справочников для оператора:
- `departments`
- `question_categories`

Скрипт идемпотентный: повторный запуск не создаёт дубликаты (проверка по `name`).
"""

from __future__ import annotations

import pathlib
import sys
from typing import Dict, List, Optional, Tuple

project_root = pathlib.Path(__file__).resolve().parents[1]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
from sqlalchemy import select

from app.models import SessionLocal, engine, Base
from app.models.department import Department
from app.models.question_category import QuestionCategory


def _decode(s: str) -> str:
    # На случай если в списках встречаются HTML-сущности.
    return (
        s.replace("&amp;", "&")
        .replace("эконом.", "эконом.")
    )


DEPARTMENTS: List[str] = [
    "Руководство (GM)",
    "Финансовый департамент (FD)",
    "Департамент по управлению персоналом и общим вопросам (HR&GA)",
    "Департамент информационных технологий (IT)",
    "Производственный департамент (MD)",
    "Департамент логистики (LD)",
    "Департамент качества (QD)",
    "Департамент технического обслуживания оборудования (M&U)",
    "Департамент технологий (TD)",
    "Департамент исследований и разработок (R&D)",
    "Департамент стратегического развития и локализации (SDD)",
    "Департамент управления качеством (QMD)",
]


QUESTION_CATEGORIES: List[str] = [
    "Группа по безопасности (SEC)",
    "Департамент по управлению персоналом(HR)",
    "Вопросы по заработной плате (HR, salary)",
    "Антикоррупция и эконом. безопасность",
    "Вопросы по столовой (GA)",
    "Административный отдел (GA)",
    "Департамент обслуживания (M&U)",
    "Отдел охраны труда и экологии (HSE)",
    "Производственный департамент (MD)",
    "Цех Сварки (MD,WELD)",
    "Департамент качества (QD)",
    "Бережливое производство (LM)",
    "Другое (Other)",
    "Департамент логистики (LD)",
    "Финансовый департамент (FD)",
    "Департамент исследований (R&D)",
    "Департамент закупок (T&P)",
    "Департамент технологий (QT)",
    "Департамент страт. развития (SDD)",
]


def build_department_name_to_id_map(session) -> Dict[str, int]:
    rows = session.execute(select(Department)).scalars().all()
    return {d.name: d.id for d in rows}


def pick_department_for_category(
    category_name: str,
    dept_name_to_id: Dict[str, int],
) -> Optional[int]:
    # Heuristics-мэппинг (приблизительный). Если уверенности нет — оставляем `None`,
    # т.к. `question_categories.department_id` допускает `NULL`.
    if category_name.endswith("(MD)") or "Производственный департамент" in category_name:
        return dept_name_to_id.get("Производственный департамент (MD)")
    if "WELD" in category_name:
        return dept_name_to_id.get("Производственный департамент (MD)")
    if "(QD" in category_name or "Департамент качества (QD)" == category_name:
        return dept_name_to_id.get("Департамент качества (QD)")
    if "(LD" in category_name or "Департамент логистики (LD)" == category_name:
        return dept_name_to_id.get("Департамент логистики (LD)")
    if "(FD" in category_name or "Финансовый департамент (FD)" == category_name:
        return dept_name_to_id.get("Финансовый департамент (FD)")
    if "(R&D" in category_name or "Департамент исследований (R&D)" == category_name:
        return dept_name_to_id.get("Департамент исследований и разработок (R&D)")
    if "Технолог" in category_name:
        return dept_name_to_id.get("Департамент технологий (TD)")
    if "(SDD" in category_name:
        return dept_name_to_id.get("Департамент стратегического развития и локализации (SDD)")
    if "M&U" in category_name:
        return dept_name_to_id.get("Департамент технического обслуживания оборудования (M&U)")
    if "(HR" in category_name or "GA" in category_name or "заработ" in category_name:
        return dept_name_to_id.get("Департамент по управлению персоналом и общим вопросам (HR&GA)")

    # SEC / HSE / LM / Other / T&P — пока не маппим (нет явных соответствий в списке департаментов).
    return None


def main() -> Tuple[int, int]:
    load_dotenv()
    # На случай чистой БД.
    Base.metadata.create_all(bind=engine)

    with SessionLocal() as session:
        dept_name_to_id = build_department_name_to_id_map(session)

        added_departments = 0
        for raw_name in DEPARTMENTS:
            name = _decode(raw_name)
            if name in dept_name_to_id:
                continue
            session.add(Department(name=name))
            added_departments += 1
        session.commit()

        # После commit обновим map.
        dept_name_to_id = build_department_name_to_id_map(session)

        added_categories = 0
        for raw_name in QUESTION_CATEGORIES:
            name = _decode(raw_name)
            existing = session.execute(
                select(QuestionCategory).where(QuestionCategory.name == name)
            ).scalar_one_or_none()
            if existing is not None:
                continue

            dept_id = pick_department_for_category(name, dept_name_to_id)
            session.add(
                QuestionCategory(
                    name=name,
                    department_id=dept_id,
                    is_active=True,
                    sort_order=0,
                )
            )
            added_categories += 1
        session.commit()

        print(f"Added departments: {added_departments}")
        print(f"Added question categories: {added_categories}")
        return added_departments, added_categories


if __name__ == "__main__":
    main()

