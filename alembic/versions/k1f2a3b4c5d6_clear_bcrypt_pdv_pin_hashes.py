"""clear bcrypt pdv_pin_hashes for argon2id migration

Revision ID: k1f2a3b4c5d6
Revises: j0e1f2a3b4c5
Create Date: 2026-07-20 00:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "k1f2a3b4c5d6"
down_revision: Union[str, Sequence[str], None] = "j0e1f2a3b4c5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Invalidate legacy bcrypt PIN hashes; admins must regenerate via POST /users/{id}/pdv-pin.
    op.execute(sa.text("UPDATE users SET pdv_pin_hash = NULL WHERE pdv_pin_hash IS NOT NULL"))


def downgrade() -> None:
    # Cannot restore cleared PIN hashes.
    pass
