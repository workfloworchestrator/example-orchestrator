"""Reconcile workflows L2VPN.

Revision ID: 0e8d17ce0f06
Revises: d946c20663d3
Create Date: 2025-08-28 13:02:03.796540

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "0e8d17ce0f06"
down_revision = "d946c20663d3"
branch_labels = None
depends_on = None


from orchestrator.migrations.helpers import create_workflow, delete_workflow

new_workflows = [
    {
        "name": "reconcile_l2vpn",
        "target": "RECONCILE",
        "description": "Reconcile SN8 L2Vpn",
        "product_type": "L2vpn",
    }
]


def upgrade() -> None:
    conn = op.get_bind()
    for workflow in new_workflows:
        create_workflow(conn, workflow)


def downgrade() -> None:
    conn = op.get_bind()
    for workflow in new_workflows:
        delete_workflow(conn, workflow["name"])
