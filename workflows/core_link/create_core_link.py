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
from random import randrange
from typing import TypeAlias, cast

from orchestrator.services.products import get_product_by_id
from orchestrator.targets import Target
from orchestrator.types import SubscriptionLifecycle, UUIDstr
from orchestrator.workflow import StepList, begin, step
from orchestrator.workflows.steps import store_process_subscription
from orchestrator.workflows.utils import create_workflow
from pydantic import ConfigDict
from pydantic_forms.core import FormPage
from pydantic_forms.types import FormGenerator, State
from pydantic_forms.validators import Choice

from products.product_types.core_link import CoreLinkInactive, CoreLinkProvisioning
from products.product_types.node import Node
from products.services.description import description
from products.services.netbox.netbox import build_payload
from services import netbox
from settings import settings
from workflows.shared import NodeAChoice, NodeBChoice, free_port_selector


def initial_input_form_generator(product: UUIDstr, product_name: str) -> FormGenerator:
    class SelectNodes(FormPage):
        model_config = ConfigDict(title=f"{product_name} - node A and B")

        node_subscription_id_a: NodeAChoice
        node_subscription_id_b: NodeBChoice

    select_nodes = yield SelectNodes
    select_nodes_dict = select_nodes.dict()

    _product = get_product_by_id(product)
    speed = int(_product.fixed_input_value("speed"))
    FreePortAChoice: TypeAlias = cast(
        type[Choice],
        free_port_selector(select_nodes_dict["node_subscription_id_a"], speed, "FreePortEnumA"),  # noqa: F821
    )
    FreePortBChoice: TypeAlias = cast(
        type[Choice],
        free_port_selector(select_nodes_dict["node_subscription_id_b"], speed, "FreePortEnumB"),  # noqa: F821
    )

    class SelectPorts(FormPage):
        model_config = ConfigDict(title=f"{product_name} - port A and B")

        port_ims_id_a: FreePortAChoice
        port_ims_id_b: FreePortBChoice
        under_maintenance: bool = False

    select_ports = yield SelectPorts
    select_ports_dict = select_ports.dict()

    return select_nodes_dict | select_ports_dict


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
    interface_a = netbox.get_interface(id=port_ims_id_a)
    subscription.core_link.ports[0].ims_id = port_ims_id_a
    subscription.core_link.ports[0].port_name = interface_a.name
    subscription.core_link.ports[0].node = node_a.node
    # side B
    node_b = Node.from_subscription(node_subscription_id_b)
    interface_b = netbox.get_interface(id=port_ims_id_b)
    subscription.core_link.ports[1].ims_id = port_ims_id_b
    subscription.core_link.ports[1].port_name = interface_b.name
    subscription.core_link.ports[1].node = node_b.node
    # core link setting(s)
    subscription.core_link.under_maintenance = under_maintenance

    subscription = CoreLinkProvisioning.from_other_lifecycle(subscription, SubscriptionLifecycle.PROVISIONING)
    subscription.description = description(subscription)

    return {
        "subscription": subscription,
        "subscription_id": subscription.subscription_id,  # necessary to be able to use older generic step functions
        "subscription_description": subscription.description,
    }


@step("Assign IPv6 prefix")
def assign_ipv6_prefix(subscription: CoreLinkProvisioning) -> State:
    parent_prefix_ipv6 = netbox.get_ip_prefix(prefix=settings.IPv6_CORE_LINK_PREFIX)
    prefix_ipv6 = netbox.create_available_prefix(
        parent_id=parent_prefix_ipv6.id,
        payload=netbox.AvailablePrefixPayload(
            prefix_length=127,
            description=description(subscription),
        ),
    )
    subscription.core_link.ipv6_prefix_ipam_id = prefix_ipv6.id

    return {"subscription": subscription, "prefix_ipv6": prefix_ipv6.prefix}


@step("Assign side A IPv6 address")
def assign_side_a_ipv6_prefix(subscription: CoreLinkProvisioning) -> State:
    a_side_ipv6 = netbox.create_available_ip(
        parent_id=subscription.core_link.ipv6_prefix_ipam_id,
        payload=netbox.AvailableIpPayload(
            assigned_object_id=subscription.core_link.ports[0].ims_id,
            description=description(subscription.core_link.ports[0]),
        ),
    )
    subscription.core_link.ports[0].ipv6_ipam_id = a_side_ipv6.id

    return {"subscription": subscription, "a_side_ipv6": a_side_ipv6.address}


@step("Assign side B IPv6 address")
def assign_side_b_ipv6_prefix(subscription: CoreLinkProvisioning) -> State:
    b_side_ipv6 = netbox.create_available_ip(
        parent_id=subscription.core_link.ipv6_prefix_ipam_id,
        payload=netbox.AvailableIpPayload(
            assigned_object_id=subscription.core_link.ports[1].ims_id,
            description=description(subscription.core_link.ports[1]),
        ),
    )
    subscription.core_link.ports[1].ipv6_ipam_id = b_side_ipv6.id

    return {"subscription": subscription, "b_side_ipv6": b_side_ipv6.address}


@step("Connect ports in IMS")
def connect_ports(subscription: CoreLinkProvisioning):
    payload = build_payload(subscription.core_link, subscription)
    subscription.core_link.ims_id = netbox.create(payload)

    return {"subscription": subscription, "payload": payload}


@step("enable ports in IMS")
def enable_ports(subscription: CoreLinkProvisioning) -> State:
    # Note that the enabled field on the CorePortBlock is set to True by default, only need to send payload to IMS
    payload_port_a = build_payload(subscription.core_link.ports[0], subscription)
    netbox.update(payload_port_a, id=subscription.core_link.ports[0].ims_id)
    payload_port_b = build_payload(subscription.core_link.ports[1], subscription)
    netbox.update(payload_port_b, id=subscription.core_link.ports[1].ims_id)

    return {"payload_port_a": payload_port_a, "payload_port_b": payload_port_b}


@step("Provision core link in NRM")
def provision_core_link_in_nrm(subscription: CoreLinkProvisioning) -> State:
    """Dummy step that only creates random NRM IDs, replace with actual call to NRM."""
    subscription.core_link.ports[0].nrm_id = randrange(2**16)
    subscription.core_link.ports[1].nrm_id = randrange(2**16)
    subscription.core_link.nrm_id = randrange(2**16)
    return {"subscription": subscription}


@create_workflow("Create core_link", initial_input_form=initial_input_form_generator)
def create_core_link() -> StepList:
    return (
        begin
        >> construct_core_link_model
        >> store_process_subscription(Target.CREATE)
        >> assign_ipv6_prefix
        >> assign_side_a_ipv6_prefix
        >> assign_side_b_ipv6_prefix
        >> connect_ports
        >> enable_ports
        >> provision_core_link_in_nrm
    )
