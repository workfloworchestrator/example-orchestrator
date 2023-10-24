from typing import Optional

from orchestrator.domain.base import ProductBlockModel, serializable_property
from orchestrator.types import SubscriptionLifecycle


class NodeBlockInactive(ProductBlockModel, product_block_name="Node"):
    role: Optional[str] = None
    type: Optional[str] = None
    site: Optional[str] = None
    status: Optional[str] = None
    node_name: Optional[str] = None
    node_description: Optional[str] = None
    ims_id: Optional[int] = None
    nrm_id: Optional[int] = None
    ipv4_ipam_id: Optional[int] = None
    ipv6_ipam_id: Optional[int] = None


class NodeBlockProvisioning(NodeBlockInactive, lifecycle=[SubscriptionLifecycle.PROVISIONING]):
    role: str
    type: str
    site: str
    status: str
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
    role: str
    type: str
    site: str
    status: str
    node_name: Optional[str] = None
    node_description: Optional[str] = None
    ims_id: int
    nrm_id: int
    ipv4_ipam_id: int
    ipv6_ipam_id: int
