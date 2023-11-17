from typing import Optional, TypeVar

from orchestrator.domain.base import (
    ProductBlockModel,
    SubscriptionInstanceList,
    serializable_property,
)
from orchestrator.types import SubscriptionLifecycle

from products.product_blocks.sap import SAPBlock, SAPBlockInactive, SAPBlockProvisioning

T = TypeVar("T", covariant=True)


class ListOfSaps(SubscriptionInstanceList[T]):
    min_items = 2
    max_items = 8


class VirtualCircuitBlockInactive(ProductBlockModel, product_block_name="VirtualCircuit"):
    saps: ListOfSaps[SAPBlockInactive]
    speed: Optional[int] = None
    speed_policer: Optional[bool] = None
    ims_id: Optional[int] = None
    nrm_id: Optional[int] = None


class VirtualCircuitBlockProvisioning(VirtualCircuitBlockInactive, lifecycle=[SubscriptionLifecycle.PROVISIONING]):
    saps: ListOfSaps[SAPBlockProvisioning]
    speed: int
    speed_policer: bool
    ims_id: Optional[int] = None
    nrm_id: Optional[int] = None

    @serializable_property
    def title(self) -> str:
        # TODO: format correct title string
        return f"{self.name}"


class VirtualCircuitBlock(VirtualCircuitBlockProvisioning, lifecycle=[SubscriptionLifecycle.ACTIVE]):
    saps: ListOfSaps[SAPBlock]
    speed: int
    speed_policer: bool
    ims_id: int
    nrm_id: int
