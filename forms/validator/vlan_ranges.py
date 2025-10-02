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
from typing import Annotated

from nwastdlib.vlans import VlanRanges
from pydantic import AfterValidator, Field, TypeAdapter

from utils.exceptions import VlanValueError


def validate_vlan_range(vlan_ranges: VlanRanges) -> VlanRanges:
    for vlan in vlan_ranges:
        if vlan == 0 or (2 <= vlan <= 4094):
            continue
        raise VlanValueError("VLAN range must be between 2 and 4094")
    return vlan_ranges


_vlan_ranges_schema = TypeAdapter(VlanRanges).json_schema()

NsiVlanRanges = Annotated[
    VlanRanges,
    Field(json_schema_extra=_vlan_ranges_schema | {"uniforms": {"nsiVlansOnly": True}}),
    AfterValidator(validate_vlan_range),
]
