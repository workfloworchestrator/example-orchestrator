from collections.abc import Generator

import structlog
from orchestrator.domain import SubscriptionModel
from orchestrator.forms import FormPage
from orchestrator.forms.validators import Divider, MigrationSummary, OrganisationId
from orchestrator.types import FormGenerator, State, SubscriptionLifecycle, UUIDstr
from orchestrator.workflow import StepList, begin, step
from orchestrator.workflows.steps import set_status
from orchestrator.workflows.utils import modify_workflow
from pydantic_forms.core import ReadOnlyField

from products.product_types.node import Node, NodeProvisioning


def subscription_description(subscription: SubscriptionModel) -> str:
    """The suggested pattern is to implement a subscription service that generates a subscription specific
    description, in case that is not present the description will just be set to the product name.
    """
    return f"{subscription.product.name} subscription"


logger = structlog.get_logger(__name__)


def initial_input_form_generator(subscription_id: UUIDstr) -> FormGenerator:
    subscription = Node.from_subscription(subscription_id)
    node = subscription.node

    # TODO fill in additional fields if needed

    class ModifyNodeForm(FormPage):
        organisation: OrganisationId = subscription.customer_id  # type: ignore

        divider_1: Divider

        ims_id: int = ReadOnlyField(node.ims_id)
        nrm_id: int = ReadOnlyField(node.nrm_id)
        ipv4_ipam_id: int = ReadOnlyField(node.ipv4_ipam_id)
        ipv6_ipam_id: int = ReadOnlyField(node.ipv6_ipam_id)
        role_id: int = node.role_id
        type_id: int = node.type_id
        site_id: int = node.site_id
        node_status: str = node.node_status
        node_name: str = node.node_name
        node_description: str = node.node_description

    user_input = yield ModifyNodeForm
    user_input_dict = user_input.dict()

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
        "ims_id",
        "nrm_id",
        "ipv4_ipam_id",
        "ipv6_ipam_id",
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
        divider_1: Divider

    # TODO fill in additional details if needed

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
    return {"subscription": subscription}


@step("Update subscription description")
def update_subscription_description(subscription: Node) -> State:
    subscription.description = subscription_description(subscription)
    return {"subscription": subscription}


additional_steps = begin


@modify_workflow("Modify node", initial_input_form=initial_input_form_generator, additional_steps=additional_steps)
def modify_node() -> StepList:
    return (
        begin
        >> set_status(SubscriptionLifecycle.PROVISIONING)
        >> update_subscription
        >> update_subscription_description
        # TODO add additional steps if needed
        >> set_status(SubscriptionLifecycle.ACTIVE)
    )
