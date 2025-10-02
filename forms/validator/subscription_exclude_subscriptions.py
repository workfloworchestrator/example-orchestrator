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

from forms.validator.shared import uniforms_field
from utils.exceptions import ProductValueError


def validate_excluded_subscriptions(
    v: UUID, *, excluded_subscriptions: list[UUID]
) -> UUID:
    if excluded_subscriptions and v in excluded_subscriptions:
        raise ProductValueError(
            "Subscription is in the excluded list and cannot be chosen"
        )

    return v


@dataclass(frozen=True, **SLOTS)
class SubscriptionExcludeSubscriptionsValidator(GroupedMetadata):
    excluded_subscriptions: list[UUID]

    def __iter__(self) -> Iterator[BaseMetadata]:
        validator = partial(
            validate_excluded_subscriptions,
            excluded_subscriptions=self.excluded_subscriptions,
        )
        yield cast(BaseMetadata, AfterValidator(validator))
        yield uniforms_field(
            {"excludedSubscriptionIds": list(map(str, self.excluded_subscriptions))}
        )
