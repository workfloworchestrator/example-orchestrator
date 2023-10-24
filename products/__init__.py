from orchestrator.domain import SUBSCRIPTION_MODEL_REGISTRY

from products.product_types.node import Node

SUBSCRIPTION_MODEL_REGISTRY.update(
    {
        "node Cisco": Node,
        "node Nokia": Node,
        }
)  # fmt:skip
