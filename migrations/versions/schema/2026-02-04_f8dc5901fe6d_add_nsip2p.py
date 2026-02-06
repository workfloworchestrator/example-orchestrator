"""Add nsip2p product.

Revision ID: f8dc5901fe6d
Revises: a87d11eb8dd1
Create Date: 2026-02-04 14:18:16.704092

"""

from uuid import uuid4

from alembic import op
from orchestrator.migrations.helpers import create, create_workflow, delete, delete_workflow, ensure_default_workflows
from orchestrator.targets import Target

# revision identifiers, used by Alembic.
revision = "f8dc5901fe6d"
down_revision = "a87d11eb8dd1"
branch_labels = None
depends_on = None

new_products = {
    "products": {
        "nsip2p": {
            "product_id": uuid4(),
            "product_type": "Nsip2p",
            "description": "Network Service Interface Point-to-Point",
            "tag": "NSIP2P",
            "status": "active",
            "root_product_block": "VirtualCircuit",
            "fixed_inputs": {},
        },
    },
    "product_blocks": {},
    "workflows": {},
}

new_workflows = [
    {
        "name": "create_nsip2p",
        "target": Target.CREATE,
        "is_task": False,
        "description": "Create nsip2p",
        "product_type": "Nsip2p",
    },
    {
        "name": "modify_nsip2p",
        "target": Target.MODIFY,
        "is_task": False,
        "description": "Modify nsip2p",
        "product_type": "Nsip2p",
    },
    {
        "name": "terminate_nsip2p",
        "target": Target.TERMINATE,
        "is_task": False,
        "description": "Terminate nsip2p",
        "product_type": "Nsip2p",
    },
    {
        "name": "validate_nsip2p",
        "target": Target.VALIDATE,
        "is_task": True,
        "description": "Validate nsip2p",
        "product_type": "Nsip2p",
    },
]


def upgrade() -> None:
    conn = op.get_bind()
    create(conn, new_products)
    for workflow in new_workflows:
        create_workflow(conn, workflow)
    ensure_default_workflows(conn)


def downgrade() -> None:
    conn = op.get_bind()
    for workflow in new_workflows:
        delete_workflow(conn, workflow["name"])

    delete(conn, new_products)
