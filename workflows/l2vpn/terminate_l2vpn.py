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
from orchestrator.workflows.utils import terminate_workflow

from products.product_types.l2vpn import L2vpn
from pydantic_forms.core import FormPage
from pydantic_forms.types import InputForm, UUIDstr
from pydantic_forms.validators import DisplaySubscription
from workflows.shared import remove_l2vpn_in_netbox, remove_saps_in_netbox


def terminate_initial_input_form_generator(subscription_id: UUIDstr) -> InputForm:
    temp_subscription_id = subscription_id

    class TerminateForm(FormPage):
        subscription_id: DisplaySubscription = temp_subscription_id  # type: ignore

    return TerminateForm


@step("Remove L2VPN from IMS")
def ims_remove_l2vpn(subscription: L2vpn) -> None:
    vc = subscription.virtual_circuit

    remove_l2vpn_in_netbox(vc)


@step("Remove VLANs from IMS")
def ims_remove_vlans(subscription: L2vpn) -> None:
    saps = subscription.virtual_circuit.saps

    remove_saps_in_netbox(saps)


@terminate_workflow("Terminate l2vpn", initial_input_form=terminate_initial_input_form_generator)
def terminate_l2vpn() -> StepList:
    return begin >> ims_remove_l2vpn >> ims_remove_vlans
