"""add auto_assign and signature fields to agents

Revision ID: 676853fedd68
Revises: c739fdb23971
Create Date: 2026-03-30 09:31:30.600143

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '676853fedd68'
down_revision: Union[str, Sequence[str], None] = 'c739fdb23971'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('agents', sa.Column('auto_assign', sa.Boolean(), nullable=False, server_default='1'))
    op.add_column('agents', sa.Column('signature', sa.Text(), nullable=True))
    op.create_index(op.f('ix_agents_auto_assign'), 'agents', ['auto_assign'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_agents_auto_assign'), table_name='agents')
    op.drop_column('agents', 'signature')
    op.drop_column('agents', 'auto_assign')
