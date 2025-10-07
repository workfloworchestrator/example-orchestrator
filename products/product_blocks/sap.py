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

from products.product_blocks.port import (
    PortBlock,
    PortBlockInactive,
    PortBlockProvisioning,
)


class SAPBlockInactive(ProductBlockModel, product_block_name="SAP"):
    port: PortBlockInactive | None = None
    vlan: int | None = None
    ims_id: int | None = None


class SAPBlockProvisioning(
    SAPBlockInactive, lifecycle=[SubscriptionLifecycle.PROVISIONING]
):
    port: PortBlockProvisioning
    vlan: int  # TODO: refactor to CustomVlanRanges together with L2VPN product and workflow
    ims_id: int | None = None

    @computed_field  # type: ignore[misc]
    @property
    def title(self) -> str:
        return f"VLAN {self.vlan} on port {self.port.port_name} of {self.port.node.node_name}"


class SAPBlock(SAPBlockProvisioning, lifecycle=[SubscriptionLifecycle.ACTIVE]):
    port: PortBlock
    vlan: int  # TODO: refactor to CustomVlanRanges together with L2VPN product and workflow
    ims_id: int
