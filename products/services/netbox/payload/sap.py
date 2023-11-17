# Copyright 2019 - 2023 SURF.
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
# from dataclasses import dataclass

from orchestrator.domain import SubscriptionModel

from products.product_blocks.sap import SAPBlockProvisioning
from services import netbox


def build_sap_payload(model: SAPBlockProvisioning, subscription: SubscriptionModel) -> netbox.VlanPayload:
    """Create and return a Netbox payload object for a :class:`~products.product_blocks.sap.SAPBlockProvisioning`.

    Example payload::

       {
          "vid": 4,
          "name": "paris01a 0/0/1 vlan 4",
          "status": "active"
       }

    Args:
        model: SAPBlockProvisioning
        subscription: The Subscription that will be provisioned

    Returns: :class:`netbox.VlanPayload`

    """
    return netbox.VlanPayload(vid=int(model.vlan), name=f"{model.port.node.node_name} {model.port.port_name}")
