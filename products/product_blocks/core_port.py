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


from typing import Optional

from orchestrator.domain.base import ProductBlockModel, serializable_property
from orchestrator.types import SubscriptionLifecycle

from products.product_blocks.node import (
    NodeBlock,
    NodeBlockInactive,
    NodeBlockProvisioning,
)


class CorePortBlockInactive(ProductBlockModel, product_block_name="CorePort"):
    port_name: Optional[str] = None
    enabled: Optional[bool] = True
    ims_id: Optional[int] = None
    nrm_id: Optional[int] = None
    node: Optional[NodeBlockInactive] = None
    ipv6_ipam_id: Optional[int] = None


class CorePortBlockProvisioning(CorePortBlockInactive, lifecycle=[SubscriptionLifecycle.PROVISIONING]):
    port_name: Optional[str] = None
    enabled: bool
    ims_id: Optional[int] = None
    nrm_id: Optional[int] = None
    node: NodeBlockProvisioning
    ipv6_ipam_id: Optional[int] = None

    @serializable_property
    def title(self) -> str:
        # TODO: format correct title string
        return f"{self.name}"


class CorePortBlock(CorePortBlockProvisioning, lifecycle=[SubscriptionLifecycle.ACTIVE]):
    port_name: Optional[str] = None
    enabled: bool
    ims_id: int
    nrm_id: int
    node: NodeBlock
    ipv6_ipam_id: int
