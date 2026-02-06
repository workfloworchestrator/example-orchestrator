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
from orchestrator.graphql.schemas import DEFAULT_GRAPHQL_MODELS

from products.product_blocks.node import NodeBlockInactive as _NodeBlockInactive


@strawberry.federation.type(keys=["id"])
class DeviceType():
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
