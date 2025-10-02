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
import random
import string
from collections import defaultdict
from collections.abc import Iterable
from typing import Any
from uuid import UUID

import structlog
from more_itertools import flatten
from nwastdlib.vlans import VlanRanges
from orchestrator.db import (
    SubscriptionTable,
)
from orchestrator.services import subscriptions
from orchestrator.types import SubscriptionLifecycle
from pydantic import BaseModel, Field, create_model, field_validator
from pydantic_core.core_schema import ValidationInfo
from pydantic_forms.types import State, UUIDstr

from forms.types import Tags, VisiblePortMode
from forms.validator.shared import (
    PortTag,
    _get_port_mode,
    get_port_speed_for_port_subscription,
)
from forms.validator.subscription_id import subscription_id
from forms.validator.vlan_ranges import NsiVlanRanges
from products.product_blocks.port import PortMode
from utils.exceptions import PortsValueError, VlanValueError
from workflows.nsistp.shared.nsistp import (
    get_available_vlans_by_port_id,
    nsistp_get_by_port_id,
)

logger = structlog.get_logger(__name__)

_port_tag_values = [str(value) for value in PortTag]


class ServicePortNoVlan(BaseModel):
    subscription_id: subscription_id(allowed_tags=_port_tag_values)  # type: ignore # noqa: F821

    def __repr__(self) -> str:
        return f"FormServicePortNoVlan({self.subscription_id=})"


class ServicePort(BaseModel):
    # By default we don't want constraints but having ports in the allowed taglist also signals the frontend
    # This way we get te correct behavior even though we don't constrain.. (Well we are sure we want ports here..)
    subscription_id: subscription_id(allowed_tags=_port_tag_values)  # type: ignore # noqa: F821
    vlan: VlanRanges

    def __repr__(self) -> str:
        # Help distinguish this from the ServicePort product type..
        print("subscription_id", self.subscription_id)

        return f"FormServicePort({self.subscription_id=}, {self.vlan=})"

    @field_validator("vlan")
    @classmethod
    def check_vlan(cls, vlan: VlanRanges, info: ValidationInfo) -> VlanRanges:
        # We assume an empty string is untagged and thus 0
        if not vlan:
            vlan = VlanRanges(0)

        subscription_id = info.data.get("subscription_id")
        if not subscription_id:
            return vlan

        subscription = subscriptions.get_subscription(
            subscription_id, model=SubscriptionTable
        )

        port_mode = _get_port_mode(subscription)

        if port_mode == PortMode.tagged and vlan == VlanRanges(0):
            raise VlanValueError(
                f"{port_mode} {subscription.product.tag} must have a vlan"
            )
        elif port_mode == PortMode.untagged and vlan != VlanRanges(0):  # noqa: RET506
            raise VlanValueError(
                f"{port_mode} {subscription.product.tag} can not have a vlan"
            )

        return vlan


class NsiServicePort(ServicePort):
    vlan: NsiVlanRanges


def _random_service_port_str() -> str:
    return "".join(
        random.choice(string.ascii_letters + string.digits) for _ in range(8)
    )  # noqa: S311


