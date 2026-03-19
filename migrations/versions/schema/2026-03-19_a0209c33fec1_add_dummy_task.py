"""add dummy task.

Revision ID: a0209c33fec1
Revises: f8dc5901fe6d
Create Date: 2026-03-19 11:33:25.886387

"""
from alembic import op
from orchestrator.migrations.helpers import create_task, delete_workflow

# revision identifiers, used by Alembic.
revision = 'a0209c33fec1'
down_revision = 'f8dc5901fe6d'
branch_labels = None
depends_on = None

new_tasks = [
    {
        "name": "task_perform_dummy_task",
        "description": "Test new Task decorator",
    }
]

def upgrade() -> None:
    conn = op.get_bind()
    for task in new_tasks:
        create_task(conn, task)


def downgrade() -> None:
    conn = op.get_bind()
    for task in new_tasks:
        delete_workflow(conn, task["name"])
