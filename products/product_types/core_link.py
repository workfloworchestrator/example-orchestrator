from enum import IntEnum

from orchestrator.domain.base import SubscriptionModel
from orchestrator.types import SubscriptionLifecycle

from products.product_blocks.core_link import (
    CoreLinkBlock,
    CoreLinkBlockInactive,
    CoreLinkBlockProvisioning,
)


class CoreLinkSpeed(IntEnum):
    """Speed of physical port in Mbit/s."""

    _10000 = 10000
    _100000 = 100000


class CoreLinkInactive(SubscriptionModel, is_base=True):
    speed: CoreLinkSpeed
    core_link: CoreLinkBlockInactive


class CoreLinkProvisioning(CoreLinkInactive, lifecycle=[SubscriptionLifecycle.PROVISIONING]):
    speed: CoreLinkSpeed
    core_link: CoreLinkBlockProvisioning


class CoreLink(CoreLinkProvisioning, lifecycle=[SubscriptionLifecycle.ACTIVE]):
    speed: CoreLinkSpeed
    core_link: CoreLinkBlock
