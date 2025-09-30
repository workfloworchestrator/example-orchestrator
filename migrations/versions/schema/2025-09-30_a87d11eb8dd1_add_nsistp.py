"""Add nsistp product.

Revision ID: a87d11eb8dd1
Revises: 0e8d17ce0f06
Create Date: 2025-09-30 15:50:36.882313

"""

from uuid import uuid4

from alembic import op
from orchestrator.migrations.helpers import create, create_workflow, delete, delete_workflow, ensure_default_workflows
from orchestrator.targets import Target

# revision identifiers, used by Alembic.
revision = "a87d11eb8dd1"
down_revision = "0e8d17ce0f06"
branch_labels = None
depends_on = None

new_products = {
    "products": {
        "nsistp": {
            "product_id": uuid4(),
            "product_type": "Nsistp",
            "description": "NSISTP",
            "tag": "NSISTP",
            "status": "active",
            "root_product_block": "Nsistp",
            "fixed_inputs": {},
        },
    },
    "product_blocks": {
        "Nsistp": {
            "product_block_id": uuid4(),
            "description": "nsistp product block",
            "tag": "NSISTP",
            "status": "active",
            "resources": {
                "topology": "Topology type or identifier for the service instance",
                "stp_id": "Unique identifier for the Service Termination Point",
                "stp_description": "Description of the Service Termination Point",
                "is_alias_in": "Indicates if the incoming SAP is an alias",
                "is_alias_out": "Indicates if the outgoing SAP is an alias",
                "expose_in_topology": "Whether to expose this STP in the topology view",
                "bandwidth": "Requested bandwidth for the service instance (in Mbps)",
            },
            "depends_on_block_relations": [
                "SAP",
            ],
        },
    },
    "workflows": {},
}

new_workflows = [
    {
        "name": "create_nsistp",
        "target": Target.CREATE,
        "is_task": False,
        "description": "Create nsistp",
        "product_type": "Nsistp",
    },
    {
        "name": "modify_nsistp",
        "target": Target.MODIFY,
        "is_task": False,
        "description": "Modify nsistp",
        "product_type": "Nsistp",
    },
    {
        "name": "terminate_nsistp",
        "target": Target.TERMINATE,
        "is_task": False,
        "description": "Terminate nsistp",
        "product_type": "Nsistp",
    },
    {
        "name": "validate_nsistp",
        "target": Target.VALIDATE,
        "is_task": True,
        "description": "Validate nsistp",
        "product_type": "Nsistp",
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
