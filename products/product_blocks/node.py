from typing import Optional

from orchestrator.domain.base import ProductBlockModel, serializable_property
from orchestrator.types import SubscriptionLifecycle


class NodeBlockInactive(ProductBlockModel, product_block_name="Node"):
    role_id: Optional[int] = None
    type_id: Optional[int] = None
    site_id: Optional[int] = None
    node_status: Optional[str] = None  # TODO: should be NodeStatus
    node_name: Optional[str] = None
    node_description: Optional[str] = None
    ims_id: Optional[int] = None
    nrm_id: Optional[int] = None
    ipv4_ipam_id: Optional[int] = None
    ipv6_ipam_id: Optional[int] = None


class NodeBlockProvisioning(NodeBlockInactive, lifecycle=[SubscriptionLifecycle.PROVISIONING]):
    role_id: int
    type_id: int
    site_id: int
    node_status: str  # TODO: should be NodeStatus
    node_name: Optional[str] = None
    node_description: Optional[str] = None
    ims_id: Optional[int] = None
    nrm_id: Optional[int] = None
    ipv4_ipam_id: Optional[int] = None
    ipv6_ipam_id: Optional[int] = None

    @serializable_property
    def title(self) -> str:
        # TODO: format correct title string
        return f"{self.name}"


class NodeBlock(NodeBlockProvisioning, lifecycle=[SubscriptionLifecycle.ACTIVE]):
    role_id: int
    type_id: int
    site_id: int
    node_status: str  # TODO: should be NodeStatus
    node_name: Optional[str] = None
    node_description: Optional[str] = None
    ims_id: int
    nrm_id: int
    ipv4_ipam_id: int
    ipv6_ipam_id: int
