import uuid
from random import randrange

from orchestrator.domain import SubscriptionModel
from orchestrator.forms import FormPage
from orchestrator.services.products import get_product_by_id
from orchestrator.targets import Target
from orchestrator.types import FormGenerator, State, SubscriptionLifecycle, UUIDstr
from orchestrator.workflow import StepList, begin, step
from orchestrator.workflows.steps import store_process_subscription
from orchestrator.workflows.utils import create_workflow
from pydantic import validator

from products import Node
from products.product_types.core_link import CoreLinkInactive, CoreLinkProvisioning
from products.services.description import description
from products.services.netbox.netbox import build_payload
from services import netbox
from services.netbox import IPv6_CORE_LINK_PREFIX, get_interface, get_prefix
from workflows.shared import node_selector, pop_first, port_selector


def subscription_description(subscription: SubscriptionModel) -> str:
    """The suggested pattern is to implement a subscription service that generates a subscription specific
    description, in case that is not present the description will just be set to the product name.
    """
    return f"{subscription.product.name} subscription"


def initial_input_form_generator(product: UUIDstr, product_name: str) -> FormGenerator:
    class SelectNodes(FormPage):
        class Config:
            title = f"{product_name} - node A and B"

        node_subscription_id_a: node_selector("NodesEnumA")  # type:ignore # noqa: F821
        node_subscription_id_b: node_selector("NodesEnumB")  # type:ignore # noqa: F821

        @validator("node_subscription_id_b", allow_reuse=True)
        def separate_nodes(cls, v: str, values: dict, **kwargs):
            if v == values["node_subscription_id_a"]:
                raise AssertionError("node B cannot be the same as node A")
            return v

    user_input = yield SelectNodes
    user_input_dict = user_input.dict()
    pop_first(user_input_dict, "node_subscription_id_a")
    pop_first(user_input_dict, "node_subscription_id_b")

    _product = get_product_by_id(product)
    speed = int(_product.fixed_input_value("speed"))

    class SelectPorts(FormPage):
        class Config:
            title = f"{product_name} - port A and B"

        port_ims_id_a: port_selector(
            user_input_dict["node_subscription_id_a"], speed, "PortsEnumA"  # type:ignore # noqa: F821
        )
        port_ims_id_b: port_selector(
            user_input_dict["node_subscription_id_b"], speed, "PortsEnumB"  # type:ignore # noqa: F821
        )
        under_maintenance: bool = False

    user_input = yield SelectPorts
    user_input_dict.update(user_input.dict())
    pop_first(user_input_dict, "port_ims_id_a")
    pop_first(user_input_dict, "port_ims_id_b")

    return user_input_dict


@step("Construct Subscription model")
def construct_core_link_model(
    product: UUIDstr,
    node_subscription_id_a: UUIDstr,
    node_subscription_id_b: UUIDstr,
    port_ims_id_a: int,
    port_ims_id_b: int,
    under_maintenance: bool,
) -> State:
    subscription = CoreLinkInactive.from_product_id(
        product_id=product,
        customer_id=str(uuid.uuid4()),
        status=SubscriptionLifecycle.INITIAL,
    )
    # side A
    node_a = Node.from_subscription(node_subscription_id_a)
    interface_a = get_interface(id=port_ims_id_a)
    subscription.core_link.ports[0].ims_id = port_ims_id_a
    subscription.core_link.ports[0].nrm_id = randrange(
        2**16
    )  # TODO: move to separate step that provisions core link in NRM
    subscription.core_link.ports[0].port_name = interface_a.name
    subscription.core_link.ports[0].node = node_a.node
    # side B
    node_b = Node.from_subscription(node_subscription_id_b)
    interface_b = get_interface(id=port_ims_id_b)
    subscription.core_link.ports[1].ims_id = port_ims_id_b
    subscription.core_link.ports[1].nrm_id = randrange(
        2**16
    )  # TODO: move to separate step that provisions core link in NRM
    subscription.core_link.ports[1].port_name = interface_b.name
    subscription.core_link.ports[1].node = node_b.node
    # core link setting(s)
    subscription.core_link.under_maintenance = under_maintenance
    subscription.core_link.nrm_id = randrange(2**16)  # TODO: move to separate step that provisions core link in NRM

    subscription = CoreLinkProvisioning.from_other_lifecycle(subscription, SubscriptionLifecycle.PROVISIONING)
    subscription.description = description(subscription)

    return {
        "subscription": subscription,
        "subscription_id": subscription.subscription_id,  # necessary to be able to use older generic step functions
        "subscription_description": subscription.description,
    }


@step("Assign IPv6 addresses")
def assign_ip_addresses(subscription: CoreLinkProvisioning) -> State:
    # Fetch parent prefixes.
    parent_prefix_ipv6 = get_prefix(prefix=IPv6_CORE_LINK_PREFIX)
    # Reserve IPv6 point-to-point subnet for the core link.
    prefix_ipv6 = netbox.create_available_prefix(
        parent_id=parent_prefix_ipv6.id,
        payload=netbox.AvailablePrefixPayload(
            prefix_length=127,
            description=description(subscription),
        ),
    )
    # Create the IP Addresses for each side of the core link.
    a_side_ipv6 = netbox.create_available_ip(
        parent_id=prefix_ipv6.id,
        payload=netbox.AvailableIpPayload(
            assigned_object_id=subscription.core_link.ports[0].ims_id,
            description=(
                f"{subscription.product.name} "
                f"{subscription.core_link.ports[0].node.node_name} "
                f"{subscription.core_link.ports[0].port_name}"
            ),
        ),
    )
    b_side_ipv6 = netbox.create_available_ip(
        parent_id=prefix_ipv6.id,
        payload=netbox.AvailableIpPayload(
            assigned_object_id=subscription.core_link.ports[1].ims_id,
            description=(
                f"{subscription.product.name} "
                f"{subscription.core_link.ports[1].node.node_name} "
                f"{subscription.core_link.ports[1].port_name}"
            ),
        ),
    )

    # Add IPv6 Addresses to the domain model.
    subscription.core_link.ports[0].ipv6_ipam_id = a_side_ipv6.id
    subscription.core_link.ports[1].ipv6_ipam_id = b_side_ipv6.id

    return {"subscription": subscription, "a_side_ipv6": a_side_ipv6.address, "b_side_ipv6": b_side_ipv6.address}


@step("Connect ports in IMS")
def connect_ports(subscription: CoreLinkProvisioning):
    payload = build_payload(subscription.core_link, subscription)
    subscription.core_link.ims_id = netbox.create(payload)

    return {"subscription": subscription, "payload": payload}


@step("enable ports in IMS")
def enable_ports(subscription: CoreLinkProvisioning) -> State:
    """Enable ports in IMS"""
    payload_port_a = build_payload(subscription.core_link.ports[0], subscription)
    netbox.update(payload_port_a, id=subscription.core_link.ports[0].ims_id)
    payload_port_b = build_payload(subscription.core_link.ports[1], subscription)
    netbox.update(payload_port_b, id=subscription.core_link.ports[1].ims_id)

    return {"payload_port_a": payload_port_a, "payload_port_b": payload_port_b}


@create_workflow("Create core_link", initial_input_form=initial_input_form_generator)
def create_core_link() -> StepList:
    return (
        begin
        >> construct_core_link_model
        >> store_process_subscription(Target.CREATE)
        >> assign_ip_addresses
        >> connect_ports
        >> enable_ports
    )
