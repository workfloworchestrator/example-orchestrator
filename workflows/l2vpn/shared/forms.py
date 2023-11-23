from orchestrator.types import SubscriptionLifecycle
from pydantic_forms.validators import Choice, choice_list

from products.product_blocks.port import PortMode
from workflows.shared import subscriptions_by_product_type_and_instance_value


def ports_selector(number_of_ports: int) -> list:
    port_subscriptions = subscriptions_by_product_type_and_instance_value(
        "Port", "port_mode", PortMode.TAGGED, [SubscriptionLifecycle.ACTIVE]
    )
    ports = {
        str(subscription.subscription_id): subscription.description
        for subscription in sorted(port_subscriptions, key=lambda port: port.description)
    }
    return choice_list(
        Choice("PortsEnum", zip(ports.keys(), ports.items())),  # type:ignore
        min_items=number_of_ports,
        max_items=number_of_ports,
        unique_items=True,
    )
