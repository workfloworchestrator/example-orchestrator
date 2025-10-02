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
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from functools import partial
from typing import cast
from uuid import UUID

from annotated_types import SLOTS, BaseMetadata, GroupedMetadata
from orchestrator.db.models import SubscriptionTable
from pydantic import AfterValidator

from utils.exceptions import InSyncValueError

GetSubscriptionByIdFunc = Callable[[UUID], SubscriptionTable]


def validate_in_sync(v: UUID, *, get_subscription: GetSubscriptionByIdFunc) -> UUID:
    subscription = get_subscription(v)
    if not subscription.insync:
        raise InSyncValueError("Subscription is not in sync")

    return v


@dataclass(frozen=True, **SLOTS)
class SubscriptionInSyncValidator(GroupedMetadata):
    get_subscription: GetSubscriptionByIdFunc

    def __iter__(self) -> Iterator[BaseMetadata]:
        validator = partial(validate_in_sync, get_subscription=self.get_subscription)
        yield cast(BaseMetadata, AfterValidator(validator))
