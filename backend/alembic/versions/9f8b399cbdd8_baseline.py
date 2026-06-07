"""baseline

Revision ID: 9f8b399cbdd8
Revises: 
Create Date: 2026-05-23 10:18:06.814739
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = '9f8b399cbdd8'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
