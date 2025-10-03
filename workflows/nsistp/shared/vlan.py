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
from uuid import UUID

import structlog
from more_itertools import first, flatten
from orchestrator.db import (
    SubscriptionTable,
)
from orchestrator.services import subscriptions
from pydantic_core.core_schema import ValidationInfo
from pydantic_forms.types import State

from products.product_blocks.port import PortMode
from utils.exceptions import PortsValueError, VlanValueError
from workflows.nsistp.shared.nsistp_services import get_available_vlans_by_port_id
from workflows.nsistp.shared.shared import CustomVlanRanges, PortTag

logger = structlog.get_logger(__name__)

# def get_vlans_by_ims_circuit_id(ims_circuit_id: int) -> list[VlanRange]:
#     return VlansApi(ims_api_client).vlans_by_msp(ims_circuit_id)


# def _clean_vlan_ranges(vlans: list[VlanRange]) -> list[list[int]]:
#     """Return a list of VlanRange objects that each has a start and end integer property.

#     It flattens this list to a list of numbers to dedupe and potentially apply a filter (default to True/all). It
#     groups that list by adjacency creating a new list of range start/ends - e.g. [[2,4],[5,19]] the (monadic/Right)
#     return value of this function.

#     Args:
#         vlans: a list of VlanRange objects

#     >>> import collections
#     >>> VlanRange = collections.namedtuple("VlanRange", ["start", "end"])
#     >>> _clean_vlan_ranges([VlanRange(1,4), VlanRange(3,3), VlanRange(5, 5), VlanRange(7, 10), VlanRange(12, 12)])
#     [[1, 5], [7, 10], [12]]

#     """
#     numbers: list[int] = expand_ranges(
#         [(vlan.start, vlan.end) for vlan in vlans], inclusive=True
#     )
#     sorted_numbers: Iterable[int] = sorted(set(numbers))
#     grouped_by = (
#         list(x) for _, x in groupby(sorted_numbers, lambda x, c=count(): next(c) - x)
#     )  # type: ignore  # noqa: B008
#     return [
#         [element[0], element[-1]] if element[0] != element[-1] else [element[0]]
#         for element in grouped_by
#     ]


def get_port_mode(subscription: SubscriptionTable) -> PortMode:
    if subscription.product.tag in [PortTag.AGGSP + PortTag.SP]:
        return subscription.port_mode
    return PortMode.TAGGED


# TODO: check why this cannot find vlans by subsriptions_id (it seems that there is no subscription_instance_id created)
def get_vlans_by_subscription_id(subscription_id: UUID) -> list[list[int]]:
    values = subscriptions.find_values_for_resource_types(
        subscription_id, ["vlan"], strict=False
    )
    print("Values from vlan resource type:", values)
    vlan = first(values["vlan"], default=[])  # Provide empty list as default
    print("First vlan value:", vlan)
    return vlan
    # return _clean_vlan_ranges(get_vlans_by_ims_circuit_id(int(ims_circuit_id)))


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

    port_mode = get_port_mode(subscription)

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
        current: List of current form states, used to filter out self from used vlans.
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

    # TODO: check why this cannot find vlans by subsriptions_id (it seems that there is no subscription_instance_id created)
    vlans = get_vlans_by_subscription_id(subscription_id)
    used_vlans = [vlan.vid for vlan in vlans if vlan is not None]
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
        port_mode = get_port_mode(subscription)

        # for tagged only; for link_member/untagged say "SP already in use"
        if port_mode == PortMode.UNTAGGED or port_mode == PortMode.LINK_MEMBER:
            raise PortsValueError("Port already in use")
        raise VlanValueError(f"Vlan(s) {used_vlans} already in use")

    return v


def validate_vlan_not_in_use(
    v: CustomVlanRanges, info: ValidationInfo
) -> CustomVlanRanges:
    """Wrapper for check_vlan_in_use to work with AfterValidator."""
    # For single form validation, we don't have a 'current' list, so pass empty list
    current: list[State] = []
    return check_vlan_in_use(current, v, info)


def parse_vlan_ranges_to_list(vlan_string: str) -> list[int]:
    """Convert VLAN range string to list of integers.

    Args:
        vlan_string: String like "3,5-6,10-12" or "3,5,6"

    Returns:
        List of integers: [3, 5, 6, 10, 11, 12]
    """
    if not vlan_string or vlan_string == "0":
        return [0]

    vlans = []
    parts = vlan_string.split(",")

    for part in parts:
        part = part.strip()
        if "-" in part:
            # Handle range like "5-6"
            start, end = map(int, part.split("-"))
            vlans.extend(range(start, end + 1))
        else:
            # Handle single VLAN
            vlans.append(int(part))

    return sorted(set(vlans))
