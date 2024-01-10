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
from orchestrator.forms import FormPage
from orchestrator.targets import Target
from orchestrator.types import FormGenerator, State
from orchestrator.workflow import StepList, done, init, step
from pydantic import ConfigDict, validator

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


def initial_input_form_generator() -> FormGenerator:
    class AreYouSure(FormPage):
        model_config = ConfigDict(title="Wipe Netbox")

        annihilate: bool | None

        # TODO[pydantic]: We couldn't refactor the `validator`, please replace it by `field_validator` manually.
        # Check https://docs.pydantic.dev/dev-v2/migration/#changes-to-validators for more information.
        @validator("annihilate", allow_reuse=True)
        def must_be_true(cls, v: str, values: dict, **kwargs):
            if not v:
                raise AssertionError("Will not continue unless you check this box")
            return v

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
