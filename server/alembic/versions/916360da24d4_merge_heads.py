"""merge heads

Revision ID: 916360da24d4
Revises: ec11eb7ff557
Create Date: 2026-03-04 17:06:32.401123

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '916360da24d4'
down_revision: Union[str, None] = 'ec11eb7ff557'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass

