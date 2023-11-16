from typing import Optional, TypeVar

from orchestrator.domain.base import (
    ProductBlockModel,
    SubscriptionInstanceList,
    serializable_property,
)
from orchestrator.types import SubscriptionLifecycle

from products.product_blocks.core_port import (
    CorePortBlock,
    CorePortBlockInactive,
    CorePortBlockProvisioning,
)

T = TypeVar("T", covariant=True)


class ListOfPorts(SubscriptionInstanceList[T]):
    min_items = 2
    max_items = 2


class CoreLinkBlockInactive(ProductBlockModel, product_block_name="CoreLink"):
    ports: ListOfPorts[CorePortBlockInactive]
    ims_id: Optional[int] = None
    ipv6_prefix_ipam_id: Optional[int] = None
    nrm_id: Optional[int] = None
    under_maintenance: Optional[bool] = None


class CoreLinkBlockProvisioning(CoreLinkBlockInactive, lifecycle=[SubscriptionLifecycle.PROVISIONING]):
    ports: ListOfPorts[CorePortBlockProvisioning]
    ims_id: Optional[int] = None
    ipv6_prefix_ipam_id: Optional[int] = None
    nrm_id: Optional[int] = None
    under_maintenance: bool

    @serializable_property
    def title(self) -> str:
        # TODO: format correct title string
        return f"{self.name}"


class CoreLinkBlock(CoreLinkBlockProvisioning, lifecycle=[SubscriptionLifecycle.ACTIVE]):
    ports: ListOfPorts[CorePortBlock]
    ims_id: int
    ipv6_prefix_ipam_id: int
    nrm_id: int
    under_maintenance: bool
