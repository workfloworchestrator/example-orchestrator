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


from typing import Optional, TypeVar

from orchestrator.domain.base import (
    ProductBlockModel,
    SubscriptionInstanceList,
    serializable_property,
)
from orchestrator.types import SubscriptionLifecycle

from products.product_blocks.core_port import (
    CorePortBlock,
    CorePortBlockInactive,
    CorePortBlockProvisioning,
)

T = TypeVar("T", covariant=True)


class ListOfPorts(SubscriptionInstanceList[T]):
    min_items = 2
    max_items = 2


class CoreLinkBlockInactive(ProductBlockModel, product_block_name="CoreLink"):
    ports: ListOfPorts[CorePortBlockInactive]
    ims_id: Optional[int] = None
    ipv6_prefix_ipam_id: Optional[int] = None
    nrm_id: Optional[int] = None
    under_maintenance: Optional[bool] = None


class CoreLinkBlockProvisioning(CoreLinkBlockInactive, lifecycle=[SubscriptionLifecycle.PROVISIONING]):
    ports: ListOfPorts[CorePortBlockProvisioning]
    ims_id: Optional[int] = None
    ipv6_prefix_ipam_id: Optional[int] = None
    nrm_id: Optional[int] = None
    under_maintenance: bool

    @serializable_property
    def title(self) -> str:
        # TODO: format correct title string
        return f"{self.name}"


class CoreLinkBlock(CoreLinkBlockProvisioning, lifecycle=[SubscriptionLifecycle.ACTIVE]):
    ports: ListOfPorts[CorePortBlock]
    ims_id: int
    ipv6_prefix_ipam_id: int
    nrm_id: int
    under_maintenance: bool
