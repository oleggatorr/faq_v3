"""add_indexes_for_performance

Revision ID: 44586382e4ef
Revises: d917c5d51d8b
Create Date: 2026-03-26 12:23:46.258029

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '44586382e4ef'
down_revision: Union[str, Sequence[str], None] = 'd917c5d51d8b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Дополнительные индексы для ускорения запросов
    # Создаём только те, которых ещё нет
    
    # Индекс для таблицы логов (фильтрация по агенту и времени)
    # Этих индексов точно нет, так как таблица новая
    try:
        op.create_index('ix_audit_logs_agent_id', 'audit_logs', ['agent_id'], unique=False)
    except Exception:
        pass  # Индекс уже существует
    
    try:
        op.create_index('ix_audit_logs_timestamp', 'audit_logs', ['timestamp'], unique=False)
    except Exception:
        pass  # Индекс уже существует


def downgrade() -> None:
    """Downgrade schema."""
    # Удаляем индексы
    try:
        op.drop_index('ix_audit_logs_timestamp', 'audit_logs')
    except Exception:
        pass
    
    try:
        op.drop_index('ix_audit_logs_agent_id', 'audit_logs')
    except Exception:
        pass
