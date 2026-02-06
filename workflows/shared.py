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
from collections.abc import Iterator
from pprint import pformat
from typing import Annotated, Generator, List, TypeAlias, cast
from uuid import UUID

import structlog
from annotated_types import Ge, Le, doc
from deepdiff import DeepDiff
from orchestrator.db import (
    ProductTable,
    ResourceTypeTable,
    SubscriptionInstanceRelationTable,
    SubscriptionInstanceTable,
    SubscriptionInstanceValueTable,
    SubscriptionTable,
    db,
)
from orchestrator.domain import SubscriptionModel
from orchestrator.domain.base import ProductBlockModel
from orchestrator.services import subscriptions
from orchestrator.types import SubscriptionLifecycle
from pydantic import ConfigDict
from pydantic_core.core_schema import ValidationInfo
from sqlalchemy import select
from sqlalchemy.orm import aliased

from nwastdlib.vlans import VlanRanges
from products import Port
from products.product_blocks.sap import SAPBlock, SAPBlockProvisioning
from products.product_blocks.virtual_circuit import VirtualCircuitBlock, VirtualCircuitBlockProvisioning
from products.product_types.node import Node
from products.services.netbox.netbox import build_payload
from products.services.netbox.payload.sap import build_sap_vlan_group_payload
from pydantic_forms.core import FormPage
from pydantic_forms.types import State, SummaryData, UUIDstr
from pydantic_forms.validators import Choice, MigrationSummary, migration_summary
from services import netbox
from services.netbox import L2vpnTerminationPayload

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


def _vlan_partially_in_vlan_range(vlan: int | VlanRanges, vlan_range: VlanRanges) -> bool:
    match vlan:
        case int():
            return vlan in vlan_range
        case VlanRanges():
            return any(v in vlan_range for v in vlan)


def _vlan_completely_in_vlan_range(vlan: int | VlanRanges, vlan_range: VlanRanges) -> bool:
    match vlan:
        case int():
            return vlan in vlan_range
        case VlanRanges():
            return all(v in vlan_range for v in vlan)


def _get_subscription_ids_from_info(info: ValidationInfo, port_field_name: str) -> list[str] | None:
    match info.data.get(port_field_name):
        case list() | tuple() | set() as iterable:
            return list(iterable)
        case str() as scalar:
            return [scalar]
        case None:
            return None
        case _ as invalid:
            raise ValueError(f"Cannot convert value {invalid} in field {port_field_name} to list of subscription ids")


def validate_vlan_not_in_use(
    vlan: int | VlanRanges,
    info: ValidationInfo,
    port_field_name: str = "subscription_id",
    current: list[State] | None = None,
) -> int | VlanRanges:
    """Check if vlan value is already in use by one or more subscriptions."""
    if not (subscription_ids := _get_subscription_ids_from_info(info, port_field_name)):
        return vlan

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

    if _vlan_partially_in_vlan_range(vlan, used_vlans):
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


def find_allocated_vlans_for_product(subscription_id: UUID | UUIDstr, product_type: str) -> VlanRanges:
    """Find VLANs allocated to SAPs on a port filtered by product type (e.g. NSISTP or NSIP2P)."""
    logger.debug("Finding allocated VLANs for product", subscription_id=subscription_id, product_type=product_type)

    port_si = aliased(SubscriptionInstanceTable)
    sap_si = aliased(SubscriptionInstanceTable)
    sap_sub = aliased(SubscriptionTable)
    sap_prod = aliased(ProductTable)

    query = (
        select(SubscriptionInstanceValueTable.value)
        .join(
            ResourceTypeTable,
            SubscriptionInstanceValueTable.resource_type_id == ResourceTypeTable.resource_type_id,
        )
        .join(
            sap_si,
            SubscriptionInstanceValueTable.subscription_instance_id == sap_si.subscription_instance_id
        )
        .join(sap_sub, sap_si.subscription_id == sap_sub.subscription_id)
        .join(sap_prod, sap_sub.product_id == sap_prod.product_id)
        .join(
            SubscriptionInstanceRelationTable,
            sap_si.subscription_instance_id == SubscriptionInstanceRelationTable.in_use_by_id
        )
        .join(
            port_si,
            SubscriptionInstanceRelationTable.depends_on_id == port_si.subscription_instance_id,
        )
        .filter(
            port_si.subscription_id == subscription_id,
            ResourceTypeTable.resource_type == "vlan",
            sap_prod.product_type == product_type,
            sap_sub.status.in_(
                [SubscriptionLifecycle.PROVISIONING, SubscriptionLifecycle.ACTIVE]
            ),
        )
    )

    values = db.session.execute(query).scalars().all()
    if not values:
        logger.debug("No VLAN values in use found for product", product_type=product_type)
        return VlanRanges([])

    logger.debug("Found VLAN values for product", values=values, product_type=product_type)
    return VlanRanges(",".join(values))

def _get_subscription(subscription_id: UUID | UUIDstr) -> SubscriptionTable:
    return db.session.scalar(select(SubscriptionTable).where(SubscriptionTable.subscription_id == subscription_id))


