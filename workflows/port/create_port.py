import uuid
from collections.abc import Generator
from random import randrange
from typing import Optional

from orchestrator.forms import FormPage
from orchestrator.forms.validators import Label, MigrationSummary
from orchestrator.services.products import get_product_by_id
from orchestrator.targets import Target
from orchestrator.types import FormGenerator, State, SubscriptionLifecycle, UUIDstr
from orchestrator.workflow import StepList, begin, step
from orchestrator.workflows.steps import store_process_subscription
from orchestrator.workflows.utils import create_workflow

from products import Node
from products.product_blocks.port import PortMode
from products.product_types.port import PortInactive, PortProvisioning
from products.services.description import description
from services.netbox import get_interface
from workflows.port.shared.forms import node_selector, port_mode_selector, port_selector
from workflows.port.shared.steps import update_port_in_ims


def initial_input_form_generator(product: UUIDstr, product_name: str) -> FormGenerator:
    class SelectNodeForm(FormPage):
        class Config:
            title = product_name

        # organisation: OrganisationId

        node_subscription_id: node_selector()  # type:ignore

    user_input = yield SelectNodeForm

    user_input_dict = user_input.dict()
    node_subscription_id = user_input_dict["node_subscription_id"].pop(0)

    _product = get_product_by_id(product)
    speed = int(_product.fixed_input_value("speed"))

    class CreatePortForm(FormPage):
        class Config:
            title = product_name

        # organisation: OrganisationId

        port_settings: Label

        ims_id: port_selector(node_subscription_id, speed)  # type:ignore
        port_description: Optional[str]
        port_mode: port_mode_selector()  # type:ignore
        auto_negotiation: Optional[bool] = False
        lldp: Optional[bool] = False

    user_input = yield CreatePortForm

    user_input_dict = user_input.dict()
    user_input_dict["ims_id"] = user_input_dict["ims_id"].pop(0)
    user_input_dict["node_subscription_id"] = node_subscription_id

    yield from create_summary_form(user_input_dict, product_name)

    return user_input_dict


def create_summary_form(
    user_input: dict,
    product_name: str,
) -> Generator:
    product_summary_fields = [
        "ims_id",
        "port_description",
        "port_mode",
        "auto_negotiation",
        "lldp",
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

    yield SummaryForm


@step("Construct Subscription model")
def construct_port_model(
    product: UUIDstr,
    node_subscription_id: UUIDstr,
    ims_id: int,
    port_description: Optional[str],
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
    interface = get_interface(id=ims_id)
    subscription.port.node = node.node
    subscription.port.port_name = interface.name
    subscription.port.port_type = interface.type.value
    subscription.port.port_description = port_description
    subscription.port.port_mode = port_mode
    subscription.port.auto_negotiation = auto_negotiation
    subscription.port.lldp = lldp
    subscription.port.enabled = False
    subscription.port.ims_id = ims_id
    subscription.port.nrm_id = randrange(2**16)  # TODO: move to separate step that provisions port in NRM

    subscription = PortProvisioning.from_other_lifecycle(subscription, SubscriptionLifecycle.PROVISIONING)
    subscription.description = description(subscription)

    return {
        "subscription": subscription,
        "subscription_id": subscription.subscription_id,  # necessary to be able to use older generic step functions
        "subscription_description": subscription.description,
    }


@step("enable port")
def enable_port(subscription: PortProvisioning) -> State:
    """Enable port in IMS"""
    subscription.port.enabled = True
    return {"subscription": subscription}


@create_workflow("Create port", initial_input_form=initial_input_form_generator)
def create_port() -> StepList:
    return (
        begin >> construct_port_model >> store_process_subscription(Target.CREATE) >> enable_port >> update_port_in_ims
    )
