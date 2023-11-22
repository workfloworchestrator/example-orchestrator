import structlog

from services import netbox

logger = structlog.get_logger(__name__)


endpoints = [
    netbox.api.dcim.devices,
    netbox.api.dcim.device_types,
    netbox.api.dcim.manufacturers,
    netbox.api.dcim.device_roles,
    netbox.api.dcim.sites,
    netbox.api.dcim.cables,
    netbox.api.ipam.prefixes,
    netbox.api.ipam.ip_addresses,
    netbox.api.ipam.vlans,
    netbox.api.ipam.l2vpns,
    netbox.api.ipam.l2vpn_terminations,
]


if __name__ == "__main__":
    for endpoint in endpoints:
        for object in endpoint.all():
            object.delete()
            logger.info("delete object from Netbox", object=object, endpoint=object.endpoint.name)
