# Copyright 2019-2026 SURF.
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
from typing import List, Tuple, Callable

from orchestrator.workflow import step, StepList, conditional

from products.product_types.node import Node, NodeProvisioning
from products.services.netbox.netbox import build_payload
from pydantic_forms.types import State
from services import netbox


_CHECK_AUTO_IFACES_FLAG = "auto_add_interfaces"
if_auto_add_ifaces: Callable[..., StepList] = conditional(lambda state: state[_CHECK_AUTO_IFACES_FLAG])


@step("Update node in IMS")
def update_node_in_ims(subscription: Node) -> State:
    """Update node in IMDB"""
    payload = build_payload(subscription.node, subscription)
    netbox.update(payload, id=subscription.node.ims_id)
    return {"subscription": subscription, "payload": payload.dict()}


def get_node_interface_list(node_name: str) -> List[Tuple[str, str, int]]:
    """
    The list of interfaces installed in the node is usually obtained dynamically
    through (for example) SNMP, but for demonstration purposes we just return a
    static list of interfaces here without taking into account the type of the node.

    :param node_name: name of the node to retrieve interfaces from
    :return: list of interface tuples with name, type, and speed (kbps) details
    """
    ten_gig_interfaces = [(f"ethernet-1/{i}", "10gbase-x-xfp", 10000000) for i in range(10)]
    hundred_gig_interfaces = [(f"ethernet-1/{i + 10}", "100gbase-x-cfp", 100000000) for i in range(4)]
    return ten_gig_interfaces + hundred_gig_interfaces


@step("Update interfaces")
def update_interfaces(
        subscription: NodeProvisioning,
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
