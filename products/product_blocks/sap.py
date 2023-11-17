from typing import Optional

from orchestrator.domain.base import ProductBlockModel, serializable_property
from orchestrator.types import SubscriptionLifecycle

from products.product_blocks.port import (
    PortBlock,
    PortBlockInactive,
    PortBlockProvisioning,
)


class SAPBlockInactive(ProductBlockModel, product_block_name="SAP"):
    port: Optional[PortBlockInactive] = None
    vlan: Optional[str] = None
    ims_id: Optional[int] = None


class SAPBlockProvisioning(SAPBlockInactive, lifecycle=[SubscriptionLifecycle.PROVISIONING]):
    port: PortBlockProvisioning
    vlan: str
    ims_id: Optional[int] = None

    @serializable_property
    def title(self) -> str:
        # TODO: format correct title string
        return f"{self.name}"


class SAPBlock(SAPBlockProvisioning, lifecycle=[SubscriptionLifecycle.ACTIVE]):
    port: PortBlock
    vlan: str
    ims_id: int
