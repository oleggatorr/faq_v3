"""add email_notifications to agents

Revision ID: 6440c7c01941
Revises: a63d8f25553f
Create Date: 2026-03-30 12:26:19.734146

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6440c7c01941'
down_revision: Union[str, Sequence[str], None] = 'a63d8f25553f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('agents', sa.Column('email_notifications', sa.Boolean(), nullable=False, server_default='1'))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('agents', 'email_notifications')
