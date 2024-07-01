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

import structlog
from orchestrator.db import ProductTable, db
from orchestrator.domain.base import SubscriptionModel
from orchestrator.types import SubscriptionLifecycle

from products.product_types.node import NodeInactive
from services.customer import DEFAULT_CUSTOMER

logger = structlog.getLogger(__name__)


def make_node_subscription(
    customer_id=DEFAULT_CUSTOMER,
    product_name="node Cisco",  # or "node Cisco", "node Nokia"
    insync=True,
    role_id=1,
    type_id=1,
    site_id=1,
    node_name="TestNode",
    node_description="TestNode Description",
    node_status=NodeStatus.Active,
    ims_id=1,
    nrm_id=1,
    ipv4_ipam_id=1,
    ipv6_ipam_id=1,
    lifecycle_state=SubscriptionLifecycle.ACTIVE,
):
    """Node fixture factory.

    Returns: The subscription_id of the created fixture.
    """
    product = ProductTable.query.filter(ProductTable.name == product_name).one()
    description = f"{product.name} description"
    subscription = NodeInactive.from_product_id(
        product_id=product.product_id,
        customer_id=customer_id,
        status=SubscriptionLifecycle.INITIAL,
        insync=insync,
    )
    subscription.description = description
    subscription.node.node_description = node_description
    subscription.node.role_id = role_id
    subscription.node.type_id = type_id
    subscription.node.site_id = site_id
    subscription.node.node_name = node_name
    subscription.node.node_description = node_description
    subscription.node.node_status = node_status
    subscription.node.ims_id = ims_id
    subscription.node.nrm_id = nrm_id
    subscription.node.ipv4_ipam_id = ipv4_ipam_id
    subscription.node.ipv6_ipam_id = ipv6_ipam_id

    subscription.save()
    subscription = SubscriptionModel.from_other_lifecycle(subscription, lifecycle_state)
    subscription.save()
    db.session.commit()

    return str(subscription.subscription_id)
