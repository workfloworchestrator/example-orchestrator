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


from orchestrator.domain.base import SubscriptionModel
from orchestrator.types import SubscriptionLifecycle, strEnum

from products.product_blocks.node import (
    NodeBlock,
    NodeBlockInactive,
    NodeBlockProvisioning,
)


class Node_Type(strEnum):
    Cisco = "Cisco"
    Nokia = "Nokia"


class NodeInactive(SubscriptionModel, is_base=True):
    node_type: Node_Type
    node: NodeBlockInactive


class NodeProvisioning(NodeInactive, lifecycle=[SubscriptionLifecycle.PROVISIONING]):
    node_type: Node_Type
    node: NodeBlockProvisioning


class Node(NodeProvisioning, lifecycle=[SubscriptionLifecycle.ACTIVE]):
    node_type: Node_Type
    node: NodeBlock
