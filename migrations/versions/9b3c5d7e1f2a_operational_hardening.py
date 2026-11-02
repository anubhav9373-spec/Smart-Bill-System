"""add audit events and invoice number protection

Revision ID: 9b3c5d7e1f2a
Revises: 8a2f4e1c6b7d
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "9b3c5d7e1f2a"
down_revision: Union[str, Sequence[str], None] = "8a2f4e1c6b7d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "audit_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("shop_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("action", sa.String(length=80), nullable=False),
        sa.Column("target_type", sa.String(length=50), nullable=False),
        sa.Column("target_id", sa.String(length=80), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["shop_id"], ["shops.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_audit_events_shop_id", "audit_events", ["shop_id"], unique=False)
    op.create_index("ix_audit_events_user_id", "audit_events", ["user_id"], unique=False)
    with op.batch_alter_table("invoices") as batch:
        batch.create_unique_constraint("uq_invoice_shop_number", ["shop_id", "invoice_number"])


def downgrade() -> None:
    with op.batch_alter_table("invoices") as batch:
        batch.drop_constraint("uq_invoice_shop_number", type_="unique")
    op.drop_index("ix_audit_events_user_id", table_name="audit_events")
    op.drop_index("ix_audit_events_shop_id", table_name="audit_events")
    op.drop_table("audit_events")
