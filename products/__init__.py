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


from orchestrator.domain import SUBSCRIPTION_MODEL_REGISTRY

from products.product_types.core_link import CoreLink
from products.product_types.l2vpn import L2vpn
from products.product_types.node import Node
from products.product_types.port import Port

SUBSCRIPTION_MODEL_REGISTRY.update(
    {
        "node Cisco": Node,
        "node Nokia": Node,
        "node Cumulus": Node,
        "node FRR": Node,
        "port 10G": Port,
        "port 100G": Port,
        "core link 10G": CoreLink,
        "core link 100G": CoreLink,
        "l2vpn": L2vpn,
    }
)
