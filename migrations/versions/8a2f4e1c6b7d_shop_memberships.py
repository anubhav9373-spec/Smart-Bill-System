"""add shop memberships and roles

Revision ID: 8a2f4e1c6b7d
Revises: c5d6121a979c
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "8a2f4e1c6b7d"
down_revision: Union[str, Sequence[str], None] = "c5d6121a979c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "shop_memberships",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("shop_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("role", sa.String(length=30), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["shop_id"], ["shops.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("shop_id", "user_id", name="uq_shop_membership"),
    )
    op.create_index("ix_shop_memberships_shop_id", "shop_memberships", ["shop_id"], unique=False)
    op.create_index("ix_shop_memberships_user_id", "shop_memberships", ["user_id"], unique=False)
    bind = op.get_bind()
    bind.execute(sa.text(
        "INSERT INTO shop_memberships (shop_id, user_id, role, created_at) "
        "SELECT shop_id, id, CASE WHEN role IN ('owner', 'manager', 'cashier', 'staff') THEN role ELSE 'owner' END, created_at "
        "FROM users"
    ))


def downgrade() -> None:
    op.drop_index("ix_shop_memberships_user_id", table_name="shop_memberships")
    op.drop_index("ix_shop_memberships_shop_id", table_name="shop_memberships")
    op.drop_table("shop_memberships")
