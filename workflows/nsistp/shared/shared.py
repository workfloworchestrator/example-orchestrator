# Copyright 2019-2024 SURF.
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
from collections.abc import Callable
from enum import StrEnum
from uuid import UUID

import structlog
from nwastdlib.vlans import VlanRanges
from orchestrator.db import (
    SubscriptionTable,
)
from pydantic import GetJsonSchemaHandler
from pydantic.json_schema import JsonSchemaValue
from pydantic_core import CoreSchema

from utils.types import Tags

logger = structlog.get_logger(__name__)

GetSubscriptionByIdFunc = Callable[[UUID], SubscriptionTable]

PORT_SPEED = "port_speed"
MAX_SPEED_POSSIBLE = 400_000


class PortTag(StrEnum):
    SP = "SP"
    SPNL = "SPNL"
    AGGSP = "AGGSP"
    AGGSPNL = "AGGSPNL"
    MSC = "MSC"
    MSCNL = "MSCNL"
    IRBSP = "IRBSP"


PORT_TAG_GENERAL: list[Tags] = ["PORT"]

# TODO: these tags can probably be removed
PORT_TAGS_AGGSP: list[Tags] = ["AGGSP", "AGGSPNL"]
PORT_TAGS_IRBSP: list[Tags] = ["IRBSP"]
PORT_TAGS_MSC: list[Tags] = ["MSC", "MSCNL"]
PORT_TAGS_SP: list[Tags] = ["SP"]
PORT_TAGS_ALL: list[Tags] = (
    PORT_TAGS_SP + PORT_TAGS_AGGSP + PORT_TAGS_MSC + PORT_TAGS_IRBSP + PORT_TAG_GENERAL
)


# Custom VlanRanges needed to avoid matching conflict with SURF orchestrator-ui components
class CustomVlanRanges(VlanRanges):
    def __str__(self) -> str:
        # `range` objects have an exclusive `stop`. VlanRanges is expressed using terms that use an inclusive stop,
        # which is one less then the exclusive one we use for the internal representation. Hence the `-1`
        return ", ".join(
            str(vr.start) if len(vr) == 1 else f"{vr.start}-{vr.stop - 1}"
            for vr in self._vlan_ranges
        )

    @classmethod
    def __get_pydantic_json_schema__(
        cls, core_schema_: CoreSchema, handler: GetJsonSchemaHandler
    ) -> JsonSchemaValue:
        parent_schema = super().__get_pydantic_json_schema__(core_schema_, handler)
        parent_schema["format"] = "custom-vlan"

        return parent_schema
