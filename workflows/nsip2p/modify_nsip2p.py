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

from orchestrator.workflow import StepList, begin, step
from orchestrator.workflows.utils import ensure_provisioning_status, modify_workflow, reconcile_workflow
from pydantic_forms.core import FormPage
from pydantic_forms.types import FormGenerator, State, UUIDstr

from products.product_types.nsip2p import Nsip2p, Nsip2pProvisioning
from products.services.description import description
from workflows.shared import modify_summary_form


def initial_input_form_generator(subscription_id: UUIDstr) -> FormGenerator:
    subscription = Nsip2p.from_subscription(subscription_id)
    virtual_circuit = subscription.virtual_circuit

    class ModifyNsip2pForm(FormPage):
        speed: int = virtual_circuit.speed
        speed_policer: bool = virtual_circuit.speed_policer

    user_input = yield ModifyNsip2pForm
    user_input_dict = user_input.model_dump()

    summary_fields = ["speed", "speed_policer"]
    yield from modify_summary_form(user_input_dict, subscription.virtual_circuit, summary_fields)

    return user_input_dict | {"subscription": subscription}


@ensure_provisioning_status
@step("Update NSIP2P subscription")
def update_subscription(
    subscription: Nsip2pProvisioning,
    speed: int,
    speed_policer: bool,
) -> State:
    subscription.virtual_circuit.speed = speed
    subscription.virtual_circuit.speed_policer = speed_policer
    subscription.description = description(subscription)

    return {"subscription": subscription}


@step("Update NSIP2P in NRM")
def update_nsip2p_in_nrm(subscription: Nsip2p) -> State:
    # Placeholder for NRM update when available
    return {"subscription": subscription}


update_nsip2p_in_external_systems = begin >> update_nsip2p_in_nrm


@modify_workflow("Modify NSIP2P", initial_input_form=initial_input_form_generator)
def modify_nsip2p() -> StepList:
    return begin >> update_subscription >> update_nsip2p_in_external_systems


@reconcile_workflow("Reconcile NSIP2P")
def reconcile_nsip2p() -> StepList:
    return begin >> update_nsip2p_in_external_systems

