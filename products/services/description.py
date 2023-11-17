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

from functools import singledispatch
from typing import Union

from orchestrator.domain.base import ProductBlockModel, ProductModel, SubscriptionModel

from products.product_types.core_link import CoreLinkProvisioning
from products.product_types.l2vpn import L2vpnProvisioning
from products.product_types.node import NodeProvisioning
from products.product_types.port import PortProvisioning
from utils.singledispatch import single_dispatch_base


@singledispatch
def description(model: Union[ProductModel, ProductBlockModel, SubscriptionModel]) -> str:
    """Build subscription description (generic function).

    Specific implementations of this generic function will specify the model types they work on.

    Args:
        model: Domain model for which to construct a description.

    Returns:
    ---
        The constructed description.

    Raises:
    --
        TypeError: in case a specific implementation could not be found. The domain model it was called for will be
            part of the error message.

    """
    return single_dispatch_base(description, model)


@description.register
def node_product_description(node: NodeProvisioning) -> str:
    return f"node {node.node.node_name} ({node.node.node_status})"


@description.register
def port_product_description(port: PortProvisioning) -> str:
    return f"{port.product.name} {port.port.node.node_name} {port.port.port_name} {port.port.port_description}"


@description.register
def core_link_product_description(core_link: CoreLinkProvisioning) -> str:
    maintenance = " (MAINTENANCE)" if core_link.core_link.under_maintenance else ""
    return (
        f"{core_link.product.name} "
        f"{core_link.core_link.ports[0].node.node_name} {core_link.core_link.ports[0].port_name}"
        " <-> "
        f"{core_link.core_link.ports[1].port_name} {core_link.core_link.ports[1].node.node_name}"
        f"{maintenance}"
    )


@description.register
def l2vpn_product_description(l2vpn: L2vpnProvisioning) -> str:
    return (
        f"{l2vpn.product.tag} "
        f"{l2vpn.virtual_circuit.speed} Mbit/s "
        f"({'-'.join(sorted(list(set([sap.port.node.node_name for sap in l2vpn.virtual_circuit.saps]))))})"
    )
