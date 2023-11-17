"""Add l2vpn product.

Revision ID: e2a0fed2a4c7
Revises: 1faddadd7aae
Create Date: 2023-11-17 10:59:41.544653

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
revision = "e2a0fed2a4c7"
down_revision = "1faddadd7aae"
branch_labels = None
depends_on = None

new_products = {
    "products": {
        "l2vpn": {
            "product_id": uuid4(),
            "product_type": "L2vpn",
            "description": "L2VPN",
            "tag": "L2VPN",
            "status": "active",
            "product_blocks": [
                "VirtualCircuit",
                "SAP",
            ],
            "fixed_inputs": {},
        },
    },
    "product_blocks": {
        "VirtualCircuit": {
            "product_block_id": uuid4(),
            "description": "virtual circuit product block",
            "tag": "VC",
            "status": "active",
            "resources": {
                "saps": "Virtual circuit service access points",
                "speed": "speed of the L2VPN im Mbit/s",
                "speed_policer": "speed policer active?",
                "ims_id": "ID of the L2VPN in the inventory management system",
                "nrm_id": "ID of the L2VPN in the network resource manager",
            },
            "depends_on_block_relations": [],
        },
        "SAP": {
            "product_block_id": uuid4(),
            "description": "service access point",
            "tag": "SAP",
            "status": "active",
            "resources": {
                "port": "Link to Port product block",
                "vlan": "VLAN ID on port",
                "ims_id": "ID of the SAP in the inventory management system",
            },
            "depends_on_block_relations": [],
        },
    },
    "workflows": {},
}

new_workflows = [
    {
        "name": "create_l2vpn",
        "target": Target.CREATE,
        "description": "Create l2vpn",
        "product_type": "L2vpn",
    },
    {
        "name": "modify_l2vpn",
        "target": Target.MODIFY,
        "description": "Modify l2vpn",
        "product_type": "L2vpn",
    },
    {
        "name": "terminate_l2vpn",
        "target": Target.TERMINATE,
        "description": "Terminate l2vpn",
        "product_type": "L2vpn",
    },
    {
        "name": "validate_l2vpn",
        "target": Target.SYSTEM,
        "description": "Validate l2vpn",
        "product_type": "L2vpn",
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
