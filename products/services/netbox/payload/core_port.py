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

from products.product_blocks.core_port import CorePortBlockProvisioning
from services import netbox


def build_core_port_payload(
    model: CorePortBlockProvisioning, subscription: SubscriptionModel
) -> netbox.InterfacePayload:
    """Create and return a Netbox payload object for a
       :class:`~products.product_blocks.core_port.CorePortBlockProvisioning`.

    Example payload::

        {
           "name": "0/0/4",
           "type": "10gbase-x-xfp",
           "speed": 10000000,
           "device": 28,
           "enabled": true,
           "description": "Core Link 10G to paris01a"
        }

    Args:
        model: CorePortBlockProvisioning
        subscription: The Subscription that will be provisioned

    Returns: :class:`netbox.InterfacePayload`

    """
    interface = netbox.get_interface(id=model.ims_id)
    node_a = subscription.core_link.ports[0].node  # type: ignore[attr-defined]
    node_b = subscription.core_link.ports[1].node  # type: ignore[attr-defined]
    opposite_node = node_a.node_name if model.node.ims_id == node_b.ims_id else node_b.node_name
    return netbox.InterfacePayload(
        device=model.node.ims_id,
        name=model.port_name,
        type=interface.type.value,
        description=f"{subscription.product.name} to {opposite_node}",
        enabled=model.enabled,
        speed=interface.speed,
    )
