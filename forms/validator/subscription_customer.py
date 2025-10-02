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
from pydantic_forms.types import UUIDstr

from forms.validator.shared import GetSubscriptionByIdFunc, uniforms_field
from utils.exceptions import CustomerValueError


def validate_customer(
    v: UUID, *, customer_id: UUIDstr, get_subscription: GetSubscriptionByIdFunc
) -> UUID:
    subscription = get_subscription(v)

    if subscription.customer_id != str(customer_id):
        raise CustomerValueError(f"Subscription is not of customer {customer_id}")
    return v


@dataclass(frozen=True, **SLOTS)
class SubscriptionCustomerValidator(GroupedMetadata):
    customer_id: UUIDstr
    get_subscription: GetSubscriptionByIdFunc
    customer_key: str | None = None

    def __iter__(self) -> Iterator[BaseMetadata]:
        validator = partial(
            validate_customer,
            customer_id=self.customer_id,
            get_subscription=self.get_subscription,
        )
        yield cast(BaseMetadata, AfterValidator(validator))
        yield uniforms_field(
            {"customerId": self.customer_id, "customerKey": self.customer_key}
        )
