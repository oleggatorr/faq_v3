"""create ticket_read_states table

Revision ID: a63d8f25553f
Revises: 5c22ddac7b69
Create Date: 2026-03-30 10:25:01.114546

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a63d8f25553f'
down_revision: Union[str, Sequence[str], None] = '5c22ddac7b69'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'ticket_read_states',
        sa.Column('ticket_id', sa.Integer(), nullable=False),
        sa.Column('last_read_message_id', sa.Integer(), nullable=True),
        sa.Column('last_read_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.ForeignKeyConstraint(['ticket_id'], ['tickets.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('ticket_id'),
    )
    op.create_index(op.f('ix_ticket_read_states_ticket_id'), 'ticket_read_states', ['ticket_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_ticket_read_states_ticket_id'), table_name='ticket_read_states')
    op.drop_table('ticket_read_states')
