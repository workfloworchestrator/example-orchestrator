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
