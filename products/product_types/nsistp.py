# products/product_types/nsistp.py
from orchestrator.domain.base import SubscriptionModel
from orchestrator.types import SubscriptionLifecycle

from products.product_blocks.nsistp import (
    NsistpBlock,
    NsistpBlockInactive,
    NsistpBlockProvisioning,
)
from workflows.nsistp.shared.shared import CustomVlanRanges


class NsistpInactive(SubscriptionModel, is_base=True):
    nsistp: NsistpBlockInactive


class NsistpProvisioning(
    NsistpInactive, lifecycle=[SubscriptionLifecycle.PROVISIONING]
):
    nsistp: NsistpBlockProvisioning


class Nsistp(NsistpProvisioning, lifecycle=[SubscriptionLifecycle.ACTIVE]):
    nsistp: NsistpBlock

    @property
    def vlan_range(self) -> CustomVlanRanges:
        return self.nsistp.sap.vlan
