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


from typing import Annotated

from annotated_types import Len
from orchestrator.domain.base import ProductBlockModel
from orchestrator.types import SI, SubscriptionLifecycle
from pydantic import computed_field

from products.product_blocks.sap import SAPBlock, SAPBlockInactive, SAPBlockProvisioning

ListOfSaps = Annotated[list[SI], Len(min_length=2, max_length=8)]


class VirtualCircuitBlockInactive(ProductBlockModel, product_block_name="VirtualCircuit"):
    saps: ListOfSaps[SAPBlockInactive]
    speed: int | None = None
    speed_policer: bool | None = None
    ims_id: int | None = None
    nrm_id: int | None = None


class VirtualCircuitBlockProvisioning(VirtualCircuitBlockInactive, lifecycle=[SubscriptionLifecycle.PROVISIONING]):
    saps: ListOfSaps[SAPBlockProvisioning]
    speed: int
    speed_policer: bool
    ims_id: int | None = None
    nrm_id: int | None = None

    @computed_field  # type: ignore[misc]
    @property
    def title(self) -> str:
        return (
            f"{self.speed} Mbit/s circuit between "
            f"{self.saps[0].port.node.node_name} and "
            f"{self.saps[1].port.node.node_name}"
        )


class VirtualCircuitBlock(VirtualCircuitBlockProvisioning, lifecycle=[SubscriptionLifecycle.ACTIVE]):
    saps: ListOfSaps[SAPBlock]
    speed: int
    speed_policer: bool
    ims_id: int
    nrm_id: int
