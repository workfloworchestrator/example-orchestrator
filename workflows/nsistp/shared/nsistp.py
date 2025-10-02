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
from collections.abc import Sequence
from uuid import UUID

from more_itertools import flatten
from nwastdlib.vlans import VlanRanges
from orchestrator.db import db
from orchestrator.db.models import (
    ProductTable,
    SubscriptionInstanceRelationTable,
    SubscriptionInstanceTable,
    SubscriptionTable,
)
from orchestrator.types import SubscriptionLifecycle
from sqlalchemy import select
from sqlalchemy.orm import aliased

# from surf.products.product_types.nsi_lp import NsiLightPath
from products.product_types.nsistp import Nsistp


def _get_subscriptions_inuseby_port_id(
    port_id: UUID, product_type: str, statuses: list[SubscriptionLifecycle]
) -> Sequence[UUID]:
    relations = aliased(SubscriptionInstanceRelationTable)
    instances = aliased(SubscriptionInstanceTable)
    query = (
        select(SubscriptionTable.subscription_id)
        .join(SubscriptionInstanceTable)
        .join(ProductTable)
        .join(
            relations,
            relations.in_use_by_id
            == SubscriptionInstanceTable.subscription_instance_id,
        )
        .join(instances, relations.depends_on_id == instances.subscription_instance_id)
        .filter(instances.subscription_id == port_id)
        .filter(ProductTable.product_type == product_type)
        .filter(SubscriptionTable.status.in_(statuses))
    )
    return db.session.scalars(query).all()


def nsistp_get_by_port_id(port_id: UUID) -> list[Nsistp]:
    """Get Nsistps by service port id.

    Args:
        port_id: ID of the service port for which you want all nsistps of.
    """
    statuses = [
        SubscriptionLifecycle.ACTIVE,
        SubscriptionLifecycle.PROVISIONING,
        SubscriptionLifecycle.MIGRATING,
    ]
    result = _get_subscriptions_inuseby_port_id(port_id, "NSISTP", statuses)

    return [Nsistp.from_subscription(id) for id in list(set(result))]


# def nsi_lp_get_by_port_id(port_id: UUID) -> list[NsiLightPath]:
#     """Get NsiLightPaths by service port id.

#     Args:
#         port_id: ID of the service port for which you want all NsiLightPaths of.
#     """
#     statuses = [SubscriptionLifecycle.ACTIVE]
#     result = _get_subscriptions_inuseby_port_id(port_id, "NSILP", statuses)

#     return [NsiLightPath.from_subscription(id) for id in list(set(result))]


def get_available_vlans_by_port_id(port_id: UUID) -> VlanRanges:
    """Get available vlans by service port id.

    This will get all NSISTPs and adds their vlan ranges to a single VlanRanges to get the available vlans by nsistps.

    Then filters out the vlans that are already in use by NSI light paths and returns the available vlans.

    Args:
        port_id: ID of the service port to find available vlans.
    """
    nsistps = nsistp_get_by_port_id(port_id)
    available_vlans = VlanRanges(flatten(nsistp.vlan_range for nsistp in nsistps))

    # NOTE: Lightpad can be ommited?
    # nsi_lps = nsi_lp_get_by_port_id(port_id)
    # used_vlans = VlanRanges(
    #     flatten(sap.vlanrange for nsi_lp in nsi_lps for sap in nsi_lp.vc.saps)
    # )

    # return available_vlans - used_vlans

    return available_vlans
