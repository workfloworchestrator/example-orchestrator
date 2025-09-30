"""Add core_link product.

Revision ID: 1faddadd7aae
Revises: c044b0da4126
Create Date: 2023-11-16 16:40:52.193565

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
revision = "1faddadd7aae"
down_revision = "c044b0da4126"
branch_labels = None
depends_on = None

new_products = {
    "products": {
        "core link 10G": {
            "product_id": uuid4(),
            "product_type": "CoreLink",
            "description": "Core link",
            "tag": "CORE_LINK",
            "status": "active",
            "root_product_block": "CoreLink",
            "fixed_inputs": {
                "speed": CoreLinkSpeed._10000.value,
            },
        },
        "core link 100G": {
            "product_id": uuid4(),
            "product_type": "CoreLink",
            "description": "Core link",
            "tag": "CORE_LINK",
            "status": "active",
            "root_product_block": "CoreLink",
            "fixed_inputs": {
                "speed": CoreLinkSpeed._100000.value,
            },
        },
    },
    "product_blocks": {
        "CorePort": {
            "product_block_id": uuid4(),
            "description": "core port product block",
            "tag": "CORE_PORT",
            "status": "active",
            "resources": {
                "port_name": "Unique name of the port on the device",
                "enabled": "is port enabled in inventory management system?",
                "ims_id": "ID of the port in the inventory management system",
                "nrm_id": "ID of the port in the network resource manager",
                "ipv6_ipam_id": "ID of the port&#39;s IPv6 address in IPAM",
            },
            "depends_on_block_relations": [
                "Node",
            ],
        },
        "CoreLink": {
            "product_block_id": uuid4(),
            "description": "core link product block",
            "tag": "CORE_LINK",
            "status": "active",
            "resources": {
                "ims_id": "ID of the core link in the inventory management system",
                "ipv6_prefix_ipam_id": "IPAM ID of IP prefix used to number ports of this core link",
                "nrm_id": "ID of the core link in the network resource manager",
                "under_maintenance": "core link under maintenance?",
            },
            "depends_on_block_relations": [
                "CorePort",
            ],
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
