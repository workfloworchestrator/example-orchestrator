import uuid
from random import randrange
from typing import Optional

from orchestrator.forms import FormPage
from orchestrator.forms.validators import Label
from orchestrator.services.products import get_product_by_id
from orchestrator.targets import Target
from orchestrator.types import FormGenerator, State, SubscriptionLifecycle, UUIDstr
from orchestrator.workflow import StepList, begin, step
from orchestrator.workflows.steps import store_process_subscription
from orchestrator.workflows.utils import create_workflow

from products.product_blocks.port import PortMode
from products.product_types.node import Node
from products.product_types.port import PortInactive, PortProvisioning
from products.services.description import description
from services import netbox
from workflows.port.shared.forms import port_mode_selector
from workflows.port.shared.steps import update_port_in_ims
from workflows.shared import (
    create_summary_form,
    free_port_selector,
    node_selector,
    pop_first,
)


def initial_input_form_generator(product: UUIDstr, product_name: str) -> FormGenerator:
    class SelectNodeForm(FormPage):
        class Config:
            title = product_name

        # organisation: OrganisationId

        node_subscription_id: node_selector()  # type:ignore

    select_node = yield SelectNodeForm
    select_node_dict = select_node.dict()
    node_subscription_id = select_node_dict["node_subscription_id"].pop(0)

    _product = get_product_by_id(product)
    speed = int(_product.fixed_input_value("speed"))

    class CreatePortForm(FormPage):
        class Config:
            title = product_name

        # organisation: OrganisationId

        port_settings: Label

        ims_id: free_port_selector(node_subscription_id, speed)  # type:ignore
        port_description: Optional[str]
        port_mode: port_mode_selector()  # type:ignore
        auto_negotiation: Optional[bool] = False
        lldp: Optional[bool] = False

    user_input = yield CreatePortForm
    user_input_dict = user_input.dict()
    pop_first(user_input_dict, "ims_id")

    summary_fields = ["ims_id", "port_description", "port_mode", "auto_negotiation", "lldp"]
    yield from create_summary_form(user_input_dict, product_name, summary_fields)

    return user_input_dict | {"node_subscription_id": node_subscription_id}


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
    interface = netbox.get_interface(id=ims_id)
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
