"""add indexes to agents table

Revision ID: d917c5d51d8b
Revises: c1b54489b381
Create Date: 2026-03-25 16:28:29.725079

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd917c5d51d8b'
down_revision: Union[str, Sequence[str], None] = 'c1b54489b381'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Создаём индексы для ускорения фильтрации и поиска
    op.create_index('ix_agents_full_name', 'agents', ['full_name'], unique=False)
    op.create_index('ix_agents_role', 'agents', ['role'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    # Удаляем индексы
    op.drop_index('ix_agents_role', 'agents')
    op.drop_index('ix_agents_full_name', 'agents')
