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


from orchestrator.forms.validators import Choice

from products.product_blocks.shared.types import NodeStatus
from services import netbox


def site_selector() -> Choice:
    sites = {str(site.id): site.name for site in netbox.get_sites(status="active")}
    return Choice("SitesEnum", zip(sites.keys(), sites.items()))  # type:ignore


def node_role_selector() -> Choice:
    roles = {str(role.id): role.name for role in netbox.get_device_roles()}
    return Choice("RolesEnum", zip(roles.keys(), roles.items()))  # type:ignore


def node_type_selector(node_type: str) -> Choice:
    types = {
        str(type.id): " ".join((type.manufacturer.name, type.model))
        for type in netbox.get_device_types()
        if type.manufacturer.name == node_type
    }
    return Choice("TypesEnum", zip(types.keys(), types.items()))  # type:ignore


def node_status_selector() -> Choice:
    statuses = NodeStatus.list()
    return Choice("NodeStatusEnum", zip(statuses, statuses))  # type:ignore
