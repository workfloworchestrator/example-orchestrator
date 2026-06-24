"""Add customer table and seed example customers.

Revision ID: b3a1c7e9f012
Revises: f8dc5901fe6d
Create Date: 2026-06-16

"""

from uuid import uuid4

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "b3a1c7e9f012"
down_revision = "f8dc5901fe6d"
branch_labels = None
depends_on = None

EXAMPLE_CUSTOMERS = [
    {"customer_id": str(uuid4()), "fullname": "SURF", "shortcode": "SURF"},
    {"customer_id": str(uuid4()), "fullname": "ESnet", "shortcode": "ESnet"},
    {"customer_id": str(uuid4()), "fullname": "GÉANT", "shortcode": "GEANT"},
]


def upgrade() -> None:
    customers_table = op.create_table(
        "customers",
        sa.Column("customer_id", sa.String(), nullable=False, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("fullname", sa.String(length=255), nullable=True),
        sa.Column("shortcode", sa.String(length=255), nullable=True),
        sa.PrimaryKeyConstraint("customer_id"),
    )
    op.create_index(op.f("ix_customers_shortcode"), "customers", ["shortcode"], unique=False)

    op.bulk_insert(customers_table, EXAMPLE_CUSTOMERS)


def downgrade() -> None:
    op.drop_index(op.f("ix_customers_shortcode"), table_name="customers")
    op.drop_table("customers")
