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
from dataclasses import asdict, dataclass
from functools import singledispatch
from os import environ
from typing import Any, List, Optional, Tuple

import structlog
from pynetbox import api
from pynetbox.core.endpoint import Endpoint
from pynetbox.core.query import RequestError
from pynetbox.models.dcim import Interfaces
from pynetbox.models.dcim import Interfaces as PynetboxInterfaces
from pynetbox.models.ipam import IpAddresses, Prefixes

from utils.singledispatch import single_dispatch_base

logger = structlog.get_logger(__name__)

netbox = api(
    url=environ.get("NETBOX_URL", "http://netbox:8080"),
    token=environ.get("NETBOX_TOKEN", "e744057d755255a31818bf74df2350c26eeabe54"),
)

IPv4_LOOPBACK_PREFIX = "10.0.127.0/24"
IPv6_LOOPBACK_PREFIX = "fc00:0:0:127::/64"
IPv4_CORE_LINK_PREFIX = "10.0.10.0/24"
IPv6_CORE_LINK_PREFIX = "fc00:0:0:10::/64"


@dataclass
class NetboxPayload:
    # id: int  # unique id of object on Netbox endpoint

    # return payload as a dict that is suitable to be used on pynetbox .create() or .updates().
    def dict(self):
        return asdict(self)


@dataclass
class SitePayload(NetboxPayload):
    # mandatory fields to create a Sites object in Netbox
    name: str
    slug: str
    status: str


@dataclass
class DeviceRolePayload(NetboxPayload):
    # mandatory fields to create a DeviceRole object in Netbox
    name: str
    slug: str
    color: str  # RGB encoded string


@dataclass
class ManufacturerPayload(NetboxPayload):
    # mandatory fields to create a DeviceRole object in Netbox
    name: str
    slug: str


@dataclass
class DeviceTypePayload(NetboxPayload):
    # mandatory fields to create a DeviceRole object in Netbox
    manufacturer: ManufacturerPayload
    model: str
    slug: str
    u_height: float


@dataclass
class DevicePayload(NetboxPayload):
    # mandatory fields to create Devices object in Netbox:
    site: int
    device_type: int
    device_role: int
    # optional fields:
    name: Optional[str]
    status: Optional[str]
    primary_ip4: Optional[int] = None
    primary_ip6: Optional[int] = None


@dataclass
class CableTerminationPayload:
    object_id: int
    object_type: str = "dcim.interface"


@dataclass
class CablePayload(NetboxPayload):
    status: str
    type: str
    description: Optional[str]
    a_terminations: List[CableTerminationPayload]
    b_terminations: List[CableTerminationPayload]


@dataclass
class IpPrefixPayload(NetboxPayload):
    description: str
    prefix: str
    status: Optional[str] = "active"
    is_pool: Optional[bool] = True


@dataclass
class InterfacePayload(NetboxPayload):
    device: int
    name: str
    type: str
    description: str = ""
    enabled: bool = False
    speed: Optional[int] = None


@dataclass
class AvailablePrefixPayload:
    prefix_length: int
    description: str
    is_pool: Optional[bool] = False


@dataclass
class AvailableIpPayload:
    description: str
    assigned_object_id: int
    assigned_object_type: Optional[str] = "dcim.interface"
    status: Optional[str] = "active"


@dataclass
class VlanPayload(NetboxPayload):
    vid: int
    name: str
    status: Optional[str] = "active"


@dataclass
class L2vpnPayload(NetboxPayload):
    name: str
    slug: str
    type: Optional[str] = "mpls-evpn"


@dataclass
class L2vpnTerminationPayload(NetboxPayload):
    l2vpn: int
    assigned_object_id: int
    assigned_object_type: Optional[str] = "ipam.vlan"


def get_sites(**kwargs) -> List:
    return list(netbox.dcim.sites.filter(**kwargs))


def get_site(**kwargs):
    return netbox.dcim.sites.get(**kwargs)


def get_device_roles(**kwargs) -> List:
    return list(netbox.dcim.device_roles.filter(**kwargs))


def get_device_role(**kwargs):
    return netbox.dcim.device_roles.get(**kwargs)


def get_device_types(**kwargs) -> List:
    return list(netbox.dcim.device_types.filter(**kwargs))


def get_device_type(**kwargs):
    return netbox.dcim.device_types.get(**kwargs)


def get_devices(**kwargs) -> List:
    return netbox.dcim.devices.filter(**kwargs)


def get_device(**kwargs):
    return netbox.dcim.devices.get(**kwargs)


def get_interfaces(**kwargs) -> List:
    return netbox.dcim.interfaces.filter(**kwargs)


def get_interface(**kwargs):
    return netbox.dcim.interfaces.get(**kwargs)


