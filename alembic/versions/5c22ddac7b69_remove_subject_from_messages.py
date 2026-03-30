"""remove subject from messages

Revision ID: 5c22ddac7b69
Revises: da4c1e69776c
Create Date: 2026-03-30 09:46:44.772391

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5c22ddac7b69'
down_revision: Union[str, Sequence[str], None] = 'da4c1e69776c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.drop_column('messages', 'subject')


def downgrade() -> None:
    """Downgrade schema."""
    op.add_column('messages', sa.Column('subject', sa.String(255), nullable=True))
