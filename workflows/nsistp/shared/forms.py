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
import re
from collections.abc import Iterator
from datetime import datetime
from functools import partial
from typing import Annotated, Any
from uuid import UUID

from annotated_types import BaseMetadata, Ge, Le
from orchestrator.db import ProductTable, db
from orchestrator.db.models import (
    SubscriptionTable,
)
from orchestrator.domain.base import SubscriptionModel
from orchestrator.types import SubscriptionLifecycle
from pydantic import AfterValidator, Field, ValidationInfo
from pydantic_forms.types import UUIDstr
from pydantic_forms.validators import Choice
from sqlalchemy import select
from typing_extensions import Doc

from products.product_blocks.port import PortMode
from products.product_types.nsistp import Nsistp, NsistpInactive
from utils.exceptions import (
    DuplicateValueError,
    FieldValueError,
)
from workflows.nsistp.shared.shared import (
    MAX_SPEED_POSSIBLE,
    CustomVlanRanges,
)
from workflows.shared import subscriptions_by_product_type_and_instance_value

TOPOLOGY_REGEX = r"^[-a-z0-9+,.;=_]+$"
STP_ID_REGEX = r"^[-a-z0-9+,.;=_:]+$"
NURN_REGEX = r"^urn:ogf:network:([^:]+):([0-9]+):([a-z0-9+,-.:;_!$()*@~&]*)$"
FQDN_REQEX = (
    r"^(?!.{255}|.{253}[^.])([a-z0-9](?:[-a-z-0-9]{0,61}[a-z0-9])?\.)*[a-z0-9](?:[-a-z0-9]{0,61}[a-z0-9])?[.]?$"
)


def port_selector() -> type[Choice]:
    port_subscriptions = subscriptions_by_product_type_and_instance_value(
        "Port", "port_mode", PortMode.TAGGED, [SubscriptionLifecycle.ACTIVE]
    )
    ports = {
        str(subscription.subscription_id): subscription.description
        for subscription in sorted(port_subscriptions, key=lambda port: port.description)
    }
    return Choice("Port", zip(ports.keys(), ports.items()))


def is_fqdn(hostname: str) -> bool:
    return re.match(FQDN_REQEX, hostname, re.IGNORECASE) is not None


def valid_date(date: str) -> tuple[bool, str | None]:
    def valid_month() -> tuple[bool, str | None]:
        month_str = date[4:6]
        month = int(month_str)
        if month < 1 or month > 12:
            return False, f"{month_str} is not a valid month number"
        return True, None

    def valid_day() -> tuple[bool, str | None]:
        try:
            datetime.fromisoformat(f"{date[0:4]}-{date[4:6]}-{date[6:8]}")
        except ValueError:
            return False, f"`{date}` is not a valid date"
        return True, None

    length = len(date)
    if length == 4:  # year
        pass  # No checks on reasonable year, so 9999 is allowed
    elif length in (6, 8):
        valid, message = valid_month()
        if not valid:
            return valid, message
        if length == 8:  # year + month + day
            return valid_day()
    else:
        return False, f"date `{date}` has invalid length"

    return True, None


def valid_nurn(nurn: str) -> tuple[bool, str | None]:
    if not (match := re.match(NURN_REGEX, nurn, re.IGNORECASE)):
        return False, "not a valid NSI STP identifier (urn:ogf:network:...)"

    hostname = match.group(1)
    if not is_fqdn(hostname):
        return False, f"{hostname} is not a valid fqdn"

    date = match.group(2)
    valid, message = valid_date(date)

    return valid, message


def validate_regex(
    regex: str,
    message: str,
    field: str | None,
) -> str | None:
    if field is None:
        return field

    if not re.match(regex, field, re.IGNORECASE):
        raise FieldValueError(f"{message} must match: {regex}")

    return field


def _get_nsistp_subscriptions(subscription_id: UUID | None) -> Iterator[Nsistp]:
    query = (
        select(SubscriptionTable.subscription_id)
        .join(ProductTable)
        .filter(
            ProductTable.product_type == "NSISTP",
            SubscriptionTable.status == SubscriptionLifecycle.ACTIVE,
            SubscriptionTable.subscription_id != subscription_id,
        )
    )
    result = db.session.scalars(query).all()
    return (Nsistp.from_subscription(subscription_id) for subscription_id in result)


def validate_stp_id_uniqueness(subscription_id: UUID | None, stp_id: str, info: ValidationInfo) -> str:
    values = info.data

    customer_id = values.get("customer_id")
    topology = values.get("topology")

    if customer_id and topology:

        def is_not_unique(nsistp: Nsistp) -> bool:
            return (
                nsistp.settings.stp_id.casefold() == stp_id.casefold()
                and nsistp.settings.topology.casefold() == topology.casefold()
            )

        subscriptions = _get_nsistp_subscriptions(subscription_id)
        if any(is_not_unique(nsistp) for nsistp in subscriptions):
            raise DuplicateValueError(f"STP identifier `{stp_id}` already exists for topology `{topology}`")

    return stp_id


def validate_both_aliases_empty_or_not(is_alias_in: str | None, is_alias_out: str | None) -> None:
    if bool(is_alias_in) != bool(is_alias_out):
        raise FieldValueError("NSI inbound and outbound isAlias should either both have a value or be empty")


def validate_nurn(nurn: str | None) -> str | None:
    if nurn:
        valid, message = valid_nurn(nurn)
        if not valid:
            raise FieldValueError(message)

    return nurn


def nsistp_fill_sap(subscription: NsistpInactive, subscription_id: UUIDstr, vlan: CustomVlanRanges | int) -> None:
    subscription.nsistp.sap.vlan = vlan
    subscription.nsistp.sap.port = SubscriptionModel.from_subscription(subscription_id).port  # type: ignore


def merge_uniforms(schema: dict[str, Any], *, to_merge: dict[str, Any]) -> None:
    schema["uniforms"] = schema.get("uniforms", {}) | to_merge


def uniforms_field(to_merge: dict[str, Any]) -> BaseMetadata:
    return Field(json_schema_extra=partial(merge_uniforms, to_merge=to_merge))


Topology = Annotated[
    str,
    AfterValidator(partial(validate_regex, TOPOLOGY_REGEX, "Topology")),
    Doc("topology string may only consist of characters from the set [-a-z+,.;=_]"),
]

StpId = Annotated[
    str,
    AfterValidator(partial(validate_regex, STP_ID_REGEX, "STP identifier")),
    Doc("must be unique along the set of NSISTP's in the same TOPOLOGY"),
]

StpDescription = Annotated[
    str,
    AfterValidator(partial(validate_regex, r"^[^<>&]*$", "STP description")),
    Doc("STP description may not contain characters from the set [<>&]"),
]

IsAlias = Annotated[
    str,
    AfterValidator(validate_nurn),
    Doc("ISALIAS conform https://www.ogf.org/documents/GFD.202.pdf"),
]

Bandwidth = Annotated[
    int,
    Ge(1),
    Le(MAX_SPEED_POSSIBLE),
    Doc(f"Bandwidth between {1} and {MAX_SPEED_POSSIBLE}"),
]

ServiceSpeed = Bandwidth
