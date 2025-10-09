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


import json
import uuid
from random import randrange
from typing import TypeAlias, cast

from orchestrator.services.products import get_product_by_id
from orchestrator.targets import Target
from orchestrator.types import SubscriptionLifecycle
from orchestrator.utils.json import json_dumps
from orchestrator.workflow import StepList, begin, step
from orchestrator.workflows.steps import store_process_subscription
from orchestrator.workflows.utils import create_workflow
from pydantic import ConfigDict
from pydantic_forms.core import FormPage
from pydantic_forms.types import FormGenerator, State, UUIDstr
from pydantic_forms.validators import Choice, Label

from products.product_blocks.port import PortMode
from products.product_types.node import Node
from products.product_types.port import PortInactive, PortProvisioning
from products.services.description import description
from services import netbox
from services.lso_client import execute_playbook, lso_interaction
from workflows.port.shared.forms import PortModeChoice
from workflows.port.shared.steps import update_port_in_ims
from workflows.shared import create_summary_form, free_port_selector, node_selector


def initial_input_form_generator(product: UUIDstr, product_name: str) -> FormGenerator:
    NodeChoice: TypeAlias = cast(type[Choice], node_selector())

    class SelectNodeForm(FormPage):
        model_config = ConfigDict(title=product_name)

        # organisation: OrganisationId

        node_subscription_id: NodeChoice

    select_node = yield SelectNodeForm
    select_node_dict = select_node.model_dump()
    node_subscription_id = select_node_dict["node_subscription_id"]

    _product = get_product_by_id(product)
    speed = int(_product.fixed_input_value("speed"))
    FreePortChoice: TypeAlias = cast(
        type[Choice], free_port_selector(node_subscription_id, speed)
    )

    class CreatePortForm(FormPage):
        model_config = ConfigDict(title=product_name)

        # organisation: OrganisationId

        port_settings: Label

        port_ims_id: FreePortChoice
        port_description: str
        port_mode: PortModeChoice
        auto_negotiation: bool | None = False
        lldp: bool | None = False

    user_input = yield CreatePortForm
    user_input_dict = user_input.model_dump()

    summary_fields = [
        "port_ims_id",
        "port_description",
        "port_mode",
        "auto_negotiation",
        "lldp",
    ]
    yield from create_summary_form(user_input_dict, product_name, summary_fields)

    return user_input_dict | {"node_subscription_id": node_subscription_id}


@step("Construct Subscription model")
def construct_port_model(
    product: UUIDstr,
    node_subscription_id: UUIDstr,
    port_ims_id: int,
    port_description: str | None,
    port_mode: PortMode,
    auto_negotiation: bool,
    lldp: bool,
) -> State:
    subscription = PortInactive.from_product_id(
        product_id=product,
        customer_id=str(uuid.uuid4()),
        status=SubscriptionLifecycle.INITIAL,
    )
    node = Node.from_subscription(node_subscription_id)
    interface = netbox.get_interface(id=port_ims_id)
    subscription.port.node = node.node
    subscription.port.port_name = interface.name
    subscription.port.port_type = interface.type.value
    subscription.port.port_description = port_description
    subscription.port.port_mode = port_mode
    subscription.port.auto_negotiation = auto_negotiation
    subscription.port.lldp = lldp
    subscription.port.enabled = False
    subscription.port.ims_id = port_ims_id

    subscription = PortProvisioning.from_other_lifecycle(
        subscription, SubscriptionLifecycle.PROVISIONING
    )
    subscription.description = description(subscription)

    return {
        "subscription": subscription,
        "subscription_id": subscription.subscription_id,  # necessary to be able to use older generic step functions
        "subscription_description": subscription.description,
    }


@step("enable port in IMS")
def enable_port(subscription: PortProvisioning) -> State:
    subscription.port.enabled = True
    return {"subscription": subscription}


@step("Provision port in NRM")
def provision_port_in_nrm(subscription: PortProvisioning) -> State:
    """Dummy step that only creates a random NRM ID, replace with actual call to NRM."""
    subscription.port.nrm_id = randrange(2**16)
    return {"subscription": subscription}


@step("Install port config")
def provision_port(
    subscription: PortProvisioning,
    callback_route: str,
    process_id: UUIDstr,
) -> State:
    """Perform a dry run of deploying configuration on both sides of the trunk."""
    extra_vars = {
        "port": json.loads(json_dumps(subscription)),
    }

    execute_playbook(
        playbook_name="create_port.yaml",
        callback_route=callback_route,
        inventory=f"{subscription.port.node.node_name}\n",
        extra_vars=extra_vars,
    )

    return {"subscription": subscription}


@create_workflow("Create port", initial_input_form=initial_input_form_generator)
def create_port() -> StepList:
    return (
        begin
        >> construct_port_model
        >> store_process_subscription(Target.CREATE)
        >> enable_port
        >> update_port_in_ims
        >> lso_interaction(provision_port)
        >> provision_port_in_nrm
    )