def validate_vlan_reserved_by_product(
    vlan: int | VlanRanges,
    info: ValidationInfo,
    *,
    port_field_name: str = "subscription_id",
    product_type: str,
) -> int | VlanRanges:
    """Require the selected VLAN to be part of the reserved set for a specific product type on the selected port(s)."""
    if not (subscription_ids := _get_subscription_ids_from_info(info, port_field_name)):
        return vlan


    logger.info("validation info data", data=info.data)
    for subscription_id in subscription_ids:
        reserved_vlans = find_allocated_vlans_for_product(subscription_id, product_type)
        if not _vlan_completely_in_vlan_range(vlan, reserved_vlans):
            sub = _get_subscription(subscription_id)
            raise ValueError(
                f"VLAN(s) {vlan} not reserved by {product_type} on {sub.description}. "
                 f"Available vlans: {reserved_vlans}"
            )

    return vlan


def validate_vlan_not_used_by_product(
    vlan: int | VlanRanges,
    info: ValidationInfo,
    *,
    port_field_name: str = "subscription_id",
    product_type: str,
    current: list[State] | None = None,
) -> int | VlanRanges:
    """Ensure VLAN is not already in use by the given product type on the selected port(s)."""
    if not (subscription_ids := _get_subscription_ids_from_info(info, port_field_name)):
        return vlan

    used_vlans = VlanRanges([])
    for subscription_id in subscription_ids:
        used_vlans |= find_allocated_vlans_for_product(subscription_id, product_type)

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

    if _vlan_partially_in_vlan_range(vlan, used_vlans):
        raise ValueError(f"VLAN(s) {vlan} already in use by {product_type}. Used vlans: {used_vlans}")

    return vlan


def update_ports_in_netbox(saps: list[SAPBlockProvisioning]) -> list[netbox.InterfacePayload]:
    """Reprovision the connected ports in Netbox and return the Interface payloads.

    The VLANs from active SAPs will be provisioned in Netbox or removed otherwise.
    """
    port_subscription_ids = sorted({sap.port.owner_subscription_id for sap in saps})
    port_subscriptions = [Port.from_subscription(i) for i in port_subscription_ids]

    def update_port(port: Port) -> netbox.InterfacePayload:
        payload = build_payload(port.port, port)
        netbox.update(payload, id=port.port.ims_id)
        return payload

    return [update_port(i) for i in port_subscriptions]


def create_saps_in_netbox(saps: list[SAPBlockProvisioning], subscription: SubscriptionModel) -> list[
    tuple[netbox.VlanGroupPayload, netbox.VlansPayload]
]:
    """Provision the SAPs in Netbox and return the VlanGroup and Vlan payloads.

    Side Effects:
        - The sap.ims_id property is changed
    """

    def create_sap(sap: SAPBlockProvisioning) -> tuple[netbox.VlanGroupPayload, netbox.VlansPayload]:
        vlan_group_payload = build_sap_vlan_group_payload(sap, subscription)
        sap.ims_id = netbox.create(vlan_group_payload)  # Required for building vlan_payload
        vlan_payload = build_payload(sap, subscription)
        netbox.create(vlan_payload)
        return vlan_group_payload, vlan_payload

    return [create_sap(i) for i in saps]


def create_l2vpn_in_netbox(vc: VirtualCircuitBlockProvisioning, subscription: SubscriptionModel) -> tuple[int, netbox.L2vpnPayload]:
    """Provision the Virtual Circuit in Netbox and return the L2vpn payload."""
    payload: netbox.L2vpnPayload = build_payload(vc, subscription)

    # Example of implementing idempotency:
    # If the l2vpn was already created but for some reason the calling workflow failed to save the reference to it,
    # this check will prevent the workflow from trying (and failing) to create it again.
    # We can rely on the name for uniqueness because it contains the subscription id.
    if l2vpn := netbox.get_l2vpn(name=payload.name):
        logger.debug("L2VPN already exists in Netbox", l2vpn=l2vpn)
        return l2vpn.id, payload

    ims_id = netbox.create(payload)
    return ims_id, payload


def create_l2vpn_terminations_in_netbox(vc: VirtualCircuitBlockProvisioning) -> list[L2vpnTerminationPayload]:
    """Provision L2VPN terminations for the Virtual Circuit in Netbox and return the L2vpnTermination payloads."""
    l2vpn = netbox.get_l2vpn(id=vc.ims_id)

    def create_sap_payloads() -> Iterator[netbox.L2vpnTerminationPayload]:
        for sap in vc.saps:
            vlans = netbox.get_vlans(group_id=sap.ims_id)
            for vlan in vlans:
                yield netbox.L2vpnTerminationPayload(l2vpn=l2vpn.id, assigned_object_id=vlan.id)

    payloads = list(create_sap_payloads())
    for payload in payloads:
        netbox.create(payload)

    return payloads


def remove_l2vpn_in_netbox(vc: VirtualCircuitBlock) -> None:
    """Deprovision the Virtual Circuit in Netbox."""
    netbox.delete_l2vpn(id=vc.ims_id)
    # We rely on Netbox to delete the vlan terminations together with the l2vpn.


def remove_saps_in_netbox(saps: list[SAPBlock]) -> None:
    """Deprovision the SAPs in Netbox."""
    for sap in saps:
        vlans = netbox.get_vlans(group_id=sap.ims_id)
        for vlan in vlans:
            netbox.delete_vlan(id=vlan.id)
        netbox.delete_vlan_group(id=sap.ims_id)
