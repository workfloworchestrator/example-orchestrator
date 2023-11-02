from enum import IntEnum

from orchestrator.domain.base import SubscriptionModel
from orchestrator.types import SubscriptionLifecycle

from products.product_blocks.port import (
    PortBlock,
    PortBlockInactive,
    PortBlockProvisioning,
)


class PortSpeed(IntEnum):
    """Speed of physical port in Mbit/s."""

    _1000 = 1000
    _10000 = 10000
    _40000 = 40000
    _100000 = 100000
    _400000 = 400000


class PortInactive(SubscriptionModel, is_base=True):
    speed: PortSpeed
    port: PortBlockInactive


class PortProvisioning(PortInactive, lifecycle=[SubscriptionLifecycle.PROVISIONING]):
    speed: PortSpeed
    port: PortBlockProvisioning


class Port(PortProvisioning, lifecycle=[SubscriptionLifecycle.ACTIVE]):
    speed: PortSpeed
    port: PortBlock