def get_l2vpn(**kwargs):
    return netbox.ipam.l2vpns.get(**kwargs)


def get_vlan(**kwargs):
    return netbox.ipam.vlans.get(**kwargs)


def delete_from_netbox(endpoint, **kwargs) -> None:
    """Try to delete object with given kwargs from endpoint, raise an exception when object was not found."""
    if object := endpoint.get(**kwargs):
        object.delete()
    else:
        raise ValueError(f"object not found on {endpoint.name} endpoint")


def delete_device(**kwargs) -> None:
    delete_from_netbox(netbox.dcim.devices, **kwargs)


def delete_interface(**kwargs) -> None:
    delete_from_netbox(netbox.dcim.interfaces, **kwargs)


def delete_cable(**kwargs) -> None:
    delete_from_netbox(netbox.dcim.cables, **kwargs)


def delete_prefix(**kwargs) -> None:
    delete_from_netbox(netbox.ipam.prefixes, **kwargs)


def delete_ip_address(**kwargs) -> None:
    delete_from_netbox(netbox.ipam.ip_addresses, **kwargs)


def delete_l2vpn(**kwargs) -> None:
    delete_from_netbox(netbox.ipam.l2vpns, **kwargs)


def delete_vlan(**kwargs) -> None:
    delete_from_netbox(netbox.ipam.vlans, **kwargs)


def get_prefixes(**kwargs) -> List:
    return netbox.ipam.prefixes.filter(**kwargs)


def get_prefix(**kwargs):
    return netbox.ipam.prefixes.get(**kwargs)


def get_ip_address(**kwargs):
    return netbox.ipam.ip_addresses.get(**kwargs)


def get_ip_addresses(**kwargs):
    return netbox.ipam.ip_addresses.filter(**kwargs)


def reserve_loopback_addresses(device_id: int) -> Tuple:
    """Reserve IP IPv4/IPv6 loopback addresses, assign to Loopback0, and return address id."""
    device = get_device(id=device_id)
    interface_id = create(InterfacePayload(device=device_id, name="Loopback0", type="virtual", enabled=True))
    return tuple(
        get_prefix(prefix=prefix)
        .available_ips.create(
            asdict(
                AvailableIpPayload(
                    description=f"{ip_version} loopback {device.name}",
                    assigned_object_id=interface_id,
                )
            )
        )
        .id
        for ip_version, prefix in (("IPv4", IPv4_LOOPBACK_PREFIX), ("IPv6", IPv6_LOOPBACK_PREFIX))
    )


# def get_devices(status: Optional[str] = None) -> List[Devices]:
#     """
#     Get list of Devices objects from netbox, optionally filtered by status.
#     """
#     logger.debug("Connecting to Netbox to get list of devices")
#     if status:
#         node_list = list(netbox.dcim.devices.filter(status=status))
#     else:
#         node_list = list(netbox.dcim.devices.all())
#     logger.debug("Found nodes in Netbox", amount=len(node_list))
#     return node_list


# TODO: make this a more generic function
def get_available_router_ports_by_name(router_name: str) -> List[PynetboxInterfaces]:
    """
    get_available_router_ports_by_name fetches a list of available ports from netbox
        when given the name of a router. To be considered available, the port must be:
            1) A 400G interface (any media type)
            2) On the router specified.
            3) Not "occupied" from netbox's perspective.

    Args:
        router_name (str): the router that you need to find an open port from, i.e. "loc1-core".

    Returns:
        List[PynetboxInterfaces]: a list of valid interfaces from netbox.
    """
    valid_ports = list(netbox.dcim.interfaces.filter(device=router_name, occupied=False, speed=400000000))
    logger.debug("Found ports in Netbox", amount=len(valid_ports))
    return valid_ports


def get_interface_by_device_and_name(device: str, name: str) -> Interfaces:
    """
    Get Interfaces object from Netbox identified by device and name.
    """
    return next(netbox.dcim.interfaces.filter(device=device, name=name))


# def get_ip_address(address: str) -> IpAddresses:
#     """
#     Get IpAddresses object from Netbox identified by address.
#     """
#     return netbox.ipam.ip_addresses.get(address=address)


def get_ip_prefix_by_id(id: int) -> Prefixes:
    """
    Get Prefixes object from Netbox identified by id.
    """
    return netbox.ipam.prefixes.get(id)


def create_available_prefix(parent_id: int, payload: AvailablePrefixPayload) -> Prefixes:
    parent_prefix = get_ip_prefix_by_id(parent_id)
    return parent_prefix.available_prefixes.create(asdict(payload))


