"""Add port product.

Revision ID: c044b0da4126
Revises: a84ca2e5e4db
Create Date: 2023-11-02 10:46:33.372496

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

from products.product_types.port import PortSpeed

# revision identifiers, used by Alembic.
revision = "c044b0da4126"
down_revision = "a84ca2e5e4db"
branch_labels = None
depends_on = None

new_products = {
    "products": {
        "port 10G": {
            "product_id": uuid4(),
            "product_type": "Port",
            "description": "Network port",
            "tag": "PORT",
            "status": "active",
            "root_product_block": "Port",
            "fixed_inputs": {
                "speed": PortSpeed._10000.value,
            },
        },
        "port 100G": {
            "product_id": uuid4(),
            "product_type": "Port",
            "description": "Network port",
            "tag": "PORT",
            "status": "active",
            "root_product_block": "Port",
            "fixed_inputs": {
                "speed": PortSpeed._100000.value,
            },
        },
    },
    "product_blocks": {
        "Port": {
            "product_block_id": uuid4(),
            "description": "port product block",
            "tag": "PORT",
            "status": "active",
            "resources": {
                "port_name": "Unique name of the port on the device",
                "port_type": "Type of the port",
                "port_description": "Description of the port",
                "port_mode": "Mode of the port, either untagged, tagged or a link_member (in an aggregate)",
                "auto_negotiation": "is Ethernet auto negotiation enabled or not",
                "lldp": "is Link Llayer Discovery Protocol enabled or not",
                "enabled": "is port enabled in inventory management system?",
                "ims_id": "ID of the node in the inventory management system",
                "nrm_id": "ID of the node in the network resource manager",
            },
            "depends_on_block_relations": [
                "Node",
            ],
        },
    },
    "workflows": {},
}

new_workflows = [
    {
        "name": "create_port",
        "target": Target.CREATE,
        "description": "Create port",
        "product_type": "Port",
    },
    {
        "name": "modify_port",
        "target": Target.MODIFY,
        "description": "Modify port",
        "product_type": "Port",
    },
    {
        "name": "terminate_port",
        "target": Target.TERMINATE,
        "description": "Terminate port",
        "product_type": "Port",
    },
    {
        "name": "validate_port",
        "target": Target.SYSTEM,
        "description": "Validate port",
        "product_type": "Port",
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
