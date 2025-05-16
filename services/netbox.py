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


from dataclasses import asdict, dataclass, field
from functools import singledispatch
from ipaddress import IPv4Interface, IPv6Interface
from typing import Any, List, Tuple

import structlog
from pynetbox import api as pynetbox_api
from pynetbox.core.endpoint import Endpoint
from pynetbox.core.query import RequestError
from pynetbox.models.ipam import IpAddresses, Prefixes

from settings import settings
from utils.singledispatch import single_dispatch_base

logger = structlog.get_logger(__name__)

api = pynetbox_api(url=settings.NETBOX_URL, token=settings.NETBOX_TOKEN)


@dataclass
class NetboxPayload:
    def dict(self):
        # return payload as a dict that is suitable to be used on pynetbox .create() or .updates().
        return asdict(self)


@dataclass
class SitePayload(NetboxPayload):
    name: str
    slug: str
    status: str


@dataclass
class DeviceRolePayload(NetboxPayload):
    name: str
    slug: str
    color: str  # RGB encoded string


@dataclass
class ManufacturerPayload(NetboxPayload):
    name: str
    slug: str


@dataclass
class DeviceTypePayload(NetboxPayload):
    manufacturer: ManufacturerPayload
    model: str
    slug: str
    u_height: float


@dataclass
class DevicePayload(NetboxPayload):
    site: int
    device_type: int
    role: int
    name: str | None
    status: str | None
    primary_ip4: int | None = None
    primary_ip6: int | None = None


@dataclass
class CableTerminationPayload:
    object_id: int
    object_type: str = "dcim.interface"


@dataclass
class CablePayload(NetboxPayload):
    status: str
    type: str
    description: str | None
    a_terminations: List[CableTerminationPayload]
    b_terminations: List[CableTerminationPayload]


@dataclass
class IpPrefixPayload(NetboxPayload):
    description: str
    prefix: str
    status: str | None = "active"
    is_pool: bool | None = True


@dataclass
class InterfacePayload(NetboxPayload):
    device: int
    name: str
    type: str
    tagged_vlans: List[int] = field(default_factory=lambda: [])
    mode: str = ""
    description: str = ""
    enabled: bool = False
    speed: int | None = None


@dataclass
class AvailablePrefixPayload:
    prefix_length: int
    description: str
    is_pool: bool | None = False


@dataclass
class AvailableIpPayload:
    description: str
    assigned_object_id: int
    assigned_object_type: str | None = "dcim.interface"
    status: str | None = "active"


@dataclass
class VlanPayload(NetboxPayload):
    vid: int
    name: str
    status: str | None = "active"


@dataclass
class L2vpnPayload(NetboxPayload):
    name: str
    slug: str
    type: str | None = "mpls-evpn"


@dataclass
class L2vpnTerminationPayload(NetboxPayload):
    l2vpn: int
    assigned_object_id: int
    assigned_object_type: str | None = "ipam.vlan"


def get_sites(**kwargs) -> List:
    return list(api.dcim.sites.filter(**kwargs))


def get_site(**kwargs):
    return api.dcim.sites.get(**kwargs)


def get_device_roles(**kwargs) -> List:
    return list(api.dcim.device_roles.filter(**kwargs))


def get_device_role(**kwargs):
    return api.dcim.device_roles.get(**kwargs)


def get_device_types(**kwargs) -> List:
    return list(api.dcim.device_types.filter(**kwargs))


def get_device_type(**kwargs):
    return api.dcim.device_types.get(**kwargs)


def get_devices(**kwargs) -> List:
    return api.dcim.devices.filter(**kwargs)


def get_device(**kwargs):
    return api.dcim.devices.get(**kwargs)


def get_interfaces(**kwargs) -> List:
    return api.dcim.interfaces.filter(**kwargs)


def get_interface(**kwargs):
    return api.dcim.interfaces.get(**kwargs)


def get_cables(**kwargs) -> List:
    return api.dcim.cables.filter(**kwargs)


def get_cable(**kwargs):
    return api.dcim.cables.get(**kwargs)


def get_l2vpns(**kwargs):
    return api.vpn.l2vpns.filter(**kwargs)


def get_l2vpn(**kwargs):
    return api.vpn.l2vpns.get(**kwargs)


def get_l2vpn_terminations(**kwargs):
    return api.vpn.l2vpn_terminations.filter(**kwargs)


def get_l2vpn_termination(**kwargs):
    return api.vpn.l2vpn_terminations.get(**kwargs)


def get_vlans(**kwargs):
    return api.ipam.vlans.filter(**kwargs)


def get_vlan(**kwargs):
    return api.ipam.vlans.get(**kwargs)


def get_ip_prefixes(**kwargs) -> List:
    return api.ipam.prefixes.filter(**kwargs)


def get_ip_prefix(**kwargs):
    return api.ipam.prefixes.get(**kwargs)


def get_ip_addresses(**kwargs):
    return api.ipam.ip_addresses.filter(**kwargs)


def get_ip_address(**kwargs):
    return api.ipam.ip_addresses.get(**kwargs)


def delete_from_netbox(endpoint, **kwargs) -> None:
    """Try to delete object with given kwargs from endpoint, raise an exception when object was not found."""
    if object := endpoint.get(**kwargs):
        object.delete()
    else:
        raise ValueError(f"object not found on {endpoint.name} endpoint")


