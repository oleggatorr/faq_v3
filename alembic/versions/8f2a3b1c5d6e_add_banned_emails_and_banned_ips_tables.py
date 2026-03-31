"""add banned_emails and banned_ips tables

Revision ID: 8f2a3b1c5d6e
Revises: 0343018c2b30
Create Date: 2026-03-31 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8f2a3b1c5d6e'
down_revision: Union[str, Sequence[str], None] = '0343018c2b30'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Таблица забаненных email
    op.create_table(
        'banned_emails',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('banned_by', sa.Integer(), nullable=True),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.ForeignKeyConstraint(['banned_by'], ['agents.id'], ondelete='SET NULL', onupdate='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_banned_emails_email'), 'banned_emails', ['email'], unique=True)
    op.create_index(op.f('ix_banned_emails_banned_by'), 'banned_emails', ['banned_by'], unique=False)

    # Таблица забаненных IP (с поддержкой диапазонов)
    op.create_table(
        'banned_ips',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('ip_from', sa.BigInteger(), nullable=False),
        sa.Column('ip_to', sa.BigInteger(), nullable=False),
        sa.Column('ip_display', sa.String(100), nullable=False),
        sa.Column('banned_by', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.ForeignKeyConstraint(['banned_by'], ['agents.id'], ondelete='SET NULL', onupdate='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_banned_ips_banned_by'), 'banned_ips', ['banned_by'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('banned_ips')
    op.drop_table('banned_emails')
