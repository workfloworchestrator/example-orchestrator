from orchestrator.domain import SUBSCRIPTION_MODEL_REGISTRY

from products.product_types.core_link import CoreLink
from products.product_types.node import Node
from products.product_types.port import Port

SUBSCRIPTION_MODEL_REGISTRY.update(
    {
        "node Cisco": Node,
        "node Nokia": Node,
        "port 10G": Port,
        "port 100G": Port,
        "Core Link 10G": CoreLink,
        "Core Link 100G": CoreLink,
    }
)
