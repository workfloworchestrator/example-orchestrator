import structlog

from services.netbox import netbox

logger = structlog.get_logger(__name__)


endpoints = [
    netbox.dcim.devices,
    netbox.dcim.device_types,
    netbox.dcim.manufacturers,
    netbox.dcim.device_roles,
    netbox.dcim.sites,
]


if __name__ == "__main__":
    for endpoint in endpoints:
        for object in endpoint.all():
            object.delete()
            logger.info("delete object from Netbox", object=object, endpoint=object.endpoint.name)
