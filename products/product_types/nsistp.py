# products/product_types/nsistp.py
from orchestrator.domain.base import SubscriptionModel
from orchestrator.types import SubscriptionLifecycle

from products.product_blocks.nsistp import (
    NsistpBlock,
    NsistpBlockInactive,
    NsistpBlockProvisioning,
)


class NsistpInactive(SubscriptionModel, is_base=True):
    nsistp: NsistpBlockInactive


class NsistpProvisioning(
    NsistpInactive, lifecycle=[SubscriptionLifecycle.PROVISIONING]
):
    nsistp: NsistpBlockProvisioning


class Nsistp(NsistpProvisioning, lifecycle=[SubscriptionLifecycle.ACTIVE]):
    nsistp: NsistpBlock
