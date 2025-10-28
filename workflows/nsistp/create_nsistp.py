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


from functools import partial
import uuid
from typing import Annotated, TypeAlias, cast

import structlog
from orchestrator.forms import FormPage
from orchestrator.forms.validators import Divider, Label
from orchestrator.targets import Target
from orchestrator.types import SubscriptionLifecycle
from orchestrator.workflow import StepList, begin, step
from orchestrator.workflows.steps import store_process_subscription
from orchestrator.workflows.utils import create_workflow
from pydantic import AfterValidator, ConfigDict, model_validator
from pydantic_forms.types import FormGenerator, State, UUIDstr
from pydantic_forms.validators import Choice

from products.product_types.nsistp import NsistpInactive, NsistpProvisioning
from products.services.description import description
from products.services.netbox.payload.sap import build_sap_vlan_group_payload
from services import netbox
from workflows.nsistp.shared.forms import (
    IsAlias,
    ServiceSpeed,
    StpDescription,
    StpId,
    Topology,
    nsistp_fill_sap,
    port_selector,
    validate_both_aliases_empty_or_not,
)
from workflows.nsistp.shared.shared import OrchestratorVlanRanges
from workflows.nsistp.shared.vlan import validate_vlan, validate_vlan_not_in_use
from workflows.shared import create_summary_form

logger = structlog.get_logger(__name__)


def initial_input_form_generator(product_name: str) -> FormGenerator:
    PortChoiceList: TypeAlias = cast(type[Choice], port_selector())

    _validate_vlan_not_in_use = partial(validate_vlan_not_in_use, port_field_name="port")
    class CreateNsiStpForm(FormPage):
        model_config = ConfigDict(title=product_name)

        nsistp_settings: Label
    
        port: PortChoiceList
        vlan: Annotated[
            OrchestratorVlanRanges,
            AfterValidator(validate_vlan),
            AfterValidator(_validate_vlan_not_in_use),
        ]

        divider_1: Divider

        topology: Topology
        stp_id: StpId
        stp_description: StpDescription | None = None
        is_alias_in: IsAlias | None = None
        is_alias_out: IsAlias | None = None
        expose_in_topology: bool = True
        bandwidth: ServiceSpeed

        @model_validator(mode="after")
        def validate_is_alias_in_out(self) -> "CreateNsiStpForm":
            validate_both_aliases_empty_or_not(self.is_alias_in, self.is_alias_out)
            return self

    user_input = yield CreateNsiStpForm
    user_input_dict = user_input.dict()

    summary_fields = [
        "port",
        "vlan",
        "topology",
        "stp_id",
        "stp_description",
        "is_alias_in",
        "is_alias_out",
        "expose_in_topology",
        "bandwidth",
    ]
    yield from create_summary_form(user_input_dict, product_name, summary_fields)

    return user_input_dict


@step("Construct Subscription model")
def construct_nsistp_model(
    product: UUIDstr,
    port: UUIDstr,
    vlan: OrchestratorVlanRanges,
    topology: str,
    stp_id: str,
    stp_description: str | None,
    is_alias_in: str | None,
    is_alias_out: str | None,
    expose_in_topology: bool | None,
    bandwidth: int | None,
) -> State:
    nsistp = NsistpInactive.from_product_id(
        product_id=product,
        customer_id=str(uuid.uuid4()),
        status=SubscriptionLifecycle.INITIAL,
    )
    nsistp.nsistp.topology = topology
    nsistp.nsistp.stp_id = stp_id
    nsistp.nsistp.stp_description = stp_description
    nsistp.nsistp.is_alias_in = is_alias_in
    nsistp.nsistp.is_alias_out = is_alias_out
    nsistp.nsistp.expose_in_topology = expose_in_topology
    nsistp.nsistp.bandwidth = bandwidth

    nsistp_fill_sap(nsistp, port, vlan)

    nsistp = NsistpProvisioning.from_other_lifecycle(nsistp, SubscriptionLifecycle.PROVISIONING)
    nsistp.description = description(nsistp)

    return {
        "subscription": nsistp,
        "subscription_id": nsistp.subscription_id,  # necessary to be able to use older generic step functions
        "subscription_description": nsistp.description,
    }


@step("Create VLANs in IMS (Netbox)")
def ims_create_vlans(subscription: NsistpProvisioning) -> State:
    group_payload = build_sap_vlan_group_payload(subscription.nsistp.sap, subscription)
    subscription.nsistp.sap.ims_id = netbox.create(group_payload)

    return {"subscription": subscription, "payload": group_payload}


@create_workflow("Create nsistp", initial_input_form=initial_input_form_generator)
def create_nsistp() -> StepList:
    return begin >> construct_nsistp_model >> store_process_subscription(Target.CREATE) >> ims_create_vlans
