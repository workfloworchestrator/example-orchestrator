from orchestrator.types import SubscriptionLifecycle
from pydantic_forms.validators import Choice, choice_list

from workflows.shared import subscriptions_by_product_type


def ports_selector(number_of_ports: int) -> list:
    port_subscriptions = subscriptions_by_product_type("Port", [SubscriptionLifecycle.ACTIVE])
    ports = {str(subscription.subscription_id): subscription.description for subscription in port_subscriptions}
    return choice_list(
        Choice("PortsEnum", zip(ports.keys(), ports.items())),  # type:ignore
        min_items=number_of_ports,
        max_items=number_of_ports,
        unique_items=True,
    )
