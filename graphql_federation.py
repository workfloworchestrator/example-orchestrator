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
from orchestrator.core.graphql import Query
from orchestrator.core.graphql.pagination import Connection
from orchestrator.core.graphql.schemas import DEFAULT_GRAPHQL_MODELS
from orchestrator.core.graphql.schemas.customer import CustomerType
from orchestrator.core.graphql.types import GraphqlFilter, GraphqlSort, OrchestratorInfo
from orchestrator.core.graphql.utils.to_graphql_result_page import to_graphql_result_page
from sqlalchemy import func, select

from db.models import CustomerTable, db
from oauth2_lib.strawberry import authenticated_field
from products.product_blocks.node import NodeBlockInactive as _NodeBlockInactive


@strawberry.federation.type(keys=["id"])
class DeviceType:
    """The name of this class matches that in Netbox."""

    id: strawberry.ID


@strawberry.experimental.pydantic.type(model=_NodeBlockInactive, all_fields=True)
class NodeBlockInactive:
    @strawberry.field(description="Get netbox device by IMS ID")
    def netbox_device(self) -> DeviceType | None:
        """Add a field which contains an object with nothing but an ID.

        Federation resolves the other DeviceType fields from Netbox.
        """
        return DeviceType(id=self.ims_id) if self.ims_id else None


CUSTOM_GRAPHQL_MODELS = DEFAULT_GRAPHQL_MODELS | {
    "NodeBlockInactive": NodeBlockInactive,
    "NodeBlock": NodeBlockInactive,
}


async def resolve_customers(
    info: OrchestratorInfo,
    filter_by: list[GraphqlFilter] | None = None,
    sort_by: list[GraphqlSort] | None = None,
    first: int = 10,
    after: int = 0,
) -> Connection[CustomerType]:
    """Resolve customers from the local CustomerTable instead of the default static customer."""
    stmt = select(CustomerTable)
    total = db.session.scalar(select(func.count()).select_from(stmt.subquery()))
    stmt = stmt.offset(after).limit(first + 1)
    customers = db.session.execute(stmt).scalars().all()

    graphql_customers = [
        CustomerType(customer_id=c.customer_id, fullname=c.fullname, shortcode=c.shortcode) for c in customers
    ]
    return to_graphql_result_page(graphql_customers, first, after, total)


@strawberry.federation.type(description="Example orchestrator queries")
class ExampleQuery(Query):
    customers: Connection[CustomerType] = authenticated_field(
        resolver=resolve_customers, description="Returns customers from the local database"
    )
