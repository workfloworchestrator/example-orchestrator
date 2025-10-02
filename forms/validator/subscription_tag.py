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

from forms.types import Tags
from forms.validator.shared import GetSubscriptionByIdFunc, uniforms_field
from utils.exceptions import ProductValueError


def validate_product_tags(
    v: UUID,
    *,
    allowed_product_tags: list[Tags],
    get_subscription: GetSubscriptionByIdFunc,
) -> UUID:
    subscription = get_subscription(v)
    if subscription.product.tag not in allowed_product_tags:
        raise ProductValueError(
            f"Subscription is of the wrong product. Allowed product tags: {allowed_product_tags}"
        )
    return v


@dataclass(frozen=True, **SLOTS)
class SubscriptionTagValidator(GroupedMetadata):
    allowed_product_tags: list[Tags]
    get_subscription: GetSubscriptionByIdFunc

    def __iter__(self) -> Iterator[BaseMetadata]:
        validator = partial(
            validate_product_tags,
            allowed_product_tags=self.allowed_product_tags,
            get_subscription=self.get_subscription,
        )
        yield cast(BaseMetadata, AfterValidator(validator))
        yield uniforms_field({"tags": list(map(str, self.allowed_product_tags))})
