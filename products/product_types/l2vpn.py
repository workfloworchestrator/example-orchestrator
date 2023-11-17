from orchestrator.domain.base import SubscriptionModel
from orchestrator.types import SubscriptionLifecycle

from products.product_blocks.virtual_circuit import (
    VirtualCircuitBlock,
    VirtualCircuitBlockInactive,
    VirtualCircuitBlockProvisioning,
)


class L2vpnInactive(SubscriptionModel, is_base=True):
    virtual_circuit: VirtualCircuitBlockInactive


class L2vpnProvisioning(L2vpnInactive, lifecycle=[SubscriptionLifecycle.PROVISIONING]):
    virtual_circuit: VirtualCircuitBlockProvisioning


class L2vpn(L2vpnProvisioning, lifecycle=[SubscriptionLifecycle.ACTIVE]):
    virtual_circuit: VirtualCircuitBlock
