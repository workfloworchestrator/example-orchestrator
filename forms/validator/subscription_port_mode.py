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

from forms.types import VisiblePortMode
from forms.validator.shared import (
    GetSubscriptionByIdFunc,
    PortMode,
    _get_port_mode,
    uniforms_field,
)
from utils.exceptions import PortsModeValueError


def validate_port_mode(
    v: UUID,
    *,
    visible_port_mode: VisiblePortMode,
    get_subscription: GetSubscriptionByIdFunc,
) -> UUID:
    subscription = get_subscription(v)
    port_mode = _get_port_mode(subscription)

    if visible_port_mode == "normal" and port_mode == PortMode.link_member:
        raise PortsModeValueError("normal", "Port mode should be 'untagged' or 'tagged")
    elif visible_port_mode == "link_member" and port_mode != PortMode.link_member:  # noqa: RET506
        raise PortsModeValueError(
            PortMode.link_member, "Port mode should be 'link_member'"
        )
    elif visible_port_mode == "untagged" and port_mode != PortMode.untagged:
        raise PortsModeValueError(PortMode.untagged, "Port mode should be 'untagged'")
    elif visible_port_mode == "tagged" and port_mode != PortMode.tagged:
        raise PortsModeValueError(PortMode.tagged, "Port mode should be 'tagged'")
    return v


@dataclass(frozen=True, **SLOTS)
class SubscriptionPortModeValidator(GroupedMetadata):
    visible_port_mode: VisiblePortMode
    get_subscription: GetSubscriptionByIdFunc

    def __iter__(self) -> Iterator[BaseMetadata]:
        validator = partial(
            validate_port_mode,
            visible_port_mode=self.visible_port_mode,
            get_subscription=self.get_subscription,
        )
        yield cast(BaseMetadata, AfterValidator(validator))
        yield uniforms_field({"visiblePortMode": self.visible_port_mode})
