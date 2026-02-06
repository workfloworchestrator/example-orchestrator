# Copyright 2019-2023 SURF, Geant.
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

from orchestrator.domain.base import SubscriptionModel
from orchestrator.types import SubscriptionLifecycle
from pydantic import model_validator

from products.product_blocks.virtual_circuit import (
    VirtualCircuitBlock,
    VirtualCircuitBlockInactive,
    VirtualCircuitBlockProvisioning,
)


class Nsip2pInactive(SubscriptionModel, is_base=True):
    virtual_circuit: VirtualCircuitBlockInactive

    @model_validator(mode="after")
    def validate_saps(self) -> "Nsip2pInactive":
        saps = self.virtual_circuit.saps
        if len(saps) != 2:
            raise ValueError("NSIP2P must contain exactly 2 SAPs")
        for sap in saps:
            if sap.vlan and not sap.vlan.is_single_vlan:
                raise ValueError("NSIP2P SAPs must each use exactly one VLAN")
        return self


class Nsip2pProvisioning(Nsip2pInactive, lifecycle=[SubscriptionLifecycle.PROVISIONING]):
    virtual_circuit: VirtualCircuitBlockProvisioning


class Nsip2p(Nsip2pProvisioning, lifecycle=[SubscriptionLifecycle.ACTIVE]):
    virtual_circuit: VirtualCircuitBlock
