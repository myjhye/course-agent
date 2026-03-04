"""merge heads

Revision ID: ec11eb7ff557
Revises: 1e85855bd5d6, 9c0f3b21add3
Create Date: 2026-03-04 17:04:38.058236

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ec11eb7ff557'
down_revision: Union[str, None] = ('1e85855bd5d6', '9c0f3b21add3')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass

