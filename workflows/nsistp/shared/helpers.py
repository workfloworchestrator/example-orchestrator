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

import operator

import structlog
from more_itertools import flatten
from nwastdlib.vlans import VlanRanges
from orchestrator.db import (
    SubscriptionTable,
)
from orchestrator.services import subscriptions
from orchestrator.types import SubscriptionLifecycle
from pydantic import GetJsonSchemaHandler, TypeAdapter
from pydantic.json_schema import JsonSchemaValue
from pydantic_core import CoreSchema
from pydantic_core.core_schema import ValidationInfo
from pydantic_forms.types import State
from pydantic_forms.validators import Choice

from products.product_blocks.port import PortMode
from utils.exceptions import PortsValueError, VlanValueError
from workflows.nsistp.shared.nsistp_services import get_available_vlans_by_port_id
from workflows.nsistp.shared.shared import (
    _get_port_mode,
)
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
# print("CustomVlanRanges schema:", adapter.json_schema())


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


# class FormNsistpPort(BaseModel):
#     # NOTE: subscription_id and vlan are pydantic_forms fields which render ui components
#     port_id: ports_selector()  # type: ignore # noqa: F821
#     vlan: CustomVlanRanges

#     def __repr__(self) -> str:
#         # Help distinguish this from the ServicePort product type..
#         return f"FormServicePort({self.port_id=}, {self.vlan=})"

#     @field_validator("vlan")
#     @classmethod
#     def check_vlan(
#         cls, vlan: CustomVlanRanges, info: ValidationInfo
#     ) -> CustomVlanRanges:
#         # We assume an empty string is untagged and thus 0
#         if not vlan:
#             vlan = CustomVlanRanges(0)

#         subscription_id = info.data.get("port_id")
#         if not subscription_id:
#             return vlan

#         subscription = subscriptions.get_subscription(
#             subscription_id, model=SubscriptionTable
#         )

#         port_mode = _get_port_mode(subscription)
#         print("port_mode:", port_mode)

#         if port_mode == PortMode.TAGGED and vlan == CustomVlanRanges(0):
#             raise VlanValueError(
#                 f"{port_mode} {subscription.product.tag} must have a vlan"
#             )
#         elif port_mode == PortMode.UNTAGGED and vlan != CustomVlanRanges(0):  # noqa: RET506
#             raise VlanValueError(
#                 f"{port_mode} {subscription.product.tag} can not have a vlan"
#             )

#         return vlan


def validate_vlan(vlan: CustomVlanRanges, info: ValidationInfo) -> CustomVlanRanges:
    # We assume an empty string is untagged and thus 0
    if not vlan:
        vlan = CustomVlanRanges(0)

    subscription_id = info.data.get("port_id")
    if not subscription_id:
        return vlan

    subscription = subscriptions.get_subscription(
        subscription_id, model=SubscriptionTable
    )

    port_mode = _get_port_mode(subscription)

    if port_mode == PortMode.TAGGED and vlan == CustomVlanRanges(0):
        raise VlanValueError(f"{port_mode} {subscription.product.tag} must have a vlan")
    elif port_mode == PortMode.UNTAGGED and vlan != CustomVlanRanges(0):  # noqa: RET506
        raise VlanValueError(
            f"{port_mode} {subscription.product.tag} can not have a vlan"
        )

    return vlan


def check_vlan_in_use(
    current: list[State], v: CustomVlanRanges, info: ValidationInfo
) -> CustomVlanRanges:
    """Check if vlan value is already in use by service port.

    Args:
        cls: class
        v: Vlan range of the form input.
        info: validation info, contains other fields in info.data

    1. Get all used vlans in a service port.
    2. Get all nsi reserved vlans and add them to the used_vlans.
    3. Filter out vlans used in current subscription from used_vlans.
    4. if nsi_vlans_only is true, it will also check if the input value is in the range of nsistp vlan ranges.
    5. checks if input value uses already used vlans. errors if true.
    6. return input value.


    """
    if not (subscription_id := info.data.get("subscription_id")):
        return v

    # TODO: obtain from db
    used_vlans = CustomVlanRanges(ims.get_vlans_by_subscription_id(subscription_id))
    nsistp_reserved_vlans = get_available_vlans_by_port_id(subscription_id)
    used_vlans = CustomVlanRanges(
        flatten([list(used_vlans), list(nsistp_reserved_vlans)])
    )

    # Remove currently chosen vlans for this port to prevent tripping on in used by itself
    current_selected_vlan_ranges: list[str] = []
    if current:
        current_selected_service_port = filter(
            lambda c: str(c["subscription_id"]) == str(subscription_id), current
        )
        current_selected_vlans = list(
            map(operator.itemgetter("vlan"), current_selected_service_port)
        )
        for current_selected_vlan in current_selected_vlans:
            # We assume an empty string is untagged and thus 0
            if not current_selected_vlan:
                current_selected_vlan = "0"

            current_selected_vlan_range = CustomVlanRanges(current_selected_vlan)
            used_vlans -= current_selected_vlan_range
            current_selected_vlan_ranges = [
                *current_selected_vlan_ranges,
                *list(current_selected_vlan_range),
            ]

    # TODO (#1842): probably better to have a separate type/validator for this
    # if nsi_vlans_only:
    #     vlan_list = list(v)
    #     invalid_ranges = [
    #         vlan
    #         for vlan in vlan_list
    #         if vlan not in list(nsistp_reserved_vlans)
    #         and vlan not in current_selected_vlan_ranges
    #     ]
    #     used_vlans -= nsistp_reserved_vlans

    #     if invalid_ranges:
    #         raise VlanValueError(
    #             f"Vlan(s) {CustomVlanRanges(invalid_ranges)} not valid nsi vlan range"
    #         )

    # logger.info(
    #     "Validation info for current chosen vlans vs vlan already in use",
    #     current=current,
    #     used_vlans=used_vlans,
    #     subscription_id=subscription_id,
    # )

    subscription = subscriptions.get_subscription(
        subscription_id, model=SubscriptionTable
    )

    if v & used_vlans:
        port_mode = _get_port_mode(subscription)

        # for tagged only; for link_member/untagged say "SP already in use"
        if port_mode == PortMode.untagged or port_mode == PortMode.link_member:
            raise PortsValueError("Port already in use")
        raise VlanValueError(f"Vlan(s) {used_vlans} already in use")

    return v
