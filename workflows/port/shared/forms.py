from orchestrator.forms.validators import Choice, choice_list
from orchestrator.types import SubscriptionLifecycle, UUIDstr

from products import Node
from products.product_blocks.port import PortMode
from services.netbox import get_device, get_interfaces
from workflows.shared import subscriptions_by_product_type


def node_selector() -> list:
    node_subscriptions = subscriptions_by_product_type("Node", [SubscriptionLifecycle.ACTIVE])
    nodes = {str(subscription.subscription_id): subscription.description for subscription in node_subscriptions}
    return choice_list(Choice("NodesEnum", zip(nodes.keys(), nodes.items())), min_items=1, max_items=1)  # type:ignore


def port_selector(node_subscription_id: UUIDstr, speed: int) -> list:
    node = Node.from_subscription(node_subscription_id)
    interfaces = {
        str(interface.id): interface.name
        for interface in get_interfaces(device=get_device(id=node.node.ims_id), speed=speed * 1000, enabled=False)
    }
    return choice_list(
        Choice("InterfacesEnum", zip(interfaces.keys(), interfaces.items())), min_items=1, max_items=1  # type:ignore
    )


def port_mode_selector() -> list:
    port_modes = [port_mode.value for port_mode in PortMode]
    return Choice("PortModesEnum", zip(port_modes, port_modes))  # type: ignore
