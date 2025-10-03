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
from pydantic import BaseModel, GetJsonSchemaHandler, TypeAdapter, field_validator
from pydantic.json_schema import JsonSchemaValue
from pydantic_core import CoreSchema
from pydantic_core.core_schema import ValidationInfo
from pydantic_forms.validators import Choice

from forms.validator.shared import (
    _get_port_mode,
)
from products.product_blocks.port import PortMode
from utils.exceptions import VlanValueError
from workflows.shared import subscriptions_by_product_type_and_instance_value

logger = structlog.get_logger(__name__)


# Custom VlanRanges needed to avoid matching conflict with SURF orchestrator-ui components
class CustomVlanRanges(VlanRanges):
    @classmethod
    def __get_pydantic_json_schema__(
        cls, core_schema_: CoreSchema, handler: GetJsonSchemaHandler
    ) -> JsonSchemaValue:
        parent_schema = super().__get_pydantic_json_schema__(core_schema_, handler)
        parent_schema["format"] = "custom-vlan"

        return parent_schema


# Add this after your CustomVlanRanges class definition
adapter = TypeAdapter(CustomVlanRanges)
print("CustomVlanRanges schema:", adapter.json_schema())


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

    return Choice("ServicePort", zip(ports.keys(), ports.items()))


class FormNsistpPort(BaseModel):
    # NOTE: subscription_id and vlan are pydantic_forms fields which render ui components
    port_id: ports_selector()  # type: ignore # noqa: F821
    vlan: CustomVlanRanges

    def __repr__(self) -> str:
        # Help distinguish this from the ServicePort product type..
        return f"FormServicePort({self.port_id=}, {self.vlan=})"

    @field_validator("vlan")
    @classmethod
    def check_vlan(
        cls, vlan: CustomVlanRanges, info: ValidationInfo
    ) -> CustomVlanRanges:
        print("hallo_vlan", vlan)
        # We assume an empty string is untagged and thus 0
        if not vlan:
            vlan = CustomVlanRanges(0)

        subscription_id = info.data.get("port_id")
        print("port:", subscription_id)
        if not subscription_id:
            return vlan

        subscription = subscriptions.get_subscription(
            subscription_id, model=SubscriptionTable
        )

        port_mode = _get_port_mode(subscription)
        print("port_mode:", port_mode)

        if port_mode == PortMode.TAGGED and vlan == CustomVlanRanges(0):
            raise VlanValueError(
                f"{port_mode} {subscription.product.tag} must have a vlan"
            )
        elif port_mode == PortMode.UNTAGGED and vlan != CustomVlanRanges(0):  # noqa: RET506
            raise VlanValueError(
                f"{port_mode} {subscription.product.tag} can not have a vlan"
            )

        return vlan
