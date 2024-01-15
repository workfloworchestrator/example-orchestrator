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


from orchestrator.types import SubscriptionLifecycle
from pydantic_forms.validators import Choice, choice_list

from products.product_blocks.port import PortMode
from workflows.shared import AllowedNumberOfL2pnPorts, subscriptions_by_product_type_and_instance_value


def ports_selector(number_of_ports: AllowedNumberOfL2pnPorts) -> type[list[Choice]]:
    port_subscriptions = subscriptions_by_product_type_and_instance_value(
        "Port", "port_mode", PortMode.TAGGED, [SubscriptionLifecycle.ACTIVE]
    )
    ports = {
        str(subscription.subscription_id): subscription.description
        for subscription in sorted(port_subscriptions, key=lambda port: port.description)
    }
    return choice_list(
        Choice("PortsEnum", zip(ports.keys(), ports.items())),  # type: ignore
        min_items=number_of_ports,
        max_items=number_of_ports,
        unique_items=True,
    )
