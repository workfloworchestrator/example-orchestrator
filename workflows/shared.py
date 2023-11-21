from typing import List

from orchestrator.db import (
    ProductTable,
    ResourceTypeTable,
    SubscriptionInstanceTable,
    SubscriptionInstanceValueTable,
    SubscriptionTable,
)
from orchestrator.forms.validators import Choice, choice_list
from orchestrator.types import SubscriptionLifecycle, UUIDstr

from products import Node

# from products.product_blocks.port import PortBlock, PortBlockInactive
# from products.product_blocks.sap import SAPBlock, SAPBlockInactive, SAPBlockProvisioning
from services.netbox import get_device, get_interfaces


def pop_first(dictionary: dict, key: str) -> None:
    dictionary[key] = dictionary[key].pop(0)


def subscriptions_by_product_type(product_type: str, status: List[SubscriptionLifecycle]) -> List[SubscriptionTable]:
    """
    retrieve_subscription_list_by_product This function lets you retreive a
    list of all subscriptions of a given product type. For example, you could
    call this like so:

    >>> subscriptions_by_product_type("Node", [SubscriptionLifecycle.ACTIVE, SubscriptionLifecycle.PROVISIONING])
    [SubscriptionTable(su...note=None), SubscriptionTable(su...note=None)]

    You now have a list of all active Node subscription instances and can then
    use them in your workflow.

    Args:
        product_type (str): The prouduct type in the DB (i.e. Node, User, etc.)
        status (List[SubscriptionLifecycle]): The lifecycle states you want returned (i.e.
        SubscriptionLifecycle.ACTIVE)

    Returns:
        List[SubscriptionTable]: A list of all the subscriptions that match
        your criteria.
    """
    subscriptions = (
        SubscriptionTable.query.join(ProductTable)
        .filter(ProductTable.product_type == product_type)
        .filter(SubscriptionTable.status.in_(status))
        .all()
    )
    return subscriptions


def subscriptions_by_product_type_and_instance_value(
    product_type: str, resource_type: str, value: str, status: List[SubscriptionLifecycle]
) -> List[SubscriptionTable]:
    """Retrieve a list of Subscriptions by product_type, resource_type and value.

    Args:
        product_type: type of subscriptions
        resource_type: name of the resource type
        value: value of the resource type
        status: lifecycle status of the subscriptions

    Returns: Subscription or None

    """
    return (
        SubscriptionTable.query.join(ProductTable)
        .join(SubscriptionInstanceTable)
        .join(SubscriptionInstanceValueTable)
        .join(ResourceTypeTable)
        .filter(ProductTable.product_type == product_type)
        .filter(SubscriptionInstanceValueTable.value == value)
        .filter(ResourceTypeTable.resource_type == resource_type)
        .filter(SubscriptionTable.status.in_(status))
        .all()
    )


def node_selector(enum: str = "NodesEnum") -> list:
    node_subscriptions = subscriptions_by_product_type("Node", [SubscriptionLifecycle.ACTIVE])
    nodes = {str(subscription.subscription_id): subscription.description for subscription in node_subscriptions}
    return choice_list(Choice(enum, zip(nodes.keys(), nodes.items())), min_items=1, max_items=1)  # type:ignore


def free_port_selector(node_subscription_id: UUIDstr, speed: int, enum: str = "PortsEnum") -> list:
    node = Node.from_subscription(node_subscription_id)
    interfaces = {
        str(interface.id): interface.name
        for interface in get_interfaces(device=get_device(id=node.node.ims_id), speed=speed * 1000, enabled=False)
    }
    return choice_list(
        Choice(enum, zip(interfaces.keys(), interfaces.items())), min_items=1, max_items=1  # type:ignore
    )
