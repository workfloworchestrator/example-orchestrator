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


from typing import Optional

import structlog
from orchestrator.forms import FormPage
from orchestrator.forms.validators import Label
from orchestrator.services.products import get_product_by_id
from orchestrator.types import FormGenerator, State, SubscriptionLifecycle, UUIDstr
from orchestrator.workflow import StepList, begin, step
from orchestrator.workflows.steps import set_status
from orchestrator.workflows.utils import modify_workflow

from products.product_types.node import Node, NodeProvisioning
from products.services.description import description
from workflows.node.shared.forms import (
    node_role_selector,
    node_status_selector,
    node_type_selector,
    site_selector,
)
from workflows.node.shared.steps import update_node_in_ims
from workflows.shared import modify_summary_form

logger = structlog.get_logger(__name__)


def initial_input_form_generator(subscription_id: UUIDstr, product: UUIDstr) -> FormGenerator:
    subscription = Node.from_subscription(subscription_id)
    node = subscription.node
    node_type = get_product_by_id(product).fixed_input_value("node_type")

    class ModifyNodeForm(FormPage):
        # organisation: OrganisationId = subscription.customer_id  # type: ignore

        node_settings: Label

        role_id: node_role_selector() = str(node.role_id)  # type:ignore
        type_id: node_type_selector(node_type) = str(node.type_id)  # type:ignore
        site_id: site_selector() = str(node.site_id)  # type:ignore
        node_status: node_status_selector() = node.node_status  # type:ignore
        node_name: Optional[str] = node.node_name
        node_description: Optional[str] = node.node_description

    user_input = yield ModifyNodeForm
    user_input_dict = user_input.dict()

    summary_fields = ["role_id", "type_id", "site_id", "node_status", "node_name", "node_description"]
    yield from modify_summary_form(user_input_dict, subscription.node, summary_fields)

    return user_input_dict | {"subscription": subscription}


@step("Update subscription")
def update_subscription(
    subscription: NodeProvisioning,
    role_id: int,
    type_id: int,
    site_id: int,
    node_status: str,
    node_name: str,
    node_description: str,
) -> State:
    # TODO: get all modified fields
    subscription.node.role_id = role_id
    subscription.node.type_id = type_id
    subscription.node.site_id = site_id
    subscription.node.node_status = node_status
    subscription.node.node_name = node_name
    subscription.node.node_description = node_description
    subscription.description = description(subscription)

    return {"subscription": subscription}


@modify_workflow("Modify node", initial_input_form=initial_input_form_generator)
def modify_node() -> StepList:
    return (
        begin
        >> set_status(SubscriptionLifecycle.PROVISIONING)
        >> update_subscription
        >> update_node_in_ims
        >> set_status(SubscriptionLifecycle.ACTIVE)
    )
