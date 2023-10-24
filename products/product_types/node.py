from orchestrator.domain.base import SubscriptionModel
from orchestrator.types import SubscriptionLifecycle, strEnum

from products.product_blocks.node import (
    NodeBlock,
    NodeBlockInactive,
    NodeBlockProvisioning,
)


class Node_Type(strEnum):
    Cisco = "Cisco"
    Nokia = "Nokia"


class NodeInactive(SubscriptionModel, is_base=True):
    node_type: Node_Type
    node: NodeBlockInactive


class NodeProvisioning(NodeInactive, lifecycle=[SubscriptionLifecycle.PROVISIONING]):
    node_type: Node_Type
    node: NodeBlockProvisioning


class Node(NodeProvisioning, lifecycle=[SubscriptionLifecycle.ACTIVE]):
    node_type: Node_Type
    node: NodeBlock
