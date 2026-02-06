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

from products.product_types.node import Node
from products.services.netbox.netbox import build_payload
from pydantic_forms.types import State
from services import netbox
from workflows.shared import pretty_print_deepdiff


@step("validate node in IMS")
def validate_node_in_ims(subscription: Node) -> State:
    device = netbox.get_device(id=subscription.node.ims_id)
    actual = netbox.DevicePayload(
        site=device.site.id,
        device_type=device.device_type.id,
        role=device.device_role.id,
        name=device.name,
        status=device.status.value,
        primary_ip4=device.primary_ip4.id,
        primary_ip6=device.primary_ip6.id,
    )
    expected = build_payload(subscription.node, subscription)
    if ims_diff := DeepDiff(actual, expected, ignore_order=False):
        raise AssertionError("Found difference in IMS:\nActual => Expected\n" + pretty_print_deepdiff(ims_diff))

    return {"payload": expected.dict()}


@validate_workflow("Validate node")
def validate_node() -> StepList:
    return begin >> validate_node_in_ims
