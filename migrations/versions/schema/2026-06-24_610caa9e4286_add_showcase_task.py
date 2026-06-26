"""Add showcase task.

Revision ID: 610caa9e4286
Revises: b3a1c7e9f012
Create Date: 2026-06-24

"""

import sqlalchemy as sa
from alembic import op
from orchestrator.core.migrations.helpers import delete_workflow
from orchestrator.core.targets import Target

# revision identifiers, used by Alembic.
revision = "610caa9e4286"
down_revision = "b3a1c7e9f012"
branch_labels = None
depends_on = None

new_workflows = [
    {
        "name": "task_showcase",
        "target": Target.SYSTEM,
        "is_task": True,
        "description": "Component Showcase",
    },
]


def upgrade() -> None:
    conn = op.get_bind()
    for workflow in new_workflows:
        conn.execute(
            sa.text(
                """
                INSERT INTO workflows(name, target, is_task, description)
                VALUES (:name, :target, :is_task, :description)
                ON CONFLICT DO NOTHING
                """
            ),
            workflow,
        )


def downgrade() -> None:
    conn = op.get_bind()
    for workflow in new_workflows:
        delete_workflow(conn, workflow["name"])
