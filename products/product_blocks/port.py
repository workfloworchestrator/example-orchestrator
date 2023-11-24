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


from typing import List

from orchestrator.domain.base import ProductBlockModel, serializable_property
from orchestrator.types import SubscriptionLifecycle
from pydantic_forms.types import strEnum

from products.product_blocks.node import (
    NodeBlock,
    NodeBlockInactive,
    NodeBlockProvisioning,
)


class PortMode(strEnum):
    """Valid port modes."""

    TAGGED = "tagged"
    UNTAGGED = "untagged"
    LINK_MEMBER = "link member"


class PortBlockInactive(ProductBlockModel, product_block_name="Port"):
    port_name: str | None = None
    port_type: str | None = None
    port_description: str | None = None
    port_mode: str | None = None
    auto_negotiation: bool | None = None
    lldp: bool | None = None
    enabled: bool | None = None
    node: NodeBlockInactive | None = None
    ims_id: int | None = None
    nrm_id: int | None = None


class PortBlockProvisioning(PortBlockInactive, lifecycle=[SubscriptionLifecycle.PROVISIONING]):
    port_name: str
    port_type: str
    port_description: str | None = None
    port_mode: str
    auto_negotiation: bool
    lldp: bool
    enabled: bool
    node: NodeBlockProvisioning
    ims_id: int
    nrm_id: int | None = None

    def _active_sap_blocks(self) -> List:
        from products.product_blocks.sap import SAPBlock

        return [
            SAPBlock.from_db(subscription_instance.subscription_instance_id)
            for subscription_instance in self.in_use_by
            if subscription_instance.product_block.tag == "SAP"
            and subscription_instance.subscription.status == SubscriptionLifecycle.ACTIVE
        ]

    @serializable_property
    def vlans(self) -> List[int]:
        """Get list of active VLANs by looking at SAPBlock's that use this PortBlock."""
        return [sap_block.vlan for sap_block in self._active_sap_blocks()]

    @serializable_property
    def vlan_ims_ids(self) -> List[int]:
        """Get list of active VLAN IMS IDs by looking at SAPBlock's that use this PortBlock."""
        return [sap_block.ims_id for sap_block in self._active_sap_blocks()]

    @serializable_property
    def title(self) -> str:
        # TODO: format correct title string
        return f"{self.name}"


class PortBlock(PortBlockProvisioning, lifecycle=[SubscriptionLifecycle.ACTIVE]):
    port_name: str
    port_type: str
    port_description: str | None = None
    port_mode: str
    auto_negotiation: bool
    lldp: bool
    enabled: bool
    node: NodeBlock
    ims_id: int
    nrm_id: int
