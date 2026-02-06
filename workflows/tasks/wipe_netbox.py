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
from typing import Annotated

import structlog
from orchestrator import workflow
from orchestrator.targets import Target
from orchestrator.workflow import StepList, done, init, step
from pydantic import AfterValidator, ConfigDict

from pydantic_forms.core import FormPage
from pydantic_forms.types import FormGenerator, State
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
    netbox.api.vpn.l2vpns,
    netbox.api.vpn.l2vpn_terminations,
]


def must_be_true(annihilate: bool) -> bool:
    if not annihilate:
        raise ValueError("Will not continue unless you check this box")
    return annihilate


Annihilate = Annotated[bool, AfterValidator(must_be_true)]


def initial_input_form_generator() -> FormGenerator:
    class AreYouSure(FormPage):
        model_config = ConfigDict(title="Wipe Netbox")

        annihilate: Annihilate = False

    yield AreYouSure

    return {}


@step("Wipe all objects")
def wipe_all_objects() -> State:
    objects_deleted = []
    for endpoint in endpoints:
        for object in endpoint.all():
            object.delete()
            logger.info("delete object from Netbox", object=object, endpoint=object.endpoint.name)
            objects_deleted.append({"object": str(object), "endpoint": object.endpoint.name})

    return {"objects_deleted": objects_deleted}


@workflow("Wipe Netbox", initial_input_form=initial_input_form_generator, target=Target.SYSTEM)
def task_wipe_netbox() -> StepList:
    return init >> wipe_all_objects >> done
