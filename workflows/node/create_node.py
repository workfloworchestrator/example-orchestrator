import uuid
from collections.abc import Generator
from typing import Optional

from orchestrator.domain import SubscriptionModel
from orchestrator.forms import FormPage
from orchestrator.forms.validators import (
    Divider,
    Label,
    MigrationSummary,
)
from orchestrator.targets import Target
from orchestrator.types import FormGenerator, State, SubscriptionLifecycle, UUIDstr
from orchestrator.workflow import StepList, begin, step
from orchestrator.workflows.steps import store_process_subscription
from orchestrator.workflows.utils import create_workflow

from products.product_types.node import NodeInactive, NodeProvisioning


def subscription_description(subscription: SubscriptionModel) -> str:
    """The suggested pattern is to implement a subscription service that generates a subscription specific
    description, in case that is not present the description will just be set to the product name.
    """
    return f"{subscription.product.name} subscription"


def initial_input_form_generator(product_name: str) -> FormGenerator:
    # TODO add additional fields to form if needed

    class CreateNodeForm(FormPage):
        class Config:
            title = product_name

        # organisation: OrganisationId

        label_node_settings: Label
        divider_1: Divider

        role: str
        type: str
        site: str
        status: str
        node_name: Optional[str]
        node_description: Optional[str]
        ims_id: Optional[int]
        nrm_id: Optional[int]
        ipv4_ipam_id: Optional[int]
        ipv6_ipam_id: Optional[int]

    user_input = yield CreateNodeForm

    user_input_dict = user_input.dict()
    yield from create_summary_form(user_input_dict, product_name)

    return user_input_dict


def create_summary_form(
    user_input: dict,
    product_name: str,
) -> Generator:
    product_summary_fields = [
        "role",
        "type",
        "site",
        "status",
        "node_name",
        "node_description",
        "ims_id",
        "nrm_id",
        "ipv4_ipam_id",
        "ipv6_ipam_id",
    ]

    class ProductSummary(MigrationSummary):
        data = {
            "labels": product_summary_fields,
            "columns": [[str(user_input[nm]) for nm in product_summary_fields]],
        }

    class SummaryForm(FormPage):
        class Config:
            title = f"{product_name} Summary"

        product_summary: ProductSummary
        divider_1: Divider

        # TODO fill in additional details if needed

    yield SummaryForm


@step("Construct Subscription model")
def construct_node_model(
    product: UUIDstr,
    # organisation: UUIDstr,
    role: str,
    type: str,
    site: str,
    status: str,
    node_name: Optional[str],
    node_description: Optional[str],
    ims_id: Optional[int],
    nrm_id: Optional[int],
    ipv4_ipam_id: Optional[int],
    ipv6_ipam_id: Optional[int],
) -> State:
    node = NodeInactive.from_product_id(
        product_id=product,
        customer_id=str(uuid.uuid4()),
        status=SubscriptionLifecycle.INITIAL,
    )
    node.node.role = role
    node.node.type = type
    node.node.site = site
    node.node.status = status
    node.node.node_name = node_name
    node.node.node_description = node_description
    node.node.ims_id = ims_id
    node.node.nrm_id = nrm_id
    node.node.ipv4_ipam_id = ipv4_ipam_id
    node.node.ipv6_ipam_id = ipv6_ipam_id

    node = NodeProvisioning.from_other_lifecycle(node, SubscriptionLifecycle.PROVISIONING)
    node.description = subscription_description(node)

    return {
        "subscription": node,
        "subscription_id": node.subscription_id,  # necessary to be able to use older generic step functions
        "subscription_description": node.description,
    }


additional_steps = begin


@create_workflow("Create node", initial_input_form=initial_input_form_generator, additional_steps=additional_steps)
def create_node() -> StepList:
    return (
        begin
        >> construct_node_model
        >> store_process_subscription(Target.CREATE)
        # TODO add provision step(s)
    )
