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
from typing import TypeAlias, cast

import structlog
from orchestrator.services.products import get_product_by_id
from orchestrator.workflow import StepList, begin, step
from orchestrator.workflows.utils import ensure_provisioning_status, modify_workflow
from pydantic_forms.core import FormPage
from pydantic_forms.types import FormGenerator, State, UUIDstr
from pydantic_forms.validators import Choice, Label

from products.product_blocks.shared.types import NodeStatus
from products.product_types.node import Node, NodeProvisioning
from products.services.description import description
from workflows.node.shared.forms import NodeStatusChoice, node_role_selector, node_type_selector, site_selector
from workflows.node.shared.steps import update_node_in_ims
from workflows.shared import modify_summary_form

logger = structlog.get_logger(__name__)


def initial_input_form_generator(subscription_id: UUIDstr, product: UUIDstr) -> FormGenerator:
    subscription = Node.from_subscription(subscription_id)
    node = subscription.node
    node_type = get_product_by_id(product).fixed_input_value("node_type")
    NodeTypeChoice: TypeAlias = cast(type[Choice], node_type_selector(node_type))
    NodeRoleChoice: TypeAlias = cast(type[Choice], node_role_selector())
    SiteChoice: TypeAlias = cast(type[Choice], site_selector())

    class ModifyNodeForm(FormPage):
        # organisation: OrganisationId = subscription.customer_id  # type: ignore

        node_settings: Label

        type_id: NodeTypeChoice = str(node.type_id)
        role_id: NodeRoleChoice = str(node.role_id)
        site_id: SiteChoice = str(node.site_id)
        node_status: NodeStatusChoice = node.node_status
        node_name: str = node.node_name
        node_description: str | None = node.node_description

    user_input = yield ModifyNodeForm
    user_input_dict = user_input.model_dump()

    summary_fields = ["role_id", "type_id", "site_id", "node_status", "node_name", "node_description"]
    yield from modify_summary_form(user_input_dict, subscription.node, summary_fields)

    return user_input_dict | {"subscription": subscription}


@ensure_provisioning_status
@step("Update subscription")
def update_subscription(
    subscription: NodeProvisioning,
    role_id: int,
    type_id: int,
    site_id: int,
    node_status: NodeStatus,
    node_name: str,
    node_description: str | None,
) -> State:
    subscription.node.role_id = role_id
    subscription.node.type_id = type_id
    subscription.node.site_id = site_id
    subscription.node.node_status = node_status
    subscription.node.node_name = node_name
    subscription.node.node_description = node_description
    subscription.description = description(subscription)

    return {"subscription": subscription}


@step("Update node in NRM")
def update_node_in_nrm(subscription: Node) -> State:
    """Dummy step, replace with actual call to NRM."""
    return {"subscription": subscription}


@modify_workflow("Modify node", initial_input_form=initial_input_form_generator)
def modify_node() -> StepList:
    return begin >> update_subscription >> update_node_in_ims >> update_node_in_nrm
