"""support fractional stock and invoice quantities

Revision ID: b7e2f4a1c9d0
Revises: af4e7c2d91b0
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b7e2f4a1c9d0"
down_revision: Union[str, Sequence[str], None] = "af4e7c2d91b0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("products") as batch:
        batch.alter_column("stock", existing_type=sa.Integer(), type_=sa.Numeric(12, 3), existing_nullable=False)
        batch.alter_column("min_stock", existing_type=sa.Integer(), type_=sa.Numeric(12, 3), existing_nullable=False)
    with op.batch_alter_table("invoice_items") as batch:
        batch.alter_column("quantity", existing_type=sa.Integer(), type_=sa.Numeric(12, 3), existing_nullable=False)


def downgrade() -> None:
    with op.batch_alter_table("invoice_items") as batch:
        batch.alter_column("quantity", existing_type=sa.Numeric(12, 3), type_=sa.Integer(), existing_nullable=False)
    with op.batch_alter_table("products") as batch:
        batch.alter_column("min_stock", existing_type=sa.Numeric(12, 3), type_=sa.Integer(), existing_nullable=False)
        batch.alter_column("stock", existing_type=sa.Numeric(12, 3), type_=sa.Integer(), existing_nullable=False)
