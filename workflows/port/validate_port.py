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


from deepdiff import DeepDiff
from orchestrator.workflow import StepList, begin, step
from orchestrator.workflows.utils import validate_workflow
from pydantic_forms.types import State

from products.product_types.port import Port
from products.services.netbox.netbox import build_payload
from services import netbox
from workflows.shared import pretty_print_deepdiff


@step("validate port in IMS")
def validate_port_in_ims(subscription: Port) -> State:
    interface = netbox.get_interface(id=subscription.port.ims_id)
    actual = netbox.InterfacePayload(
        device=interface.device.id,
        name=interface.name,
        type=interface.type.value,
        tagged_vlans=sorted([vlan.id for vlan in interface.tagged_vlans]),
        mode=interface.mode.value,
        description=interface.description,
        enabled=interface.enabled,
        speed=interface.speed,
    )
    expected = build_payload(subscription.port, subscription)
    if ims_diff := DeepDiff(actual, expected, ignore_order=False):
        raise AssertionError("Found difference in IMS:\nActual => Expected\n" + pretty_print_deepdiff(ims_diff))

    return {"payload": expected.dict()}


@validate_workflow("Validate port")
def validate_port() -> StepList:
    return begin >> validate_port_in_ims
