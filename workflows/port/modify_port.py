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
from pydantic_forms.validators import Label, ReadOnlyField

from products.product_types.port import Port, PortProvisioning
from products.services.description import description
from workflows.port.shared.steps import update_port_in_ims
from workflows.shared import modify_summary_form


def initial_input_form_generator(subscription_id: UUIDstr) -> FormGenerator:
    subscription = Port.from_subscription(subscription_id)
    port = subscription.port

    class ModifyPortForm(FormPage):
        # organisation: OrganisationId = subscription.customer_id  # type: ignore

        port_settings: Label

        node_name: ReadOnlyField(port.node.node_name)
        port_name: ReadOnlyField(port.port_name)
        port_type: ReadOnlyField(port.port_type)
        port_mode: ReadOnlyField(port.port_mode)
        port_description: str = port.port_description
        auto_negotiation: bool = port.auto_negotiation
        lldp: bool = port.lldp

    user_input = yield ModifyPortForm
    user_input_dict = user_input.dict()

    summary_fields = ["port_description", "auto_negotiation", "lldp"]
    yield from modify_summary_form(user_input_dict, subscription.port, summary_fields)

    return user_input_dict | {"subscription": subscription}


@step("Update subscription")
def update_subscription(
    subscription: PortProvisioning,
    port_description: str,
    auto_negotiation: bool,
    lldp: bool,
) -> State:
    subscription.port.port_description = port_description
    subscription.port.auto_negotiation = auto_negotiation
    subscription.port.lldp = lldp
    subscription.description = description(subscription)

    return {"subscription": subscription}


@step("Update port in NRM")
def update_port_in_nrm(subscription: PortProvisioning) -> State:
    """Dummy step, replace with actual call to NRM."""
    return {"subscription": subscription}


@modify_workflow("Modify port", initial_input_form=initial_input_form_generator)
def modify_port() -> StepList:
    return (
        begin
        >> set_status(SubscriptionLifecycle.PROVISIONING)
        >> update_subscription
        >> update_port_in_ims
        >> update_port_in_nrm
        >> set_status(SubscriptionLifecycle.ACTIVE)
    )
