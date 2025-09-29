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

from nwastdlib.vlans import VlanRanges
from orchestrator.domain.base import SubscriptionModel
from orchestrator.types import SubscriptionLifecycle
from surf.products.product_blocks.sn8_nsistp import NsistpBlock, NsistpBlockInactive
from surf.products.product_types.fixed_input_types import Domain


class NsistpInactive(SubscriptionModel, is_base=True):
    domain: Domain
    settings: NsistpBlockInactive


class NsistpProvisioning(NsistpInactive, lifecycle=[SubscriptionLifecycle.PROVISIONING]):
    domain: Domain
    settings: NsistpBlock


class Nsistp(NsistpProvisioning, lifecycle=[SubscriptionLifecycle.ACTIVE]):
    domain: Domain
    settings: NsistpBlock

    @property
    def vlan_range(self) -> VlanRanges:
        return self.settings.sap.vlanrange
