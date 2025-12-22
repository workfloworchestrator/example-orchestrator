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
import operator
from pprint import pformat
from typing import Annotated, Generator, List, TypeAlias, cast
from uuid import UUID

import structlog
from annotated_types import Ge, Le, doc
from deepdiff import DeepDiff
from nwastdlib.vlans import VlanRanges
from orchestrator.db import (
    ProductTable,
    ResourceTypeTable,
    SubscriptionInstanceRelationTable,
    SubscriptionInstanceTable,
    SubscriptionInstanceValueTable,
    SubscriptionTable,
    db,
)
from orchestrator.domain.base import ProductBlockModel
from orchestrator.services import subscriptions
from orchestrator.types import SubscriptionLifecycle
from pydantic import ConfigDict
from pydantic_core.core_schema import ValidationInfo
from pydantic_forms.core import FormPage
from pydantic_forms.types import State, SummaryData, UUIDstr
from pydantic_forms.validators import Choice, MigrationSummary, migration_summary
from sqlalchemy import select

from products.product_types.node import Node
from services import netbox

logger = structlog.get_logger(__name__)

Vlan = Annotated[int, Ge(2), Le(4094), doc("VLAN ID.")]

AllowedNumberOfL2vpnPorts = Annotated[int, Ge(2), Le(8), doc("Allowed number of L2vpn ports.")]


def subscriptions_by_product_type(product_type: str, status: List[SubscriptionLifecycle]) -> List[SubscriptionTable]:
    """
    retrieve_subscription_list_by_product This function lets you retreive a
    list of all subscriptions of a given product type. For example, you could
    call this like so:

    >>> subscriptions_by_product_type("Node", [SubscriptionLifecycle.ACTIVE, SubscriptionLifecycle.PROVISIONING])
    [SubscriptionTable(su...note=None), SubscriptionTable(su...note=None)]

    You now have a list of all active Node subscription instances and can then
    use them in your workflow.

    Args:
        product_type (str): The prouduct type in the DB (i.e. Node, User, etc.)
        status (List[SubscriptionLifecycle]): The lifecycle states you want returned (i.e.
        SubscriptionLifecycle.ACTIVE)

    Returns:
        List[SubscriptionTable]: A list of all the subscriptions that match
        your criteria.
    """
    subscriptions = (
        SubscriptionTable.query.join(ProductTable)
        .filter(ProductTable.product_type == product_type)
        .filter(SubscriptionTable.status.in_(status))
        .all()
    )
    return subscriptions


def subscriptions_by_product_type_and_instance_value(
    product_type: str, resource_type: str, value: str, status: List[SubscriptionLifecycle]
) -> List[SubscriptionTable]:
    """Retrieve a list of Subscriptions by product_type, resource_type and value.

    Args:
        product_type: type of subscriptions
        resource_type: name of the resource type
        value: value of the resource type
        status: lifecycle status of the subscriptions

    Returns: Subscription or None

    """
    return (
        SubscriptionTable.query.join(ProductTable)
        .join(SubscriptionInstanceTable)
        .join(SubscriptionInstanceValueTable)
        .join(ResourceTypeTable)
        .filter(ProductTable.product_type == product_type)
        .filter(SubscriptionInstanceValueTable.value == value)
        .filter(ResourceTypeTable.resource_type == resource_type)
        .filter(SubscriptionTable.status.in_(status))
        .all()
    )


def node_selector(enum: str = "NodesEnum") -> type[Choice]:
    node_subscriptions = subscriptions_by_product_type("Node", [SubscriptionLifecycle.ACTIVE])
    nodes = {
        str(subscription.subscription_id): subscription.description
        for subscription in sorted(node_subscriptions, key=lambda node: node.description)
    }
    return Choice(enum, zip(nodes.keys(), nodes.items()))  # type:ignore


def free_port_selector(node_subscription_id: UUIDstr, speed: int, enum: str = "PortsEnum") -> type[Choice]:
    node = Node.from_subscription(node_subscription_id)
    interfaces = {
        str(interface.id): interface.name
        for interface in netbox.get_interfaces(device=node.node.node_name, speed=speed * 1000, enabled=False)
    }
    return Choice(enum, zip(interfaces.keys(), interfaces.items()))  # type:ignore