def service_port(
    visible_port_mode: VisiblePortMode | None = None,
    customer_id: UUIDstr | None = None,
    customer_key: str | None = None,
    customer_ports_only: bool = False,
    bandwidth: int | None = None,
    bandwidth_key: str | None = None,
    current: list[State] | None = None,
    allowed_tags: list[Tags] | None = None,
    disabled_ports: bool | None = None,
    excluded_subscriptions: list[UUID] | None = None,
    allowed_statuses: list[SubscriptionLifecycle] | None = None,
    nsi_vlans_only: bool = False,
) -> type[ServicePort]:
    """Extend the normal validator with configurable constraints."""

    @field_validator("vlan")  # type: ignore[misc]
    @classmethod
    def check_vlan_in_use(
        cls: ServicePort, v: VlanRanges, info: ValidationInfo
    ) -> VlanRanges:
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

        # used_vlans = VlanRanges(ims.get_vlans_by_subscription_id(subscription_id))
        # return available_vlans - used_vlans
        used_vlans = nsistp_get_by_port_id(subscription_id)
        print("used_vlans", used_vlans)
        nsistp_reserved_vlans = get_available_vlans_by_port_id(subscription_id)
        used_vlans = VlanRanges(
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

                current_selected_vlan_range = VlanRanges(current_selected_vlan)
                used_vlans -= current_selected_vlan_range
                current_selected_vlan_ranges = [
                    *current_selected_vlan_ranges,
                    *list(current_selected_vlan_range),
                ]

        # TODO (#1842): probably better to have a separate type/validator for this
        if nsi_vlans_only:
            vlan_list = list(v)
            invalid_ranges = [
                vlan
                for vlan in vlan_list
                if vlan not in list(nsistp_reserved_vlans)
                and vlan not in current_selected_vlan_ranges
            ]
            used_vlans -= nsistp_reserved_vlans

            if invalid_ranges:
                raise VlanValueError(
                    f"Vlan(s) {VlanRanges(invalid_ranges)} not valid nsi vlan range"
                )

        logger.info(
            "Validation info for current chosen vlans vs vlan already in use",
            current=current,
            used_vlans=used_vlans,
            subscription_id=subscription_id,
        )

        subscription = subscriptions.get_subscription(
            subscription_id, model=SubscriptionTable
        )
        print("subscription check", subscription)

        if v & used_vlans:
            port_mode = _get_port_mode(subscription)

            # for tagged only; for link_member/untagged say "SP already in use"
            if port_mode == PortMode.untagged or port_mode == PortMode.link_member:
                raise PortsValueError("Service Port already in use")
            raise VlanValueError(f"Vlan(s) {used_vlans} already in use")

        return v

    # Choose needed extra validators
    validators: dict[str, Any] = {
        "check_vlan_in_use": check_vlan_in_use,
    }

    # Choose Base Model
    base_model = NsiServicePort if nsi_vlans_only else ServicePort

    print("allowed_tags", allowed_tags)
    print("base_model", base_model)

    return create_model(
        f"{base_model.__name__}{_random_service_port_str()}Value",
        __base__=base_model,
        __validators__=validators,
        subscription_id=(
            subscription_id(
                visible_port_mode=visible_port_mode,
                customer_id=customer_id if customer_ports_only else None,
                customer_key=customer_key if customer_ports_only else None,
                bandwidth=bandwidth,
                bandwidth_key=bandwidth_key,
                allowed_tags=allowed_tags,
                excluded_subscriptions=excluded_subscriptions,
                allowed_statuses=allowed_statuses,
            ),
            Field(...),
        ),
    )


def service_port_no_vlan(
    visible_port_mode: VisiblePortMode | None = None,
    customer_id: UUIDstr | None = None,
    customer_key: str | None = None,
    customer_ports_only: bool = False,
    bandwidth: int | None = None,
    bandwidth_key: str | None = None,
    allowed_tags: list[Tags] | None = None,
    excluded_subscriptions: list[UUID] | None = None,
    allowed_statuses: list[SubscriptionLifecycle] | None = None,
) -> type[ServicePortNoVlan]:
    """Extend the normal validator with configurable constraints."""

    base_model = ServicePortNoVlan

    return create_model(
        f"{base_model.__name__}{_random_service_port_str()}Value",
        __base__=base_model,
        subscription_id=(
            subscription_id(
                visible_port_mode=visible_port_mode,
                customer_id=customer_id if customer_ports_only else None,
                customer_key=customer_key if customer_ports_only else None,
                bandwidth=bandwidth,
                bandwidth_key=bandwidth_key,
                allowed_tags=allowed_tags,
                excluded_subscriptions=excluded_subscriptions,
                allowed_statuses=allowed_statuses,
            ),
            Field(...),
        ),
    )


def service_port_values(values: Iterable[dict] | None) -> list[ServicePort] | None:
    if values is None:
        return None

    return [
        ServicePort.model_construct(
            subscription_id=UUID(v["subscription_id"]), vlan=VlanRanges(v["vlan"])
        )
        for v in values
    ]


def validate_single_vlan(v: list[ServicePort]) -> list[ServicePort]:
    if not all(sp.vlan.is_single_vlan for sp in v):
        raise VlanValueError("This product only supports a single vlan")
    return v


def validate_service_ports_bandwidth(
    v: ServicePort, info: ValidationInfo, *, bandwidth_key: str
) -> ServicePort:
    values = info.data

    if bandwidth := values.get(bandwidth_key):
        port_speed = get_port_speed_for_port_subscription(v.subscription_id)

        if int(bandwidth) > port_speed:
            raise PortsValueError(
                f"The port speed is lower than the desired speed {bandwidth}"
            )

    return v


def validate_owner_of_service_port(customer: str | None, v: ServicePort) -> ServicePort:
    if customer:
        subscription = subscriptions.get_subscription(v.subscription_id)

        if subscription.customer_id != str(customer):
            raise PortsValueError(f"Port subscription is not of customer {customer}")

    return v


def validate_service_ports_unique_vlans(v: list[ServicePort]) -> list[ServicePort]:
    vlans: dict[UUID, list[VlanRanges]] = defaultdict(list)
    for sap in v:
        for vlan in vlans[sap.subscription_id]:
            if not sap.vlan.isdisjoint(vlan):
                raise VlanValueError("Vlans are already in use")

        vlans[sap.subscription_id].append(sap.vlan)

    return v
