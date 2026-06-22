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

from orchestrator.core.graphql.schemas import DEFAULT_GRAPHQL_MODELS

from graphql_utils.federation import NodeBlockInactive
from graphql_utils.resolvers import custom_subscription_interface

CUSTOM_GRAPHQL_MODELS = DEFAULT_GRAPHQL_MODELS | {
    "NodeBlockInactive": NodeBlockInactive,
    "NodeBlock": NodeBlockInactive,
}

__all__ = [
    "CUSTOM_GRAPHQL_MODELS",
    "custom_subscription_interface",
]
