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


from orchestrator.types import SubscriptionLifecycle, UUIDstr
from orchestrator.workflow import StepList, begin, step
from orchestrator.workflows.steps import set_status
from orchestrator.workflows.utils import modify_workflow
from pydantic_forms.core import FormPage
from pydantic_forms.types import FormGenerator, State

from products.product_types.l2vpn import L2vpn, L2vpnProvisioning
from products.services.description import description
from workflows.shared import modify_summary_form


def initial_input_form_generator(subscription_id: UUIDstr) -> FormGenerator:
    subscription = L2vpn.from_subscription(subscription_id)
    virtual_circuit = subscription.virtual_circuit

    class ModifyL2vpnForm(FormPage):
        speed: int = virtual_circuit.speed
        speed_policer: bool = virtual_circuit.speed_policer

    user_input = yield ModifyL2vpnForm
    user_input_dict = user_input.model_dump()

    summary_fields = ["speed", "speed_policer"]
    yield from modify_summary_form(user_input_dict, subscription.virtual_circuit, summary_fields)

    return user_input_dict | {"subscription": subscription}


@step("Update subscription")
def update_subscription(
    subscription: L2vpnProvisioning,
    speed: int,
    speed_policer: bool,
) -> State:
    subscription.virtual_circuit.speed = speed
    subscription.virtual_circuit.speed_policer = speed_policer

    return {"subscription": subscription}


@step("Update subscription description")
def update_subscription_description(subscription: L2vpn) -> State:
    subscription.description = description(subscription)
    return {"subscription": subscription}


@step("Update L2VPN in NRM")
def update_l2vpn_in_nrm(subscription: L2vpnProvisioning) -> State:
    """Dummy step, replace with actual call to NRM."""
    return {"subscription": subscription}


@modify_workflow("Modify l2vpn", initial_input_form=initial_input_form_generator)
def modify_l2vpn() -> StepList:
    return (
        begin
        >> set_status(SubscriptionLifecycle.PROVISIONING)
        >> update_subscription
        >> update_subscription_description
        >> update_l2vpn_in_nrm
        >> set_status(SubscriptionLifecycle.ACTIVE)
    )
