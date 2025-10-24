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


from orchestrator.domain import SubscriptionModel

from products.product_blocks.sap import SAPBlockProvisioning
from services import netbox
import itertools


def build_sap_payload(model: SAPBlockProvisioning, subscription: SubscriptionModel) -> list[netbox.VlanPayload]:
    """Create and return a Netbox payload object for a :class:`~products.product_blocks.sap.SAPBlockProvisioning`.

    Example payload::

       {
          "vid": 4,
          "name": "paris01a 0/0/1 vlan 4",
          "status": "active",
          "group": 1
       }

    Args:
        model: SAPBlockProvisioning
        subscription: The Subscription that will be provisioned

    Returns: :class:`netbox.VlanPayload`

    """
    name = f"{model.port.node.node_name} {model.port.port_name}"
    vlan_list = [vlan for vlan_start, vlan_end in model.vlan.to_list_of_tuples() for vlan in range(vlan_start, vlan_end+1)]
    return [netbox.VlanPayload(vid=vlan, group=model.ims_id, name=f"{name} - {vlan}") for vlan in vlan_list]


def build_sap_vlan_group_payload(model: SAPBlockProvisioning, subscription: SubscriptionModel) -> netbox.VlanGroupPayload:
    """Create

    Example payload::

       {
          "name": "paris01a 0/0/1 vlan 4",
          "vid_ranges": "5, 10, 15-20",
       }

    Args:
        model: SAPBlockProvisioning
        subscription: The Subscription that will be provisioned

    Returns: :class:`netbox.VlanGroupPayload`

    """
    name = f"{model.port.node.node_name} {model.port.port_name}"
    slug = name.replace(" ", "-").replace("/", "-")
    return netbox.VlanGroupPayload(name=name, slug=slug, vid_ranges=model.vlan.to_list_of_tuples())
