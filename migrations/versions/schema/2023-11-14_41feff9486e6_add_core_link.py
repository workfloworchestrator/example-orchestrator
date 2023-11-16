"""Add core_link product.

Revision ID: 41feff9486e6
Revises: c044b0da4126
Create Date: 2023-11-14 16:25:29.728150

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

from products.product_types.core_link import CoreLinkSpeed

# revision identifiers, used by Alembic.
revision = "41feff9486e6"
down_revision = "c044b0da4126"
branch_labels = None
depends_on = None

new_products = {
    "products": {
        "Core Link 10G": {
            "product_id": uuid4(),
            "product_type": "CoreLink",
            "description": "Core link",
            "tag": "CORE_LINK",
            "status": "active",
            "product_blocks": [
                "CoreLink",
                "CorePort",
            ],
            "fixed_inputs": {
                "speed": CoreLinkSpeed._10000.value,
            },
        },
        "Core Link 100G": {
            "product_id": uuid4(),
            "product_type": "CoreLink",
            "description": "Core link",
            "tag": "CORE_LINK",
            "status": "active",
            "product_blocks": [
                "CoreLink",
                "CorePort",
            ],
            "fixed_inputs": {
                "speed": CoreLinkSpeed._100000.value,
            },
        },
    },
    "product_blocks": {
        "CoreLink": {
            "product_block_id": uuid4(),
            "description": "core link product block",
            "tag": "CORE_LINK",
            "status": "active",
            "resources": {
                "ports": "core ports",
                "ims_id": "ID of the core link in the inventory management system",
                "nrm_id": "ID of the core link in the network resource manager",
                "under_maintenance": "core link under maintenance?",
            },
            "depends_on_block_relations": [],
        },
        "CorePort": {
            "product_block_id": uuid4(),
            "description": "core port product block",
            "tag": "CORE_PORT",
            "status": "active",
            "resources": {
                "port_name": "Unique name of the port on the device",
                "ims_id": "ID of the port in the inventory management system",
                "nrm_id": "ID of the port in the network resource manager",
                "node": "link to the Node product block the port is residing on",
                "ipv6_ipam_id": "ID of the port&#39;s IPv6 address in IPAM",
            },
            "depends_on_block_relations": [],
        },
    },
    "workflows": {},
}

new_workflows = [
    {
        "name": "create_core_link",
        "target": Target.CREATE,
        "description": "Create core_link",
        "product_type": "CoreLink",
    },
    {
        "name": "modify_core_link",
        "target": Target.MODIFY,
        "description": "Modify core_link",
        "product_type": "CoreLink",
    },
    {
        "name": "terminate_core_link",
        "target": Target.TERMINATE,
        "description": "Terminate core_link",
        "product_type": "CoreLink",
    },
    {
        "name": "validate_core_link",
        "target": Target.SYSTEM,
        "description": "Validate core_link",
        "product_type": "CoreLink",
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
