"""add Netbox tasks.

Revision ID: d946c20663d3
Revises: e2a0fed2a4c7
Create Date: 2023-12-04 17:30:42.545271

"""
import sqlalchemy as sa
from alembic import op
from orchestrator.migrations.helpers import delete_workflow
from orchestrator.targets import Target

# revision identifiers, used by Alembic.
revision = "d946c20663d3"
down_revision = "e2a0fed2a4c7"
branch_labels = None
depends_on = None

tasks = [
    {
        "name": "task_bootstrap_netbox",
        "target": Target.SYSTEM,
        "description": "Netbox Bootstrap",
    },
    {
        "name": "task_wipe_netbox",
        "target": Target.SYSTEM,
        "description": "Netbox Wipe",
    },
]


def upgrade() -> None:
    conn = op.get_bind()
    for task in tasks:
        conn.execute(
            sa.text(
                """INSERT INTO workflows(name, target, description) VALUES (:name, :target, :description)
                   ON CONFLICT DO NOTHING"""
            ),
            task,
        )


def downgrade() -> None:
    conn = op.get_bind()
    for task in tasks:
        delete_workflow(conn, task["name"])
