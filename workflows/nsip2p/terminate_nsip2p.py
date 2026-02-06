# Copyright 2019-2026 SURF, Geant.
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

from orchestrator.forms import FormPage
from orchestrator.forms.validators import DisplaySubscription
from orchestrator.workflow import StepList, begin, step
from orchestrator.workflows.utils import terminate_workflow

from products import Nsip2p
from pydantic_forms.types import InputForm, UUIDstr
from workflows.shared import remove_l2vpn_in_netbox, remove_saps_in_netbox


def terminate_initial_input_form_generator(subscription_id: UUIDstr, customer_id: UUIDstr) -> InputForm:
    temp_subscription_id = subscription_id

    class TerminateNsip2pForm(FormPage):
        subscription_id: DisplaySubscription = temp_subscription_id  # type: ignore

    return TerminateNsip2pForm


@step("Remove NSIP2P from IMS")
def ims_remove_nsip2p(subscription: Nsip2p) -> None:
    vc = subscription.virtual_circuit

    remove_l2vpn_in_netbox(vc)


@step("Remove VLANs from IMS")
def ims_remove_vlans(subscription: Nsip2p) -> None:
    saps = subscription.virtual_circuit.saps

    remove_saps_in_netbox(saps)


@terminate_workflow("Terminate NSIP2P", initial_input_form=terminate_initial_input_form_generator)
def terminate_nsip2p() -> StepList:
    return begin >> ims_remove_nsip2p >> ims_remove_vlans