def delete_device(**kwargs) -> None:
    delete_from_netbox(api.dcim.devices, **kwargs)


def delete_interface(**kwargs) -> None:
    delete_from_netbox(api.dcim.interfaces, **kwargs)


def delete_cable(**kwargs) -> None:
    delete_from_netbox(api.dcim.cables, **kwargs)


def delete_prefix(**kwargs) -> None:
    delete_from_netbox(api.ipam.prefixes, **kwargs)


def delete_ip_address(**kwargs) -> None:
    delete_from_netbox(api.ipam.ip_addresses, **kwargs)


def delete_l2vpn(**kwargs) -> None:
    delete_from_netbox(api.vpn.l2vpns, **kwargs)


def delete_vlan(**kwargs) -> None:
    delete_from_netbox(api.ipam.vlans, **kwargs)


def skip_network_address(ip_prefix: Prefixes) -> None:
    """Assign placeholders for network address(es) in available IPS of the prefix.

    Helper function for reserve_loopback_addresses().
    Ensures that the first available ip from the prefix is not a network address.
    """

    def is_network_address(address: IpAddresses) -> bool:
        addr = IPv4Interface(address) if address.family == 4 else IPv6Interface(address)
        return addr.ip == addr.network.network_address

    while True:
        if not (address := next(iter(ip_prefix.available_ips.list()), None)):
            raise ValueError(f"Prefix {ip_prefix} has no available addresses")

        if not is_network_address(address):
            return

        ip_prefix.available_ips.create({"description": "placeholder"})


def reserve_loopback_addresses(device_id: int) -> Tuple:
    """Reserve IP IPv4/IPv6 loopback addresses, assign to Loopback0, and return address id."""
    device = get_device(id=device_id)
    interface_id = create(InterfacePayload(device=device_id, name="Loopback0", type="virtual", enabled=True))

    def reserve_loopback_address(ip_version: str, prefix: str) -> int:
        ip_prefix = get_ip_prefix(prefix=prefix)
        # The netbox v3 API incorrectly allowed assigning the network address to an interface.
        #
        # The netbox v4 API now rejects this. But that raises the question of how to skip the non-network
        # address(es). There might be a better way, but for now we assign placeholders for the network address(es).
        skip_network_address(ip_prefix)
        address = ip_prefix.available_ips.create(
            asdict(
                AvailableIpPayload(description=f"{ip_version} loopback {device.name}", assigned_object_id=interface_id)
            )
        )
        return address.id

    return tuple(
        reserve_loopback_address(ip_version, prefix)
        for ip_version, prefix in (("IPv4", settings.IPv4_LOOPBACK_PREFIX), ("IPv6", settings.IPv6_LOOPBACK_PREFIX))
    )


def create_available_prefix(parent_id: int, payload: AvailablePrefixPayload) -> Prefixes:
    parent_prefix = get_ip_prefix(id=parent_id)
    return parent_prefix.available_prefixes.create(asdict(payload))


def create_available_ip(parent_id: int, payload: AvailableIpPayload) -> IpAddresses:
    parent_prefix = get_ip_prefix(id=parent_id)
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
    return _create_object(payload, endpoint=api.dcim.devices)


@create.register
def _(payload: DeviceRolePayload, **kwargs: Any) -> int:
    return _create_object(payload, endpoint=api.dcim.device_roles)


@create.register
def _(payload: ManufacturerPayload, **kwargs: Any) -> int:
    return _create_object(payload, endpoint=api.dcim.manufacturers)


@create.register
def _(payload: DeviceTypePayload, **kwargs: Any) -> int:
    return _create_object(payload, endpoint=api.dcim.device_types)


@create.register
def _(payload: CablePayload, **kwargs: Any) -> int:
    return _create_object(payload, endpoint=api.dcim.cables)


@create.register
def _(payload: IpPrefixPayload, **kwargs: Any) -> int:
    return _create_object(payload, endpoint=api.ipam.prefixes)


@create.register
def _(payload: InterfacePayload, **kwargs: Any) -> int:
    return _create_object(payload, endpoint=api.dcim.interfaces)


@create.register
def _(payload: SitePayload, **kwargs: Any) -> int:
    return _create_object(payload, endpoint=api.dcim.sites)


@create.register
def _(payload: VlanPayload, **kwargs: Any) -> int:
    return _create_object(payload, endpoint=api.ipam.vlans)


@create.register
def _(payload: L2vpnPayload, **kwargs: Any) -> int:
    return _create_object(payload, endpoint=api.vpn.l2vpns)


@create.register
def _(payload: L2vpnTerminationPayload, **kwargs: Any) -> int:
    return _create_object(payload, endpoint=api.vpn.l2vpn_terminations)


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
    return _update_object(payload, id, endpoint=api.dcim.devices)


@update.register
def _(payload: CablePayload, id: int, **kwargs: Any) -> bool:
    return _update_object(payload, id, endpoint=api.dcim.cables)


@update.register
def _(payload: DeviceTypePayload, id: int, **kwargs: Any) -> bool:
    return _update_object(payload, id, endpoint=api.dcim.device_types)


@update.register
def _(payload: InterfacePayload, id: int, **kwargs: Any) -> bool:
    return _update_object(payload, id, endpoint=api.dcim.interfaces)
