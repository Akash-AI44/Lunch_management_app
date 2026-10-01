"""add telegram chat id to users

Revision ID: 31014846a772
Revises: bd7e1852b94e
Create Date: 2026-10-01 12:10:15.101398

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '31014846a772'
down_revision: Union[str, Sequence[str], None] = 'bd7e1852b94e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("telegram_chat_id",
                  sa.String(length=50), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "telegram_chat_id")
