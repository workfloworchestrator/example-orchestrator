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
from orchestrator.db import (
    ResourceTypeTable,
    SubscriptionInstanceRelationTable,
    SubscriptionInstanceTable,
    SubscriptionInstanceValueTable,
    SubscriptionTable,
    db,
)
from orchestrator.services import subscriptions
from pydantic_core.core_schema import ValidationInfo
from pydantic_forms.types import State, UUIDstr
from sqlalchemy import select

from products.product_blocks.port import PortMode
from workflows.nsistp.shared.shared import CustomVlanRanges, PortTag

logger = structlog.get_logger(__name__)


# TODO: remove unneeded _get_port_mode()
def _get_port_mode(subscription: SubscriptionTable) -> PortMode:
    if subscription.product.tag in [PortTag.AGGSP + PortTag.SP]:
        return subscription.port_mode
    return PortMode.TAGGED


def validate_vlan(vlan: CustomVlanRanges, info: ValidationInfo) -> CustomVlanRanges:
    # We assume an empty string is untagged and thus 0
    if not vlan:
        vlan = CustomVlanRanges(0)

    subscription_id = info.data.get("port_id")
    if not subscription_id:
        return vlan

    subscription = subscriptions.get_subscription(subscription_id, model=SubscriptionTable)

    port_mode = _get_port_mode(subscription)

    if port_mode == PortMode.TAGGED and vlan == CustomVlanRanges(0):
        raise ValueError(f"{port_mode} {subscription.product.tag} must have a vlan")
    elif port_mode == PortMode.UNTAGGED and vlan != CustomVlanRanges(0):  # noqa: RET506
        raise ValueError(f"{port_mode} {subscription.product.tag} can not have a vlan")

    return vlan


def validate_vlan_not_in_use(vlan: int, info: ValidationInfo) -> int | CustomVlanRanges:
    """Wrapper for check_vlan_in_use to work with AfterValidator."""
    # For single form validation, we don't have a 'current' list, so pass empty list
    current: list[State] = []
    return check_vlan_already_used(current, vlan, info)


def check_vlan_already_used(
    current: list[State], vlan: int | CustomVlanRanges, info: ValidationInfo
) -> int | CustomVlanRanges:
    """Check if vlan value is already in use by a subscription.

    Args:
        current: List of current form states, used to filter out self from used vlans.
        v: Vlan range of the form input.
        info: validation info, contains other fields in info.data

    Returns: input value if no errors
    """
    if not (subscription_id := info.data.get("subscription_id")):
        return vlan

    used_vlans = find_allocated_vlans(subscription_id)

    # Remove currently chosen vlans for this port to prevent tripping on in used by itself
    current_selected_vlan_ranges: list[str] = []
    if current:
        current_selected_service_port = filter(lambda c: str(c["subscription_id"]) == str(subscription_id), current)
        current_selected_vlans = list(map(operator.itemgetter("vlan"), current_selected_service_port))
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

    subscription = subscriptions.get_subscription(subscription_id, model=SubscriptionTable)

    # Handle both int and CustomVlanRanges
    if isinstance(vlan, int):
        vlan_in_use = vlan in used_vlans
    else:
        # For CustomVlanRanges, check if any of its values are in used_vlans
        vlan_in_use = any(v in used_vlans for v in vlan)

    if vlan_in_use:
        port_mode = _get_port_mode(subscription)

        # for tagged only; for link_member/untagged say "SP already in use"
        if port_mode == PortMode.UNTAGGED or port_mode == PortMode.LINK_MEMBER:
            raise ValueError("Port already in use")
        raise ValueError(f"Vlan(s) {', '.join(map(str, sorted(used_vlans)))} already in use")

    return vlan


# TODO: rewrite to support CustomVlanRanges
def find_allocated_vlans(
    subscription_id: UUID | UUIDstr,
) -> list[int]:
    """Find all vlans already allocated to a SAP for a given port."""
    logger.debug(
        "Finding allocated VLANs",
        subscription_id=subscription_id,
    )

    # Get all VLAN values used by the subscription
    query = (
        select(SubscriptionInstanceValueTable.value)
        .join(
            ResourceTypeTable,
            SubscriptionInstanceValueTable.resource_type_id == ResourceTypeTable.resource_type_id,
        )
        .join(
            SubscriptionInstanceRelationTable,
            SubscriptionInstanceValueTable.subscription_instance_id == SubscriptionInstanceRelationTable.in_use_by_id,
        )
        .join(
            SubscriptionInstanceTable,
            SubscriptionInstanceRelationTable.depends_on_id == SubscriptionInstanceTable.subscription_instance_id,
        )
        .filter(
            SubscriptionInstanceTable.subscription_id == subscription_id,
            ResourceTypeTable.resource_type == "vlan",
        )
    )

    used_vlan_values = db.session.execute(query).scalars().all()

    if not used_vlan_values:
        logger.debug("No VLAN values in use found")
        return []
        # return CustomVlanRanges([])

    logger.debug("Found used VLAN values", values=used_vlan_values)
    used_vlan_values_int = list({int(vlan) for vlan in used_vlan_values})
    return used_vlan_values_int
    # return CustomVlanRanges(used_vlan_values_int)
