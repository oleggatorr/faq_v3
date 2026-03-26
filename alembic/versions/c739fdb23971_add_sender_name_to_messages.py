"""add_sender_name_to_messages

Revision ID: c739fdb23971
Revises: 44586382e4ef
Create Date: 2026-03-26 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c739fdb23971'
down_revision: Union[str, Sequence[str], None] = '44586382e4ef'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Добавляем поле sender_name для хранения ФИО отправителя
    op.add_column('messages', sa.Column('sender_name', sa.String(200), nullable=True))
    
    # Заполняем существующие записи:
    # - Если есть agent_id → берём ФИО из agents
    # - Если нет → берём customer_name
    op.execute("""
        UPDATE messages m
        LEFT JOIN agents a ON m.agent_id = a.id
        SET m.sender_name = COALESCE(a.full_name, m.customer_name)
    """)


def downgrade() -> None:
    """Downgrade schema."""
    # Удаляем поле
    op.drop_column('messages', 'sender_name')
