# Copyright 2019-2024 SURF.
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

import structlog
from nwastdlib.vlans import VlanRanges
from orchestrator.db import (
    SubscriptionTable,
)
from orchestrator.services import subscriptions
from orchestrator.types import SubscriptionLifecycle
from pydantic import BaseModel, field_validator
from pydantic_core.core_schema import ValidationInfo
from pydantic_forms.validators import Choice, choice_list

from forms.validator.shared import (
    _get_port_mode,
)
from products.product_blocks.port import PortMode
from utils.exceptions import VlanValueError
from workflows.shared import subscriptions_by_product_type_and_instance_value

logger = structlog.get_logger(__name__)


# TODO: check whether this could be the simple implementation
def ports_selector() -> type[list[Choice]]:
    port_subscriptions = subscriptions_by_product_type_and_instance_value(
        "Port", "port_mode", PortMode.TAGGED, [SubscriptionLifecycle.ACTIVE]
    )
    ports = {
        str(subscription.subscription_id): subscription.description
        for subscription in sorted(
            port_subscriptions, key=lambda port: port.description
        )
    }
    return choice_list(
        Choice("PortsEnum", zip(ports.keys(), ports.items())),  # type: ignore
        unique_items=True,
        min_items=1,
        max_items=1,
    )


class ServicePort(BaseModel):
    # NOTE: subscription_id and vlan are pydantic_forms fields which render ui components
    subscription_id: ports_selector()  # type: ignore # noqa: F821
    vlan: VlanRanges

    def __repr__(self) -> str:
        # Help distinguish this from the ServicePort product type..
        return f"FormServicePort({self.subscription_id=}, {self.vlan=})"

    @field_validator("vlan")
    @classmethod
    def check_vlan(cls, vlan: VlanRanges, info: ValidationInfo) -> VlanRanges:
        # We assume an empty string is untagged and thus 0
        if not vlan:
            print("empty vlan, setting to 0")
            vlan = VlanRanges(0)

        subscription_id = info.data.get("subscription_id")
        print("subscription_id:", subscription_id)
        if not subscription_id:
            return vlan

        subscription = subscriptions.get_subscription(
            subscription_id, model=SubscriptionTable
        )
        print("subscription:", subscription)

        port_mode = _get_port_mode(subscription)
        print("port_mode:", port_mode)

        if port_mode == PortMode.TAGGED and vlan == VlanRanges(0):
            raise VlanValueError(
                f"{port_mode} {subscription.product.tag} must have a vlan"
            )
        elif port_mode == PortMode.UNTAGGED and vlan != VlanRanges(0):  # noqa: RET506
            raise VlanValueError(
                f"{port_mode} {subscription.product.tag} can not have a vlan"
            )

        return vlan
