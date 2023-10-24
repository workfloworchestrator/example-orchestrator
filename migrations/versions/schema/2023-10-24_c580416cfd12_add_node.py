"""Add node product.

Revision ID: c580416cfd12
Revises: a77227fe5455
Create Date: 2023-10-24 15:39:47.037726

"""
from uuid import uuid4

from alembic import op
from orchestrator.migrations.helpers import (
    create,
    create_workflow,
    delete,
    delete_workflow,
    ensure_default_workflows,
)
from orchestrator.targets import Target

# revision identifiers, used by Alembic.
revision = "c580416cfd12"
down_revision = "a77227fe5455"
branch_labels = None
depends_on = None

new_products = {
    "products": {
        "node Cisco": {
            "product_id": uuid4(),
            "product_type": "Node",
            "description": "Network node",
            "tag": "NODE",
            "status": "active",
            "product_blocks": [
                "Node",
            ],
            "fixed_inputs": {
                "node_type": "Cisco",
            },
        },
        "node Nokia": {
            "product_id": uuid4(),
            "product_type": "Node",
            "description": "Network node",
            "tag": "NODE",
            "status": "active",
            "product_blocks": [
                "Node",
            ],
            "fixed_inputs": {
                "node_type": "Nokia",
            },
        },
    },
    "product_blocks": {
        "Node": {
            "product_block_id": uuid4(),
            "description": "node product block",
            "tag": "NODE",
            "status": "active",
            "resources": {
                "node_name": "Unique name of the node",
                "role": "Role of the node in the network",
                "node_description": "Description of the node",
                "type": "Type of the node",
                "site": "Site where the node is located",
                "status": "Operational status of the node",
                "ims_id": "ID of the node in the inventory management system",
                "nrm_id": "ID of the node in the network resource manager",
                "ipv4_ipam_id": "ID of the node’s iPv4 loopback address in IPAM",
                "ipv6_ipam_id": "ID of the node’s iPv6 loopback address in IPAM",
            },
            "depends_on_block_relations": [],
        },
    },
    "workflows": {},
}

new_workflows = [
    {
        "name": "create_node",
        "target": Target.CREATE,
        "description": "Create node",
        "product_type": "Node",
    },
    {
        "name": "modify_node",
        "target": Target.MODIFY,
        "description": "Modify node",
        "product_type": "Node",
    },
    {
        "name": "terminate_node",
        "target": Target.TERMINATE,
        "description": "Terminate node",
        "product_type": "Node",
    },
    {
        "name": "validate_node",
        "target": Target.SYSTEM,
        "description": "Validate node",
        "product_type": "Node",
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
