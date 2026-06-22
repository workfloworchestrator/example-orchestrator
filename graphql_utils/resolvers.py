# Copyright 2019-2023 SURF.
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

import strawberry
from orchestrator.core.db import db
from orchestrator.core.db.filters import create_memoized_field_list, generic_filter_from_clauses
from orchestrator.core.db.filters.search_filters import default_inferred_column_clauses
from orchestrator.core.db.sorting import generic_column_sort, generic_sort
from orchestrator.core.graphql.schemas.customer import CustomerType
from orchestrator.core.graphql.schemas.process import ProcessType
from orchestrator.core.graphql.schemas.subscription import SubscriptionInterface
from orchestrator.core.graphql.utils.override_class import override_class
from orchestrator.core.utils.helpers import to_camel
from sqlalchemy import select
from sqlalchemy.inspection import inspect

from db.models import CustomerTable

CUSTOMER_TABLE_COLUMN_CLAUSES = default_inferred_column_clauses(CustomerTable)
CUSTOMER_SORT_FUNCTIONS_BY_COLUMN = {
    to_camel(key): generic_column_sort(value, CustomerTable) for [key, value] in inspect(CustomerTable).columns.items()
}
customer_filter_fields = create_memoized_field_list(CUSTOMER_TABLE_COLUMN_CLAUSES)
customer_sort_fields = create_memoized_field_list(CUSTOMER_SORT_FUNCTIONS_BY_COLUMN)
filter_customers = generic_filter_from_clauses(CUSTOMER_TABLE_COLUMN_CLAUSES)
sort_customers = generic_sort(CUSTOMER_SORT_FUNCTIONS_BY_COLUMN)


def _resolve_customer_from_table(customer_id: str) -> CustomerType:
    stmt = select(CustomerTable).where(CustomerTable.customer_id == customer_id)
    customer = db.session.execute(stmt).scalars().one_or_none()
    if customer:
        return CustomerType(
            customer_id=customer.customer_id,
            fullname=customer.fullname,
            shortcode=customer.shortcode,
        )
    return CustomerType(
        customer_id=str(customer_id),
        fullname="missing",
        shortcode="missing",
    )


async def resolve_subscription_customer(root: SubscriptionInterface) -> CustomerType:
    return _resolve_customer_from_table(root.customer_id)


async def resolve_process_customer(root: ProcessType) -> CustomerType:
    return _resolve_customer_from_table(root.customer_id)


subscription_customer_field = strawberry.field(
    resolver=resolve_subscription_customer,
    description="Returns customer of a subscription",
)
subscription_customer_field.name = "customer"

process_customer_field = strawberry.field(
    resolver=resolve_process_customer,
    description="Returns customer of a process",
)
process_customer_field.name = "customer"

custom_subscription_interface = override_class(SubscriptionInterface, [subscription_customer_field])
override_class(ProcessType, [process_customer_field])
