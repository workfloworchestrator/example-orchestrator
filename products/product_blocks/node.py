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


from orchestrator.domain.base import ProductBlockModel, serializable_property
from orchestrator.types import SubscriptionLifecycle

from products.product_blocks.shared.types import NodeStatus


class NodeBlockInactive(ProductBlockModel, product_block_name="Node"):
    role_id: int | None = None
    type_id: int | None = None
    site_id: int | None = None
    node_status: NodeStatus | None = None
    node_name: str | None = None
    node_description: str | None = None
    ims_id: int | None = None
    nrm_id: int | None = None
    ipv4_ipam_id: int | None = None
    ipv6_ipam_id: int | None = None


class NodeBlockProvisioning(NodeBlockInactive, lifecycle=[SubscriptionLifecycle.PROVISIONING]):
    role_id: int
    type_id: int
    site_id: int
    node_status: NodeStatus
    node_name: str | None = None
    node_description: str | None = None
    ims_id: int | None = None
    nrm_id: int | None = None
    ipv4_ipam_id: int | None = None
    ipv6_ipam_id: int | None = None

    @serializable_property
    def title(self) -> str:
        # TODO: format correct title string
        return f"{self.name}"


class NodeBlock(NodeBlockProvisioning, lifecycle=[SubscriptionLifecycle.ACTIVE]):
    role_id: int
    type_id: int
    site_id: int
    node_status: NodeStatus
    node_name: str | None = None
    node_description: str | None = None
    ims_id: int
    nrm_id: int
    ipv4_ipam_id: int
    ipv6_ipam_id: int
