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


from orchestrator.domain.base import ProductBlockModel
from orchestrator.types import SubscriptionLifecycle
from pydantic import computed_field

from products.product_blocks.node import (
    NodeBlock,
    NodeBlockInactive,
    NodeBlockProvisioning,
)


class CorePortBlockInactive(ProductBlockModel, product_block_name="CorePort"):
    port_name: str | None = None
    enabled: bool | None = True
    ims_id: int | None = None
    nrm_id: int | None = None
    node: NodeBlockInactive | None = None
    ipv6_ipam_id: int | None = None


class CorePortBlockProvisioning(CorePortBlockInactive, lifecycle=[SubscriptionLifecycle.PROVISIONING]):
    port_name: str | None = None
    enabled: bool
    ims_id: int | None = None
    nrm_id: int | None = None
    node: NodeBlockProvisioning
    ipv6_ipam_id: int | None = None

    @computed_field  # type: ignore[misc]
    @property
    def title(self) -> str:
        return f"core port {self.port_name} on {self.node.node_name}"


class CorePortBlock(CorePortBlockProvisioning, lifecycle=[SubscriptionLifecycle.ACTIVE]):
    port_name: str | None = None
    enabled: bool
    ims_id: int
    nrm_id: int
    node: NodeBlock
    ipv6_ipam_id: int
