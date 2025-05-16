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


from pydantic_forms.types import State
from orchestrator.workflow import StepList, begin, step
from orchestrator.workflows.utils import validate_workflow

from products.product_types.core_link import CoreLink


@step("validate core link in IMS")
def validate_core_link_in_ims(subscription: CoreLink) -> State:
    # cable = netbox.get_cable(id=subscription.core_link.ims_id)
    # ...
    raise AssertionError("Not implemented yet")


@step("validate core ports in IMS")
def validate_core_ports_in_ims(subscription: CoreLink) -> State:
    # interface_a = netbox.get_interface(id=subscription.core_link.ports[0].ims_id)
    # interface_b = netbox.get_interface(id=subscription.core_link.ports[1].ims_id)
    # ...
    raise AssertionError("Not implemented yet")


@validate_workflow("Validate core_link")
def validate_core_link() -> StepList:
    return begin >> validate_core_link_in_ims >> validate_core_ports_in_ims
