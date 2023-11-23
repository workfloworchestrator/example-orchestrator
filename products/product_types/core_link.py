# Copyright 2019-2023 SURF.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


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
