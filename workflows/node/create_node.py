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


import uuid
import json
from random import randrange
from typing import TypeAlias, cast

from orchestrator.services.products import get_product_by_id
from orchestrator.targets import Target
from orchestrator.types import SubscriptionLifecycle, UUIDstr
from orchestrator.workflow import StepList, begin, step
from orchestrator.workflows.steps import store_process_subscription
from orchestrator.workflows.utils import create_workflow
from orchestrator.utils.json import json_dumps
from pydantic import ConfigDict
from pydantic_forms.core import FormPage
from pydantic_forms.types import FormGenerator, State
from pydantic_forms.validators import Choice, Label

from products.product_blocks.shared.types import NodeStatus
from products.product_types.node import NodeInactive, NodeProvisioning
from products.services.description import description
from products.services.netbox.netbox import build_payload
from services import netbox
from services.lso_client import execute_playbook, lso_interaction
from workflows.node.shared.forms import NodeStatusChoice, node_role_selector, node_type_selector, site_selector
from workflows.node.shared.steps import update_node_in_ims
from workflows.shared import create_summary_form


def initial_input_form_generator(product_name: str, product: UUIDstr) -> FormGenerator:
    node_type = get_product_by_id(product).fixed_input_value("node_type")
    NodeTypeChoice: TypeAlias = cast(type[Choice], node_type_selector(node_type))
    NodeRoleChoice: TypeAlias = cast(type[Choice], node_role_selector())
    SiteChoice: TypeAlias = cast(type[Choice], site_selector())

    class CreateNodeForm(FormPage):
        model_config = ConfigDict(title=product_name)

        # organisation: OrganisationId

        node_settings: Label

        type_id: NodeTypeChoice
        role_id: NodeRoleChoice
        site_id: SiteChoice
        node_status: NodeStatusChoice
        node_name: str
        node_description: str | None = None

    user_input = yield CreateNodeForm
    user_input_dict = user_input.model_dump()

    summary_fields = ["role_id", "type_id", "site_id", "node_status", "node_name", "node_description"]
    yield from create_summary_form(user_input_dict, product_name, summary_fields)

    return user_input_dict


@step("Construct Subscription model")
def construct_node_model(
    product: UUIDstr,
    # organisation: UUIDstr,
    role_id: int,
    type_id: int,
    site_id: int,
    node_status: NodeStatus,
    node_name: str,
    node_description: str | None,
) -> State:
    subscription = NodeInactive.from_product_id(
        product_id=product,
        customer_id=str(uuid.uuid4()),
        status=SubscriptionLifecycle.INITIAL,
    )
    print(f"construct model: type(node_status): {type(node_status)} == {node_status}")

    subscription.node.role_id = role_id
    subscription.node.type_id = type_id
    subscription.node.site_id = site_id
    subscription.node.node_status = node_status
    subscription.node.node_name = node_name
    subscription.node.node_description = node_description

    subscription = NodeProvisioning.from_other_lifecycle(subscription, SubscriptionLifecycle.PROVISIONING)
    subscription.description = description(subscription)

    return {
        "subscription": subscription,
        "subscription_id": subscription.subscription_id,  # necessary to be able to use older generic step functions
        "subscription_description": subscription.description,
    }


@step("Create node in IMS")
def create_node_in_ims(subscription: NodeProvisioning) -> State:
    payload = build_payload(subscription.node, subscription)
    subscription.node.ims_id = netbox.create(payload)
    return {"subscription": subscription, "payload": payload.dict()}


@step("Reserve loopback addresses")
def reserve_loopback_addresses(subscription: NodeProvisioning) -> State:
    subscription.node.ipv4_ipam_id, subscription.node.ipv6_ipam_id = netbox.reserve_loopback_addresses(
        subscription.node.ims_id
    )
    return {"subscription": subscription}

@step("Install node config")
def provision_node(
    subscription: NodeProvisioning,
    callback_route: str,
    process_id: UUIDstr,
) -> State:
    """Perform a dry run of deploying configuration on both sides of the trunk."""
    extra_vars = {
        "node": json.loads(json_dumps(subscription)),
    }

    execute_playbook(
        playbook_name="create_node.yaml",
        callback_route=callback_route,
        inventory=f"{subscription.node.node_name}\n",
        extra_vars=extra_vars,
    )

    return {"subscription": subscription}

@step("Provision node in NRM")
def provision_node_in_nrm(subscription: NodeProvisioning) -> State:
    """Dummy step that only creates a random NRM ID, replace with actual call to NRM."""
    subscription.node.nrm_id = randrange(2**16)
    return {"subscription": subscription}


@create_workflow("Create node", initial_input_form=initial_input_form_generator)
def create_node() -> StepList:
    return (
        begin
        >> construct_node_model
        >> store_process_subscription(Target.CREATE)
        >> create_node_in_ims
        >> reserve_loopback_addresses
        >> lso_interaction(provision_node)
        >> update_node_in_ims
        >> provision_node_in_nrm
    )
