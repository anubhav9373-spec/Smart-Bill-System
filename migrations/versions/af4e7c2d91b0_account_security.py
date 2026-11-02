"""add account lockout and session invalidation

Revision ID: af4e7c2d91b0
Revises: 9b3c5d7e1f2a
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "af4e7c2d91b0"
down_revision: Union[str, Sequence[str], None] = "9b3c5d7e1f2a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("users") as batch:
        batch.add_column(sa.Column("failed_login_attempts", sa.Integer(), nullable=False, server_default="0"))
        batch.add_column(sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True))
        batch.add_column(sa.Column("session_version", sa.Integer(), nullable=False, server_default="1"))
        batch.alter_column("failed_login_attempts", server_default=None)
        batch.alter_column("session_version", server_default=None)


def downgrade() -> None:
    with op.batch_alter_table("users") as batch:
        batch.drop_column("session_version")
        batch.drop_column("locked_until")
        batch.drop_column("failed_login_attempts")
