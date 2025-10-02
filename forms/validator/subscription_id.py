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
import random
import string
from collections.abc import Generator
from types import new_class
from typing import Annotated, Any
from uuid import UUID

import structlog
from orchestrator.db import (
    SubscriptionTable,
)
from orchestrator.services import subscriptions
from orchestrator.types import SubscriptionLifecycle
from pydantic import GetCoreSchemaHandler, GetJsonSchemaHandler
from pydantic.json_schema import JsonSchemaValue
from pydantic_core import CoreSchema
from pydantic_forms.types import UUIDstr

from forms.types import Tags, VisiblePortMode  # move to other location
from forms.validator.shared import GetSubscriptionByIdFunc
from forms.validator.subscription_bandwidth import SubscriptionBandwidthValidator
from forms.validator.subscription_customer import SubscriptionCustomerValidator
from forms.validator.subscription_exclude_subscriptions import (
    SubscriptionExcludeSubscriptionsValidator,
)
from forms.validator.subscription_in_sync import SubscriptionInSyncValidator
from forms.validator.subscription_is_port import SubscriptionIsPortValidator
from forms.validator.subscription_port_mode import SubscriptionPortModeValidator
from forms.validator.subscription_product_id import SubscriptionProductIdValidator
from forms.validator.subscription_status import SubscriptionStatusValidator
from forms.validator.subscription_tag import SubscriptionTagValidator

logger = structlog.get_logger(__name__)


class SubscriptionId:  # TODO #1983 change to Annotated Type
    @classmethod
    def __get_pydantic_json_schema__(
        cls, schema: CoreSchema, handler: GetJsonSchemaHandler
    ) -> JsonSchemaValue:
        json_schema_extra = {"type": "string", "format": "subscriptionId"}
        json_schema = handler(schema)
        json_schema.update(json_schema_extra)
        return json_schema

    @classmethod
    def __get_pydantic_core_schema__(
        cls, _source_type: Any, handler: GetCoreSchemaHandler
    ) -> CoreSchema:
        return handler(UUID)


def default_get_subscription(v: UUID) -> SubscriptionTable:
    print("uuid v", v)
    print("subscription", subscriptions.get_subscription(v, model=SubscriptionTable))

    return subscriptions.get_subscription(v, model=SubscriptionTable)


def subscription_id(
    product_ids: list[UUID] | None = None,
    visible_port_mode: VisiblePortMode | None = None,
    customer_id: UUIDstr | None = None,
    customer_key: str | None = None,
    bandwidth: int | None = None,
    bandwidth_key: str | None = None,
    allowed_tags: list[Tags] | None = None,
    excluded_subscriptions: list[UUID] | None = None,
    allowed_statuses: list[SubscriptionLifecycle] | None = None,
    allow_out_of_sync: bool = False,
    get_subscription: GetSubscriptionByIdFunc | None = None,
) -> type:
    # Create type name
    org_string = f"O{str(customer_id)[0:8]}" if customer_id else ""
    bandwidth_str = f"B{bandwidth}" if bandwidth else ""
    random_str = "".join(
        random.choice(string.ascii_letters + string.digits) for _ in range(8)
    )  # noqa: S311
    class_name = (
        f"SubscriptionId{visible_port_mode}{org_string}{bandwidth_str}{random_str}Value"
    )

    # TODO: caching is disabled here since it was in the wrong place. First #1983 has to be fixed
    get_subscription = (
        get_subscription if get_subscription else default_get_subscription
    )

    def get_validators() -> Generator[Any, Any, None]:
        yield SubscriptionStatusValidator(
            allowed_statuses=allowed_statuses, get_subscription=get_subscription
        )
        if product_ids:
            yield SubscriptionProductIdValidator(
                allowed_product_ids=product_ids, get_subscription=get_subscription
            )
        if allowed_tags:
            yield SubscriptionTagValidator(
                allowed_product_tags=allowed_tags, get_subscription=get_subscription
            )
        if visible_port_mode:
            yield SubscriptionIsPortValidator(get_subscription=get_subscription)
            yield SubscriptionPortModeValidator(
                visible_port_mode=visible_port_mode, get_subscription=get_subscription
            )
        if excluded_subscriptions:
            yield SubscriptionExcludeSubscriptionsValidator(
                excluded_subscriptions=excluded_subscriptions
            )
        if customer_id:
            print("customer_id in get_validators", customer_id)
            yield SubscriptionCustomerValidator(
                customer_id=customer_id,
                customer_key=customer_key,
                get_subscription=get_subscription,
            )
        if not allow_out_of_sync:
            yield SubscriptionInSyncValidator(get_subscription=get_subscription)
        if bandwidth is not None:
            yield SubscriptionBandwidthValidator(
                bandwidth=bandwidth,
                bandwidth_key=bandwidth_key,
                get_subscription=get_subscription,
            )

    validator = new_class(class_name, (SubscriptionId,))
    return Annotated[validator, *get_validators()]  # type: ignore
