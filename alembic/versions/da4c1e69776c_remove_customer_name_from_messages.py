"""remove customer_name from messages

Revision ID: da4c1e69776c
Revises: 676853fedd68
Create Date: 2026-03-30 09:38:32.659969

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'da4c1e69776c'
down_revision: Union[str, Sequence[str], None] = '676853fedd68'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.drop_column('messages', 'customer_name')


def downgrade() -> None:
    """Downgrade schema."""
    op.add_column('messages', sa.Column('customer_name', sa.String(200), nullable=True))
