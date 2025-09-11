# Copyright 2019-2024 SURF.
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

from pydantic import computed_field

from orchestrator.domain.base import ProductBlockModel, SubscriptionModel
from orchestrator.types import SubscriptionLifecycle
from surf.products.product_blocks.sap_sn8 import Sn8ServiceAttachPointBlock, Sn8ServiceAttachPointBlockInactive


class NsistpBlockInactive(ProductBlockModel, product_block_name="NSISTP Service Settings"):
    sap: Sn8ServiceAttachPointBlockInactive
    topology: str | None = None
    stp_id: str | None = None
    stp_description: str | None = None
    is_alias_in: str | None = None
    is_alias_out: str | None = None
    expose_in_topology: bool = False
    bandwidth: int | None = None


class NsistpBlock(NsistpBlockInactive, lifecycle=[SubscriptionLifecycle.ACTIVE, SubscriptionLifecycle.PROVISIONING]):
    sap: Sn8ServiceAttachPointBlock
    topology: str
    stp_id: str
    stp_description: str | None = None
    is_alias_in: str | None = None
    is_alias_out: str | None = None
    expose_in_topology: bool = False
    bandwidth: int | None = None

    @computed_field  # type: ignore[prop-decorator]
    @property
    def title(self) -> str:
        subscription = SubscriptionModel.from_subscription(self.sap.owner_subscription_id)
        return f"{self.tag} {self.topology} {self.stp_id} {subscription.description} vlan {self.sap.vlanrange}"
