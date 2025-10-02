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
from collections.abc import Iterator
from dataclasses import dataclass
from functools import partial
from typing import cast
from uuid import UUID

from annotated_types import SLOTS, BaseMetadata, GroupedMetadata
from pydantic import AfterValidator

from forms.validator.shared import (
    GetSubscriptionByIdFunc,
    get_port_speed_for_port_subscription,
    uniforms_field,
)
from utils.exceptions import PortsValueError


def validate_service_port_bandwidth(
    v: UUID, *, bandwidth: int, get_subscription: GetSubscriptionByIdFunc
) -> UUID:
    port_speed = get_port_speed_for_port_subscription(
        v, get_subscription=get_subscription
    )

    if bandwidth > port_speed:
        raise PortsValueError(
            f"The port speed is lower than the desired speed {bandwidth}"
        )

    return v


@dataclass(frozen=True, **SLOTS)
class SubscriptionBandwidthValidator(GroupedMetadata):
    bandwidth: int
    get_subscription: GetSubscriptionByIdFunc
    bandwidth_key: str | None = None

    def __iter__(self) -> Iterator[BaseMetadata]:
        validator = partial(
            validate_service_port_bandwidth,
            bandwidth=self.bandwidth,
            get_subscription=self.get_subscription,
        )
        yield cast(BaseMetadata, AfterValidator(validator))
        yield uniforms_field(
            {"bandwidth": self.bandwidth, "bandwidthKey": self.bandwidth_key}
        )
