from orchestrator.forms.validators import Choice, choice_list

from products.product_blocks.shared.types import NodeStatus
from services import netbox


def site_selector() -> list:
    sites = {str(site.id): site.name for site in netbox.get_sites(status="active")}
    return choice_list(Choice("SitesEnum", zip(sites.keys(), sites.items())), min_items=1, max_items=1)  # type:ignore


def node_role_selector() -> list:
    roles = {str(role.id): role.name for role in netbox.get_device_roles()}
    return choice_list(Choice("RolesEnum", zip(roles.keys(), roles.items())), min_items=1, max_items=1)  # type:ignore


def node_type_selector(node_type: str) -> list:
    types = {
        str(type.id): " ".join((type.manufacturer.name, type.model))
        for type in netbox.get_device_types()
        if type.manufacturer.name == node_type
    }
    return choice_list(Choice("TypesEnum", zip(types.keys(), types.items())), min_items=1, max_items=1)  # type:ignore


def node_status_selector() -> list:
    statuses = NodeStatus.list()
    return Choice("NodeStatusEnum", zip(statuses, statuses))  # type:ignore
