from typing import Optional

from orchestrator.domain.base import ProductBlockModel, serializable_property
from orchestrator.types import SubscriptionLifecycle
from pydantic_forms.types import strEnum

from products.product_blocks.node import (
    NodeBlock,
    NodeBlockInactive,
    NodeBlockProvisioning,
)


class PortMode(strEnum):
    """Valid port modes."""

    TAGGED = "tagged"
    UNTAGGED = "untagged"
    LINK_MEMBER = "link member"


class PortBlockInactive(ProductBlockModel, product_block_name="Port"):
    port_name: Optional[str] = None
    port_type: Optional[str] = None
    port_description: Optional[str] = None
    port_mode: Optional[str] = None
    auto_negotiation: Optional[bool] = None
    lldp: Optional[bool] = None
    enabled: Optional[bool] = None
    node: Optional[NodeBlockInactive] = None
    ims_id: Optional[int] = None
    nrm_id: Optional[int] = None


class PortBlockProvisioning(PortBlockInactive, lifecycle=[SubscriptionLifecycle.PROVISIONING]):
    port_name: str
    port_type: str
    port_description: Optional[str] = None
    port_mode: str
    auto_negotiation: bool
    lldp: bool
    enabled: bool
    node: NodeBlockProvisioning
    ims_id: int
    nrm_id: Optional[int] = None

    @serializable_property
    def title(self) -> str:
        # TODO: format correct title string
        return f"{self.name}"


class PortBlock(PortBlockProvisioning, lifecycle=[SubscriptionLifecycle.ACTIVE]):
    port_name: str
    port_type: str
    port_description: Optional[str] = None
    port_mode: str
    auto_negotiation: bool
    lldp: bool
    enabled: bool
    node: NodeBlock
    ims_id: int
    nrm_id: int
