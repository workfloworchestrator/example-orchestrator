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

from products.product_blocks.core_link import CoreLinkBlockProvisioning
from services import netbox


def build_core_link_payload(model: CoreLinkBlockProvisioning, subscription: SubscriptionModel) -> netbox.CablePayload:
    """Create and return a Netbox payload object for a
       :class:`~products.product_blocks.core_port.CoreLinkBlockProvisioning`.

    Example payload::

        {
           "name": "0/1/0",
           "type": "100gbase-x-cfp",
           "speed": 100000000,
           "device": 27,
           "enabled": true
        }

    Args:
        model: CoreLinkBlockProvisioning
        subscription: The Subscription that will be provisioned

    Returns: :class:`netbox.CablePayload`

    """
    return netbox.CablePayload(
        type="smf",
        status="connected",
        a_terminations=[netbox.CableTerminationPayload(object_id=model.ports[0].ims_id)],
        b_terminations=[netbox.CableTerminationPayload(object_id=model.ports[1].ims_id)],
        description=f"{model.ports[0].node.node_name} <-> {model.ports[1].node.node_name}",
    )
