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

from orchestrator.db import ProductTable, db
from orchestrator.types import SubscriptionLifecycle

from products.product_types.node import Node, NodeInactive
from services.customer import DEFAULT_CUSTOMER


def test_node_new():
    product = ProductTable.query.filter(ProductTable.name == "node Cisco").one()

    diff = Node.diff_product_in_database(product.product_id)
    assert diff == {}

    subscription = Nis2Inactive.from_product_id(
        product_id=product.product_id, customer_id=DEFAULT_CUSTOMER, status=SubscriptionLifecycle.INITIAL
    )

    assert subscription.subscription_id is not None
    assert subscription.insync is False

    assert subscription.description == f"Initial subscription of {product.description}"
    subscription.save()

    subscription_changed = NodeInactive.from_subscription(nis2.subscription_id)
    assert subscription == subscription_changed


def test_node_load_and_save_db(node_subscription):
    subscription = Node.from_subscription(node_subscription)

    assert subscription.insync is True

    subscription.description = "Changed description"

    subscription.save()

    # Explicit commit here as we are not running in the context of a step
    db.session.commit()

    subscription_changed = Node.from_subscription(node_subscription)
    assert subscription_changed.description == "Changed description"
