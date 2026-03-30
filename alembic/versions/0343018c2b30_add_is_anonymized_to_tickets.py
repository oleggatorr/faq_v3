"""add is_anonymized to tickets

Revision ID: 0343018c2b30
Revises: 6440c7c01941
Create Date: 2026-03-30 16:59:06.553816

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0343018c2b30'
down_revision: Union[str, Sequence[str], None] = '6440c7c01941'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('tickets', sa.Column('is_anonymized', sa.Boolean(), nullable=False, server_default='0'))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('tickets', 'is_anonymized')
