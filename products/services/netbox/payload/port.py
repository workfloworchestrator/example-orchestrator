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

from products.product_blocks.port import PortBlockProvisioning, PortMode
from services import netbox


def build_port_payload(model: PortBlockProvisioning, subscription: SubscriptionModel) -> netbox.InterfacePayload:
    """Create and return a Netbox payload object for a :class:`~products.product_blocks.port.PortBlockProvisioning`.

    Example payload::

        {
           "name": "0/1/0",
           "type": "100gbase-x-cfp",
           "speed": 100000000,
           "device": 27,
           "enabled": true
        }

    Args:
        model: PortBlockProvisioning
        subscription: The Subscription that will be provisioned

    Returns: :class:`netbox.InterfacePayload`

    """
    return netbox.InterfacePayload(
        device=model.node.ims_id,
        name=model.port_name,
        type=model.port_type,
        tagged_vlans=model.vlan_ims_ids,
        mode="tagged" if model.port_mode == PortMode.TAGGED else "",
        description=model.port_description,
        enabled=model.enabled,
        speed=subscription.speed * 1000,  # type: ignore[attr-defined]
    )