def create_available_ip(parent_id: int, payload: AvailableIpPayload) -> IpAddresses:
    parent_prefix = get_ip_prefix_by_id(parent_id)
    return parent_prefix.available_ips.create(asdict(payload))


@singledispatch
def create(payload: NetboxPayload, **kwargs: Any) -> int:
    """Create object described by payload in Netbox (generic function).

    Specific implementations of this generic function will specify the payload types they work on.

    Args:
        payload: Netbox object specific payload.

    Returns:
        The id of the created object in Netbox, raises an exception otherwise.

    Raises:
        TypeError: in case a specific implementation could not be found. The payload it was called for will be
            part of the error message.

    """
    return single_dispatch_base(create, payload)


def _create_object(payload: NetboxPayload, endpoint: Endpoint) -> int:
    """
    Create an object in Netbox.

    Args:
        payload: values to create object
        endpoint: a Netbox Endpoint

    Returns:
         The id of the created object in Netbox, raises an exception otherwise.

    Raises:
        RequestError: the pynetbox exception that was raised.
    """
    try:
        object = endpoint.create(payload.dict())
    except RequestError as exc:
        logger.warning("Netbox create failed", payload=payload, exc=str(exc))
        raise ValueError(f"invalid NetboxPayload: {exc.message}") from exc
    else:
        return object.id


@create.register
def _(payload: DevicePayload, **kwargs: Any) -> int:
    return _create_object(payload, endpoint=netbox.dcim.devices)


@create.register
def _(payload: DeviceRolePayload, **kwargs: Any) -> int:
    return _create_object(payload, endpoint=netbox.dcim.device_roles)


@create.register
def _(payload: ManufacturerPayload, **kwargs: Any) -> int:
    return _create_object(payload, endpoint=netbox.dcim.manufacturers)


@create.register
def _(payload: DeviceTypePayload, **kwargs: Any) -> int:
    return _create_object(payload, endpoint=netbox.dcim.device_types)


@create.register
def _(payload: CablePayload, **kwargs: Any) -> int:
    return _create_object(payload, endpoint=netbox.dcim.cables)


@create.register
def _(payload: IpPrefixPayload, **kwargs: Any) -> int:
    return _create_object(payload, endpoint=netbox.ipam.prefixes)


@create.register
def _(payload: InterfacePayload, **kwargs: Any) -> int:
    return _create_object(payload, endpoint=netbox.dcim.interfaces)


@create.register
def _(payload: SitePayload, **kwargs: Any) -> int:
    return _create_object(payload, endpoint=netbox.dcim.sites)


@create.register
def _(payload: VlanPayload, **kwargs: Any) -> int:
    return _create_object(payload, endpoint=netbox.ipam.vlans)


@create.register
def _(payload: L2vpnPayload, **kwargs: Any) -> int:
    return _create_object(payload, endpoint=netbox.ipam.l2vpns)


@create.register
def _(payload: L2vpnTerminationPayload, **kwargs: Any) -> int:
    return _create_object(payload, endpoint=netbox.ipam.l2vpn_terminations)


@singledispatch
def update(payload: NetboxPayload, **kwargs: Any) -> bool:
    """Update object described by payload in Netbox (generic function).

    Specific implementations of this generic function will specify the payload types they work on.

    Args:
        payload: Netbox object specific payload.
        id: ID of object to be updated

    Returns:
        True if the object was updated successfully in Netbox, False otherwise.

    Raises:
        TypeError: in case a specific implementation could not be found. The payload it was called for will be
            part of the error message.

    """
    return single_dispatch_base(update, payload)


def _update_object(payload: NetboxPayload, id: int, endpoint: Endpoint) -> bool:
    """
    Create or update an object in Netbox.

    Args:
        payload: values to create or update object
        endpoint: a Netbox Endpoint

    Returns:
         True if the node was created or updated, False otherwise

    Raises:
        ValueError if object does not exist yet in Netbox.
    """
    if not (object := endpoint.get(id)):
        raise ValueError(f"Netbox object with id {id} on netbox {endpoint.name} endpoint not found")
    object.update(payload.dict())
    return object.save()


@update.register
def _(payload: DevicePayload, id: int, **kwargs: Any) -> bool:
    return _update_object(payload, id, endpoint=netbox.dcim.devices)


@update.register
def _(payload: CablePayload, id: int, **kwargs: Any) -> bool:
    return _update_object(payload, id, endpoint=netbox.dcim.cables)


@update.register
def _(payload: DeviceTypePayload, id: int, **kwargs: Any) -> bool:
    return _update_object(payload, id, endpoint=netbox.dcim.device_types)


@update.register
def _(payload: InterfacePayload, id: int, **kwargs: Any) -> bool:
    return _update_object(payload, id, endpoint=netbox.dcim.interfaces)
