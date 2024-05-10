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


from orchestrator.types import InputForm, UUIDstr
from orchestrator.workflow import StepList, begin, step
from orchestrator.workflows.utils import terminate_workflow
from pydantic_forms.core import FormPage
from pydantic_forms.validators import DisplaySubscription

from products.product_types.l2vpn import L2vpn
from services import netbox


#def terminate_initial_input_form_generator(subscription_id: UUIDstr, organisation: UUIDstr) -> InputForm:
def terminate_initial_input_form_generator(subscription_id: UUIDstr) -> InputForm:
    temp_subscription_id = subscription_id

    class TerminateForm(FormPage):
        subscription_id: DisplaySubscription = temp_subscription_id  # type: ignore

    return TerminateForm


@step("Remove L2VPN from IMS")
def ims_remove_l2vpn(subscription: L2vpn) -> None:
    netbox.delete_l2vpn(id=subscription.virtual_circuit.ims_id)
    # We rely on Netbox to delete the vlan terminations together with the l2vpn.


@step("Remove VLANs from IMS")
def ims_remove_vlans(subscription: L2vpn) -> None:
    for sap in subscription.virtual_circuit.saps:
        netbox.delete_vlan(id=sap.ims_id)


@terminate_workflow("Terminate l2vpn", initial_input_form=terminate_initial_input_form_generator)
def terminate_l2vpn() -> StepList:
    return begin >> ims_remove_l2vpn >> ims_remove_vlans
