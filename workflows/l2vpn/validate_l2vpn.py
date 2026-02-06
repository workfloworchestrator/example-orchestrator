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

from orchestrator.workflow import StepList, begin, step
from orchestrator.workflows.utils import validate_workflow

from products.product_types.l2vpn import L2vpn
from pydantic_forms.types import State


@step("validate L2VPN in IMS")
def validate_l2vpn_in_ims(subscription: L2vpn) -> State:
    # l2vpn = netbox.get_l2vpn(id=subscription.virtual_circuit.ims_id)
    # ...
    raise AssertionError("Not implemented yet")


@step("validate L2VPN terminations in IMS")
def validate_l2vpn_terminations_in_ims(subscription: L2vpn) -> State:
    # for sap in subscription.virtual_circuit.saps:
    #     l2vpn_termination = netbox.get_l2vpn_termination(id=sap.ims_id)
    #     ...
    raise AssertionError("Not implemented yet")


@step("validate VLANs on connected ports in IMS")
def validate_vlans_on_ports_in_ims(subscription: L2vpn) -> State:
    # for sap in subscription.virtual_circuit.saps:
    #     ...
    raise AssertionError("Not implemented yet")


@validate_workflow("Validate l2vpn")
def validate_l2vpn() -> StepList:
    return begin >> validate_l2vpn_in_ims >> validate_l2vpn_terminations_in_ims >> validate_vlans_on_ports_in_ims
