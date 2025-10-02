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

from forms.types import Tags

PORT_TAG_GENERAL: list[Tags] = ["PORT"]

# TODO: these tags can probably be removed
PORT_TAGS_AGGSP: list[Tags] = ["AGGSP", "AGGSPNL"]
PORT_TAGS_IRBSP: list[Tags] = ["IRBSP"]
PORT_TAGS_MSC: list[Tags] = ["MSC", "MSCNL"]
PORT_TAGS_SPNL: list[Tags] = ["SPNL"]
PORT_TAGS_SP: list[Tags] = ["SP"]
PORT_TAGS_SP_ALL: list[Tags] = PORT_TAGS_SPNL + PORT_TAGS_SP
PORT_TAGS_ALL: list[Tags] = (
    PORT_TAGS_SP_ALL
    + PORT_TAGS_AGGSP
    + PORT_TAGS_MSC
    + PORT_TAGS_IRBSP
    + PORT_TAG_GENERAL
)
SERVICES_TAGS_FOR_IMS_REDEPLOY: list[Tags] = [
    "IPBGP",
    "IPS",
    "L2VPN",
    "L3VPN",
    "LP",
    "LR",
    "NSILP",
]
TAGS_FOR_IMS_REDEPLOY: list[Tags] = SERVICES_TAGS_FOR_IMS_REDEPLOY + PORT_TAGS_ALL
