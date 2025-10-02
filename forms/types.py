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

from ipaddress import IPv4Address, IPv4Network, IPv6Address, IPv6Network
from typing import Literal

Tags = Literal[
    "SP",
    "SPNL",
    "MSC",
    "MSCNL",
    "AGGSP",
    "LightPath",
    "LP",
    "LR",
    "NSILP",
    "IPS",
    "IPBGP",
    "AGGSPNL",
    "LRNL",
    "LIR_PREFIX",
    "SUB_PREFIX",
    "Node",
    "IRBSP",
    "FW",
    "Corelink",
    "L2VPN",
    "L3VPN",
    "LPNLNSI",
    "IPPG",
    "IPPP",
    "Wireless",
    "OS",
]

# IMSStatus = Literal["RFS", "PL", "IS", "MI", "RFC", "OOS"]
TransitionType = Literal["speed", "upgrade", "downgrade", "replace"]
VisiblePortMode = Literal["all", "normal", "tagged", "untagged", "link_member"]


# class MailAddress(TypedDict):
#     email: EmailStr
#     name: str


# class ConfirmationMail(TypedDict):
#     message: str
#     subject: str
#     language: str
#     to: list[MailAddress]
#     cc: list[MailAddress]
#     bcc: list[MailAddress]


IPAddress = IPv4Address | IPv6Address
IPNetwork = IPv4Network | IPv6Network
