"""Update validate targets.

Revision ID: bc54616fefcf
Revises: 0e8d17ce0f06
Create Date: 2025-08-26 22:55:28.955536

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "bc54616fefcf"
down_revision = "0e8d17ce0f06"
branch_labels = None
depends_on = None

# Per 4.0 migration guide:
# https://workfloworchestrator.org/orchestrator-core/migration-guide/4.0/


def upgrade() -> None:
    conn = op.get_bind()
    conn.execute(
        sa.text(
            """
UPDATE workflows
SET target = 'VALIDATE'
WHERE name LIKE 'validate_%';
    """
        )
    )
    conn.execute(
        sa.text(
            """
UPDATE workflows
SET is_task = TRUE
WHERE target IN ('SYSTEM', 'VALIDATE');
    """
        )
    )


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(
        sa.text(
            """
UPDATE workflows
SET target = 'SYSTEM'
WHERE name LIKE 'validate_%';
    """
        )
    )
    conn.execute(
        sa.text(
            """
UPDATE workflows
SET is_task = null
WHERE target = 'SYSTEM';
    """
        )
    )
