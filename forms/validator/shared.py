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
from collections.abc import Callable
from enum import StrEnum, auto
from functools import partial
from typing import Any
from uuid import UUID

import structlog
from annotated_types import BaseMetadata
from orchestrator.db import (
    SubscriptionTable,
)
from orchestrator.services import subscriptions
from pydantic import Field

from products.product_types.port import Port as ServicePort

logger = structlog.get_logger(__name__)

GetSubscriptionByIdFunc = Callable[[UUID], SubscriptionTable]

PORT_SPEED = "port_speed"
MAX_SPEED_POSSIBLE = 400_000


class PortMode(StrEnum):
    tagged = auto()
    untagged = auto()
    link_member = auto()


class PortTag(StrEnum):
    SP = "SP"
    SPNL = "SPNL"
    AGGSP = "AGGSP"
    AGGSPNL = "AGGSPNL"
    MSC = "MSC"
    MSCNL = "MSCNL"
    IRBSP = "IRBSP"


def _get_port_mode(subscription: SubscriptionTable) -> PortMode:
    if subscription.product.tag in [PortTag.AGGSP + PortTag.SP]:
        return subscription.port_mode
    return PortMode.tagged


def get_port_speed_for_port_subscription(
    subscription_id: UUID, get_subscription: GetSubscriptionByIdFunc | None = None
) -> int:
    print("HELLO from get_port_speed_for_port_subscription")
    if get_subscription:
        subscription = get_subscription(subscription_id)
        print("subscription from get_subscription", subscription)
    else:
        subscription = subscriptions.get_subscription(
            subscription_id, model=SubscriptionTable
        )

    if subscription.tag in [PortTag.MSC + PortTag.AGGSP]:
        port_speed = ServicePort.from_subscription(
            subscription.subscription_id
        ).get_port_speed()
    elif subscription.tag in PortTag.IRBSP:
        port_speed = MAX_SPEED_POSSIBLE
    else:
        port_speed = int(subscription.product.fixed_input_value(PORT_SPEED))

    logger.info(
        "Validation determined speed for port",
        product_tag=subscription.tag,
        port_speed=port_speed,
    )
    return port_speed


def merge_uniforms(schema: dict[str, Any], *, to_merge: dict[str, Any]) -> None:
    schema["uniforms"] = schema.get("uniforms", {}) | to_merge


def uniforms_field(to_merge: dict[str, Any]) -> BaseMetadata:
    return Field(json_schema_extra=partial(merge_uniforms, to_merge=to_merge))
