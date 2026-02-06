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


from typing import List, Tuple

import structlog
from orchestrator.types import SubscriptionLifecycle
from orchestrator.workflow import StepList, begin, step
from orchestrator.workflows.steps import set_status
from orchestrator.workflows.utils import modify_initial_input_form_generator, modify_workflow

from products.product_types.node import Node
from pydantic_forms.types import State
from services import netbox

logger = structlog.get_logger(__name__)


def get_node_interface_list(node_name: str) -> List[Tuple[str, str, int]]:
    """
    The list of interfaces installed in the node is usually obtained dynamically
    through (for example) SNMP, but for demonstration purposes we just return a
    static list of interfaces here without taking into account the type of the node.

    :param node_name: name of the node to retrieve interfaces from
    :return: list of interface tuples with name, type, and speed (kbps) details
    """
    ten_gig_interfaces = [(f"ethernet-1/{i}", "10gbase-x-xfp", 10000000) for i in range(10)]
    hundred_gig_interfaces = [(f"ethernet-1/{i+10}", "100gbase-x-cfp", 100000000) for i in range(4)]
    return ten_gig_interfaces + hundred_gig_interfaces


@step("Update interfaces")
def update_interfaces(
    subscription: Node,
) -> State:
    node_interfaces = set(get_node_interface_list(subscription.node.node_name))
    device = netbox.get_device(name=subscription.node.node_name)
    netbox_interfaces = set(
        (interface.name, interface.type.value, interface.speed)
        for interface in netbox.get_interfaces(device_id=device.id)
        if "Loopback" not in interface.name
    )
    interfaces_added = sorted(node_interfaces - netbox_interfaces)
    interfaces_deleted = sorted(netbox_interfaces - node_interfaces)
    for interface_name, interface_type, interface_speed in interfaces_added:
        netbox.create(
            netbox.InterfacePayload(device=device.id, name=interface_name, type=interface_type, speed=interface_speed)
        )
    for interface_name, _, _ in interfaces_deleted:
        netbox.delete_interface(device=device, name=interface_name)
    return {"interfaces_added": interfaces_added, "interfaces_deleted": interfaces_deleted}


@modify_workflow("Update node interfaces", initial_input_form=modify_initial_input_form_generator)
def modify_sync_ports() -> StepList:
    return (
        begin
        >> set_status(SubscriptionLifecycle.PROVISIONING)
        >> update_interfaces
        >> set_status(SubscriptionLifecycle.ACTIVE)
    )
