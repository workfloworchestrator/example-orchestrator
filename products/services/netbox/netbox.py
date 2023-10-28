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
from functools import singledispatch
from typing import Any

from orchestrator.domain.base import ProductBlockModel, SubscriptionModel

from products.product_blocks.node import NodeBlockProvisioning
from products.services.netbox.payload.node import build_node_payload
from services import netbox
from utils.singledispatch import single_dispatch_base


@singledispatch
def build_payload(model: ProductBlockModel, subscription: SubscriptionModel, **kwargs: Any) -> netbox.NetboxPayload:
    """Build payload for Netbox (generic function).

    Specific implementations of this generic function will specify the model types they work on and the payload types
    they return.

    Args:
        model: Domain model for which to construct a payload.
        subscription: The subscription model.
        kwargs: keyword arguments needed for some models.

    Returns:
        The constructed payload.

    Raises:
        TypeError: in case a specific implementation could not be found. The domain model it was called for will be
            part of the error message.

    """
    return single_dispatch_base(build_payload, model)


@build_payload.register
def _(model: NodeBlockProvisioning, subscription: SubscriptionModel, **kwargs: Any) -> netbox.DevicePayload:
    return build_node_payload(model, subscription)
