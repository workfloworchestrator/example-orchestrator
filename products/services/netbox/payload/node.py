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

from products.product_blocks.node import NodeBlockProvisioning
from services import netbox


def build_node_payload(model: NodeBlockProvisioning, subscription: SubscriptionModel) -> netbox.DevicePayload:
    """Create and return a Netbox payload object for a :class:`~products.product_blocks.node.NodeBlockProvisioning`.

    Example payload::

        {
           "name": "asd001a",
           "status": "active",
           "site": 17,
           "device_role": 11,
           "device_type": 23,
           "primary_ip4": 8,
           "primary_ip6": 15
        }

    Args:
        model: NodeBlockProvisioning
        subscription: The Subscription that will be changed

    Returns: :class:`netbox.DevicePayload`

    """
    return netbox.DevicePayload(
        site=model.site_id,  # not yet administrated in orchestrator
        device_type=model.type_id,  # not yet administrated in orchestrator
        device_role=model.role_id,  # not yet administrated in orchestrator
        name=model.node_name,
        status=model.node_status,
        primary_ip4=model.ipv4_ipam_id,
        primary_ip6=model.ipv6_ipam_id,
    )
