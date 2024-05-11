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
from orchestrator import workflow
from orchestrator.targets import Target
from orchestrator.types import State
from orchestrator.workflow import StepList, done, init, step

from services import netbox
from settings import settings

logger = structlog.get_logger(__name__)

initial_objects = [
    netbox.SitePayload(name="Amsterdam", slug="amsterdam", status="active"),
    netbox.SitePayload(name="Paris", slug="paris", status="active"),
    netbox.SitePayload(name="London", slug="london", status="active"),
    netbox.SitePayload(name="Madrid", slug="madrid", status="active"),
    netbox.SitePayload(name="Rome", slug="rome", status="active"),
    netbox.DeviceRolePayload(name="Provider", slug="provider", color="9e9e9e"),
    netbox.DeviceRolePayload(name="Provider Edge", slug="provider-edge", color="ff9800"),
    cisco := netbox.ManufacturerPayload(name="Cisco", slug="cisco"),
    nokia := netbox.ManufacturerPayload(name="Nokia", slug="nokia"),
    cumulus := netbox.ManufacturerPayload(name="Cumulus", slug="cumulus"),
    frr := netbox.ManufacturerPayload(name="FRR", slug="frr"),
    netbox.DeviceTypePayload(manufacturer=cisco, model="8812", slug="8812", u_height=21.0),
    netbox.DeviceTypePayload(manufacturer=cisco, model="ASR 903", slug="asr-903", u_height=3.0),
    netbox.DeviceTypePayload(manufacturer=nokia, model="7950 XRS-20", slug="7950-xrs-20", u_height=44.0),
    netbox.DeviceTypePayload(manufacturer=nokia, model="7210 SAS-R6", slug="7210-sas-r6", u_height=3.0),
    netbox.DeviceTypePayload(manufacturer=nokia, model="7220 IXR-D2", slug="7220-ixr-d2", u_height=1.0),
    netbox.DeviceTypePayload(manufacturer=nokia, model="7220 IXR-D3", slug="7220-ixr-d3", u_height=1.0),
    netbox.DeviceTypePayload(manufacturer=cumulus, model="cVX VM", slug="cvx", u_height=1.0),
    netbox.DeviceTypePayload(manufacturer=frr, model="FRR VM", slug="frr", u_height=1.0),
]


@step("Create initial set of objects")
def create_initial_set_of_objects() -> State:
    objects_created = []
    for initial_object in initial_objects:
        logger.info("add object to Netbox", object=initial_object)
        try:
            netbox.create(initial_object)
            objects_created.append(initial_object.dict())
        except ValueError:
            # pynetbox already emits a log message
            pass

    return {"objects_created": objects_created}


@step("Create prefixes")
def create_prefixes() -> State:
    prefixes_created = []
    for prefix, description in (
        (settings.IPv4_LOOPBACK_PREFIX, "IPv4 loopback prefix"),
        (settings.IPv6_LOOPBACK_PREFIX, "IPv6 loopback prefix"),
        (settings.IPv4_CORE_LINK_PREFIX, "IPv4 core link prefix"),
        (settings.IPv6_CORE_LINK_PREFIX, "IPv6 core link prefix"),
    ):
        if netbox.api.ipam.prefixes.get(prefix=prefix):
            logger.warning("prefix already exists", prefix=prefix)
        else:
            logger.info("add prefix to netbox", prefix=prefix)
            prefix_payload = netbox.IpPrefixPayload(prefix=prefix, description=description).dict()
            netbox.api.ipam.prefixes.create(prefix_payload)
            prefixes_created.append(prefix_payload)

    return {"prefixes_created": prefixes_created}


@workflow("Bootstrap Netbox", target=Target.SYSTEM)
def task_bootstrap_netbox() -> StepList:
    return init >> create_initial_set_of_objects >> create_prefixes >> done