def summary_form(product_name: str, summary_data: SummaryData) -> Generator:
    ProductSummary: TypeAlias = cast(type[MigrationSummary], migration_summary(summary_data))

    class SummaryForm(FormPage):
        model_config = ConfigDict(title=f"{product_name} summary")

        product_summary: ProductSummary

    yield SummaryForm


def create_summary_form(user_input: dict, product_name: str, fields: List[str]) -> Generator:
    columns = [[str(user_input[nm]) for nm in fields]]
    yield from summary_form(product_name, SummaryData(labels=fields, columns=columns))  # type: ignore


def modify_summary_form(user_input: dict, block: ProductBlockModel, fields: List[str]) -> Generator:
    before = [str(getattr(block, nm)) for nm in fields]  # type: ignore[attr-defined]
    after = [str(user_input[nm]) for nm in fields]
    yield from summary_form(
        block.subscription.product.name if block.subscription else "No Product Name Found",
        SummaryData(labels=fields, headers=["Before", "After"], columns=[before, after]),
    )


def pretty_print_deepdiff(diff: DeepDiff) -> str:
    return pformat(diff.to_dict(), indent=2, compact=False)


def validate_vlan(vlan: VlanRanges, info: ValidationInfo) -> VlanRanges:
    # We assume an empty string is untagged and thus 0
    if not vlan:
        vlan = VlanRanges(0)

    subscription_id = info.data.get("port_id") or info.data.get("port")
    if not subscription_id and (ports := info.data.get("ports")):
        subscription_id = ports[0] if ports else None

    if vlan == VlanRanges(0):
        if subscription_id:
            subscription = subscriptions.get_subscription(subscription_id, model=SubscriptionTable)
            raise ValueError(f"{subscription.product.tag} must have a vlan")
        raise ValueError("vlan must have a value")

    return vlan


def validate_vlan_not_in_use(
    vlan: int | VlanRanges,
    info: ValidationInfo,
    port_field_name: str = "subscription_id",
    current: list[State] | None = None,
) -> int | VlanRanges:
    """Check if vlan value is already in use by one or more subscriptions."""
    if not (subscription_ids_raw := info.data.get(port_field_name)):
        return vlan

    subscription_ids = (
        list(subscription_ids_raw)
        if isinstance(subscription_ids_raw, (list, tuple, set))
        else [subscription_ids_raw]
    )

    used_vlans = VlanRanges([])
    for subscription_id in subscription_ids:
        used_vlans |= find_allocated_vlans(subscription_id)

    if current:
        for subscription_id in subscription_ids:
            current_selected_service_port = filter(
                lambda c: str(c[port_field_name]) == str(subscription_id), current
            )
            current_selected_vlans = list(map(operator.itemgetter("vlan"), current_selected_service_port))
            for current_selected_vlan in current_selected_vlans:
                if not current_selected_vlan:
                    current_selected_vlan = "0"

                current_selected_vlan_range = VlanRanges(current_selected_vlan)
                used_vlans -= current_selected_vlan_range  # type: ignore[assignment]

    vlan_in_use = False
    if isinstance(vlan, int):
        vlan_in_use = vlan in used_vlans
    else:
        vlan_in_use = any(v in used_vlans for v in vlan)

    if vlan_in_use:
        raise ValueError(f"Vlan(s) {used_vlans} already in use")

    return vlan


def find_allocated_vlans(subscription_id: UUID | UUIDstr) -> VlanRanges:
    """Find all vlans already allocated to a SAP for a given port."""
    logger.debug("Finding allocated VLANs", subscription_id=subscription_id)

    query = (
        select(SubscriptionInstanceValueTable.value)
        .join(
            ResourceTypeTable,
            SubscriptionInstanceValueTable.resource_type_id == ResourceTypeTable.resource_type_id,
        )
        .join(
            SubscriptionInstanceRelationTable,
            SubscriptionInstanceValueTable.subscription_instance_id
            == SubscriptionInstanceRelationTable.in_use_by_id,
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
        return VlanRanges([])

    logger.debug("Found used VLAN values", values=used_vlan_values)
    return VlanRanges(",".join(used_vlan_values))
