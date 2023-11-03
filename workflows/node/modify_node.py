from collections.abc import Generator
from typing import Optional

import structlog
from orchestrator.forms import FormPage
from orchestrator.forms.validators import Label, MigrationSummary
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

logger = structlog.get_logger(__name__)


def initial_input_form_generator(subscription_id: UUIDstr, product: UUIDstr) -> FormGenerator:
    subscription = Node.from_subscription(subscription_id)
    node = subscription.node
    node_type = get_product_by_id(product).fixed_input_value("node_type")

    class ModifyNodeForm(FormPage):
        # organisation: OrganisationId = subscription.customer_id  # type: ignore

        node_settings: Label

        role_id: node_role_selector() = [str(node.role_id)]  # type:ignore
        type_id: node_type_selector(node_type) = [str(node.type_id)]  # type:ignore
        site_id: site_selector() = [str(node.site_id)]  # type:ignore
        node_status: node_status_selector() = node.node_status  # type:ignore
        node_name: Optional[str] = node.node_name
        node_description: Optional[str] = node.node_description

    user_input = yield ModifyNodeForm

    user_input_dict = user_input.dict()
    user_input_dict["role_id"] = user_input_dict["role_id"].pop(0)
    user_input_dict["type_id"] = user_input_dict["type_id"].pop(0)
    user_input_dict["site_id"] = user_input_dict["site_id"].pop(0)

    yield from create_summary_form(user_input_dict, subscription)

    return user_input_dict | {"subscription": subscription}


def create_summary_form(user_input: dict, subscription: Node) -> Generator:
    product_summary_fields = [
        "role_id",
        "type_id",
        "site_id",
        "node_status",
        "node_name",
        "node_description",
    ]

    before = [str(getattr(subscription.node, nm)) for nm in product_summary_fields]
    after = [str(user_input[nm]) for nm in product_summary_fields]

    class ProductSummary(MigrationSummary):
        data = {
            "labels": product_summary_fields,
            "headers": ["Before", "After"],
            "columns": [before, after],
        }

    class SummaryForm(FormPage):
        class Config:
            title = f"{subscription.product.name} Summary"

        product_summary: ProductSummary

    yield SummaryForm


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
