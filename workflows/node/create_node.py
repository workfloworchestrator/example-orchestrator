import uuid
from collections.abc import Generator
from random import randrange
from typing import Optional

from orchestrator.domain import SubscriptionModel
from orchestrator.forms import FormPage
from orchestrator.forms.validators import Divider, Label, MigrationSummary
from orchestrator.services.products import get_product_by_id
from orchestrator.targets import Target
from orchestrator.types import FormGenerator, State, SubscriptionLifecycle, UUIDstr
from orchestrator.workflow import StepList, begin, step
from orchestrator.workflows.steps import store_process_subscription
from orchestrator.workflows.utils import create_workflow

from products.product_blocks.shared.types import NodeStatus
from products.product_types.node import NodeInactive, NodeProvisioning
from products.services.netbox.netbox import build_payload
from services import netbox
from workflows.node.shared.forms import (
    node_role_selector,
    node_status_selector,
    node_type_selector,
    site_selector,
)


def subscription_description(subscription: SubscriptionModel) -> str:
    """The suggested pattern is to implement a subscription service that generates a subscription specific
    description, in case that is not present the description will just be set to the product name.
    """
    return f"{subscription.product.name} subscription"


def initial_input_form_generator(product_name: str, product: UUIDstr) -> FormGenerator:
    # TODO add additional fields to form if needed

    node_type = get_product_by_id(product).fixed_input_value("node_type")

    class CreateNodeForm(FormPage):
        class Config:
            title = product_name

        # organisation: OrganisationId

        label_node_settings: Label
        divider_1: Divider

        role_id: node_role_selector()  # type:ignore
        type_id: node_type_selector(node_type)  # type:ignore
        site_id: site_selector()  # type:ignore
        node_status: node_status_selector()  # type:ignore
        node_name: Optional[str]
        node_description: Optional[str]

    user_input = yield CreateNodeForm

    user_input_dict = user_input.dict()
    user_input_dict["role_id"] = user_input_dict["role_id"].pop(0)
    user_input_dict["type_id"] = user_input_dict["type_id"].pop(0)
    user_input_dict["site_id"] = user_input_dict["site_id"].pop(0)
    yield from create_summary_form(user_input_dict, product_name)

    return user_input_dict


def create_summary_form(
    user_input: dict,
    product_name: str,
) -> Generator:
    product_summary_fields = [
        "role_id",
        "type_id",
        "site_id",
        "node_status",
        "node_name",
        "node_description",
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
    role_id: int,
    type_id: int,
    site_id: int,
    node_status: NodeStatus,
    node_name: Optional[str],
    node_description: Optional[str],
) -> State:
    node = NodeInactive.from_product_id(
        product_id=product,
        customer_id=str(uuid.uuid4()),
        status=SubscriptionLifecycle.INITIAL,
    )
    print(f"construct model: type(node_status): {type(node_status)} == {node_status}")

    node.node.role_id = role_id
    node.node.type_id = type_id
    node.node.site_id = site_id
    node.node.node_status = node_status
    node.node.node_name = node_name
    node.node.node_description = node_description
    node.node.nrm_id = randrange(2**16)

    node = NodeProvisioning.from_other_lifecycle(node, SubscriptionLifecycle.PROVISIONING)
    node.description = subscription_description(node)

    return {
        "subscription": node,
        "subscription_id": node.subscription_id,  # necessary to be able to use older generic step functions
        "subscription_description": node.description,
    }


@step("Create node in IMS")
def create_node_in_imdb(subscription: NodeProvisioning) -> State:
    """Create node in IMDB"""
    payload = build_payload(subscription.node, subscription)
    subscription.node.ims_id = netbox.create(payload)
    return {"subscription": subscription, "payload": payload.dict()}


@step("Reserve loopback addresses")
def reserve_loopback_addresses(subscription: NodeProvisioning) -> State:
    """Reserve IPv4 and IPv6 loopback addresses"""
    subscription.node.ipv4_ipam_id, subscription.node.ipv6_ipam_id = netbox.reserve_loopback_addresses(
        subscription.node.ims_id
    )
    return {"subscription": subscription}


@step("Update node in IMS")
def update_node_in_imdb(subscription: NodeProvisioning) -> State:
    """Update node in IMDB"""
    payload = build_payload(subscription.node, subscription)
    netbox.update(payload, id=subscription.node.ims_id)
    return {"subscription": subscription, "payload": payload.dict()}


@create_workflow("Create node", initial_input_form=initial_input_form_generator)
def create_node() -> StepList:
    return (
        begin
        >> construct_node_model
        >> store_process_subscription(Target.CREATE)
        >> create_node_in_imdb
        >> reserve_loopback_addresses
        >> update_node_in_imdb
    )
