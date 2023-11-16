from typing import Optional

from orchestrator.domain.base import ProductBlockModel, serializable_property
from orchestrator.types import SubscriptionLifecycle

from products.product_blocks.node import (
    NodeBlock,
    NodeBlockInactive,
    NodeBlockProvisioning,
)


class CorePortBlockInactive(ProductBlockModel, product_block_name="CorePort"):
    port_name: Optional[str] = None
    ims_id: Optional[int] = None
    nrm_id: Optional[int] = None
    node: Optional[NodeBlockInactive] = None
    ipv6_ipam_id: Optional[int] = None


class CorePortBlockProvisioning(CorePortBlockInactive, lifecycle=[SubscriptionLifecycle.PROVISIONING]):
    port_name: Optional[str] = None
    ims_id: Optional[int] = None
    nrm_id: Optional[int] = None
    node: NodeBlockProvisioning
    ipv6_ipam_id: Optional[int] = None

    @serializable_property
    def title(self) -> str:
        # TODO: format correct title string
        return f"{self.name}"


class CorePortBlock(CorePortBlockProvisioning, lifecycle=[SubscriptionLifecycle.ACTIVE]):
    port_name: Optional[str] = None
    ims_id: int
    nrm_id: int
    node: NodeBlock
    ipv6_ipam_id: int
