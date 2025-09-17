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
from typing import Annotated
from uuid import UUID

from annotated_types import doc
from more_itertools import one
from pydantic import AfterValidator, ValidationInfo
from pydantic_forms.types import State
from sqlalchemy import select

from orchestrator.db import ProductTable, db
from orchestrator.domain.base import SubscriptionModel
from orchestrator.types import SubscriptionLifecycle
from surf.config.service_port_tags import SN8_PORT_TAGS_AGGSP, SN8_PORT_TAGS_MSC, SN8_PORT_TAGS_SP_ALL
from surf.db import SurfSubscriptionTable
from surf.forms.validator.service_port import service_port
from surf.products.product_types.sn8_nsistp import Nsistp, NsistpInactive
from surf.utils.exceptions import DuplicateValueError, FieldValueError

TOPOLOGY_REGEX = r"^[-a-z0-9+,.;=_]+$"
STP_ID_REGEX = r"^[-a-z0-9+,.;=_:]+$"
NURN_REGEX = r"^urn:ogf:network:([^:]+):([0-9]+):([a-z0-9+,-.:;_!$()*@~&]*)$"
FQDN_REQEX = (
    r"^(?!.{255}|.{253}[^.])([a-z0-9](?:[-a-z-0-9]{0,61}[a-z0-9])?\.)*[a-z0-9](?:[-a-z0-9]{0,61}[a-z0-9])?[.]?$"
)


def nsistp_service_port(current: list[State] | None = None) -> type:
    return service_port(
        visible_port_mode="tagged",
        allowed_tags=SN8_PORT_TAGS_SP_ALL + SN8_PORT_TAGS_AGGSP + SN8_PORT_TAGS_MSC,
        current=current,
    )


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
        select(SurfSubscriptionTable.subscription_id)
        .join(ProductTable)
        .filter(
            ProductTable.product_type == "NSISTP",
            SurfSubscriptionTable.status == SubscriptionLifecycle.ACTIVE,
            SurfSubscriptionTable.subscription_id != subscription_id,
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


StpId = Annotated[
    str,
    AfterValidator(partial(validate_regex, STP_ID_REGEX, "STP identifier")),
    doc("must be unique along the set of NSISTP's in the same TOPOLOGY"),
]


def validate_both_aliases_empty_or_not(is_alias_in: str | None, is_alias_out: str | None) -> None:
    if bool(is_alias_in) != bool(is_alias_out):
        raise FieldValueError("NSI inbound and outbound isAlias should either both have a value or be empty")


def validate_nurn(nurn: str | None) -> str | None:
    if nurn:
        valid, message = valid_nurn(nurn)
        if not valid:
            raise FieldValueError(message)

    return nurn


def nsistp_fill_sap(subscription: NsistpInactive, service_ports: list[dict]) -> None:
    sp = one(service_ports)
    subscription.settings.sap.vlanrange = sp["vlan"]
    # SubscriptionModel can be any type of ServicePort
    subscription.settings.sap.port = SubscriptionModel.from_subscription(sp["subscription_id"]).port  # type: ignore


IsAlias = Annotated[
    str, AfterValidator(validate_nurn), doc("ISALIAS conform https://www.ogf.org/documents/GFD.202.pdf")
]

StpDescription = Annotated[
    str,
    AfterValidator(partial(validate_regex, r"^[^<>&]*$", "STP description")),
    doc("STP description may not contain characters from the set [<>&]"),
]

Topology = Annotated[
    str,
    AfterValidator(partial(validate_regex, TOPOLOGY_REGEX, "Topology")),
    doc("topology string may only consist of characters from the set [-a-z+,.;=_]"),
]
