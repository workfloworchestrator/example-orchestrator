# products/product_blocks/nsistp.py

from orchestrator.domain.base import ProductBlockModel
from orchestrator.types import SubscriptionLifecycle
from pydantic import computed_field

from products.product_blocks.sap import SAPBlock, SAPBlockInactive, SAPBlockProvisioning

# NOTE: ListOfSap is not required here???
# ListOfSap = Annotated[list[SI], Len(min_length=2, max_length=8)]


class NsistpBlockInactive(ProductBlockModel, product_block_name="Nsistp"):
    sap: SAPBlockInactive
    topology: str | None = None
    stp_id: str | None = None
    stp_description: str | None = None
    is_alias_in: str | None = None
    is_alias_out: str | None = None
    expose_in_topology: bool | None = None
    bandwidth: int | None = None


class NsistpBlockProvisioning(
    NsistpBlockInactive, lifecycle=[SubscriptionLifecycle.PROVISIONING]
):
    sap: SAPBlockProvisioning
    topology: str
    stp_id: str
    stp_description: str | None = None
    is_alias_in: str | None = None
    is_alias_out: str | None = None
    expose_in_topology: bool | None = None
    bandwidth: int | None = None

    @computed_field
    @property
    def title(self) -> str:
        # TODO: format correct title string
        return f"{self.name}"


class NsistpBlock(NsistpBlockProvisioning, lifecycle=[SubscriptionLifecycle.ACTIVE]):
    sap: SAPBlock
    topology: str
    stp_id: str
    stp_description: str | None = None
    is_alias_in: str | None = None
    is_alias_out: str | None = None
    expose_in_topology: bool | None = None
    bandwidth: int | None = None
