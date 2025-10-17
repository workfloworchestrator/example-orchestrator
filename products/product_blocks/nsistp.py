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

from products.product_blocks.sap import SAPBlock, SAPBlockInactive, SAPBlockProvisioning


class NsistpBlockInactive(ProductBlockModel, product_block_name="Nsistp"):
    sap: SAPBlockInactive
    topology: str | None = None
    stp_id: str | None = None
    stp_description: str | None = None
    is_alias_in: str | None = None
    is_alias_out: str | None = None
    expose_in_topology: bool | None = None
    bandwidth: int | None = None


class NsistpBlockProvisioning(NsistpBlockInactive, lifecycle=[SubscriptionLifecycle.PROVISIONING]):
    sap: SAPBlockProvisioning
    topology: str
    stp_id: str
    stp_description: str | None = None
    is_alias_in: str | None = None
    is_alias_out: str | None = None
    expose_in_topology: bool | None = None
    bandwidth: int | None = None

    @computed_field
    @property
    def title(self) -> str:
        return f"NSISTP {self.stp_id} on {self.sap.title}"


class NsistpBlock(NsistpBlockProvisioning, lifecycle=[SubscriptionLifecycle.ACTIVE]):
    sap: SAPBlock
    topology: str
    stp_id: str
    stp_description: str | None = None
    is_alias_in: str | None = None
    is_alias_out: str | None = None
    expose_in_topology: bool | None = None
    bandwidth: int | None = None
