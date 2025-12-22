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


def build_sap_vlans_payload(model: SAPBlockProvisioning, subscription: SubscriptionModel) -> list[netbox.VlanPayload]:
    """Create and return a list of Netbox :class:`VlanPayload` for a :class:`~products.product_blocks.sap.SAPBlockProvisioning`.

    Example payload::

       {
          "vid": 4,
          "name": "paris01a 0/0/1 vlan 4",
          "status": "active",
          "group": <existing port IMS id>
       }

    Args:
        model: SAPBlockProvisioning
        subscription: The Subscription that will be provisioned

    Returns: list[:class:`netbox.VlanPayload`]

    """
    assert model.ims_id, "IMS id must be present when creating VLAN payloads"
    name = f"{model.port.node.node_name} {model.port.port_name}"
    vlan_list = [
        vlan for vlan_start, vlan_end in model.vlan.to_list_of_tuples() for vlan in range(vlan_start, vlan_end + 1)
    ]
    return [netbox.VlanPayload(vid=vlan, group=model.ims_id, name=f"{name} - {vlan}") for vlan in vlan_list]

