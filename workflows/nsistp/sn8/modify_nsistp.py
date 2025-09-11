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
from functools import partial
from typing import Annotated, TypeAlias, cast
from uuid import UUID

from more_itertools import flatten
from more_itertools.more import one
from pydantic import AfterValidator, model_validator
from pydantic_forms.types import FormGenerator, State
from pydantic_forms.validators import ReadOnlyField

from nwastdlib.vlans import VlanRanges
from orchestrator.forms import FormPage
from orchestrator.forms.validators import Divider, Label, ListOfOne
from orchestrator.workflow import StepList, begin, step
from surf.forms.validator.bandwidth import ServiceSpeed
from surf.forms.validator.service_port import ServicePort
from surf.forms.validators import JiraTicketId
from surf.products.product_types.sn8_nsistp import Nsistp, NsistpProvisioning
from surf.products.services.nsistp import nsi_lp_get_by_port_id
from surf.utils.exceptions import PortsValueError
from surf.workflows.nsistp.sn8.shared.forms import (
    IsAlias,
    StpDescription,
    StpId,
    Topology,
    nsistp_fill_sap,
    nsistp_service_port,
    validate_both_aliases_empty_or_not,
    validate_stp_id_uniqueness,
)
from surf.workflows.shared.steps import update_subscription_description
from surf.workflows.shared.summary_form import base_summary
from surf.workflows.shared.validate_subscriptions import subscription_update
from surf.workflows.workflow import modify_workflow


def validate_service_port_vlan(
    current_sp_id: UUID, nsi_lp_vlanrange: VlanRanges, service_ports: list[ServicePort]
) -> list:
    return validate_sp_vlan_in_use_by_nsi_lp(service_ports, current_sp_id, nsi_lp_vlanrange)


def validate_sp_vlan_in_use_by_nsi_lp(
    service_ports: list[ServicePort], current_sp_id: UUID, nsi_lp_vlanrange: VlanRanges
) -> list:
    sp = one(service_ports)
    nsi_lp_vlanrange_not_used = nsi_lp_vlanrange - sp.vlan

    if nsi_lp_vlanrange_not_used:
        if current_sp_id != sp.subscription_id:
            raise PortsValueError(
                f"Can't change service port when VLAN's are in use by NSI light paths: ({current_sp_id}: {nsi_lp_vlanrange})"
            )
        raise PortsValueError(f"VLAN range must include VLAN's currently in use by NSI light paths: {nsi_lp_vlanrange}")
    return service_ports


def get_vlans_in_use_by_nsi_lp(nsistp: Nsistp) -> VlanRanges:
    nsi_lps = nsi_lp_get_by_port_id(nsistp.settings.sap.port_subscription_id)
    used_vlans = VlanRanges(flatten(sap.vlanrange for nsi_lp in nsi_lps for sap in nsi_lp.vc.saps))
    used_vlans_list = set(used_vlans)

    return VlanRanges([vlan for vlan in nsistp.vlan_range if vlan in used_vlans_list])


def initial_input_form_generator(subscription_id: UUID) -> FormGenerator:
    nsistp = Nsistp.from_subscription(subscription_id)
    settings = nsistp.settings
    sap = settings.sap

    port_subscription_id = sap.port.owner_subscription_id
    current_service_port = {"subscription_id": port_subscription_id, "vlan": str(sap.vlanrange)}
    nsi_lp_vlans = get_vlans_in_use_by_nsi_lp(nsistp)
    FormNsistpServicePort: TypeAlias = cast(type[ServicePort], nsistp_service_port(current=[current_service_port]))

    ModifyStpId = Annotated[StpId, AfterValidator(partial(validate_stp_id_uniqueness, subscription_id))]

    service_port_validator = AfterValidator(partial(validate_service_port_vlan, port_subscription_id, nsi_lp_vlans))
    ServicePorts = Annotated[ListOfOne[FormNsistpServicePort], service_port_validator]

    class ModifyNsiStpForm(FormPage):
        customer_id: ReadOnlyField(UUID(nsistp.customer_id))  # type: ignore
        ticket_id: JiraTicketId

        label_nsistp_settings: Label
        divider: Divider

        service_ports: ServicePorts = [current_service_port]

        topology: Topology = settings.topology

        stp_id: ModifyStpId = settings.stp_id
        stp_description: StpDescription | None = settings.stp_description

        is_alias_in: IsAlias | None = settings.is_alias_in
        is_alias_out: IsAlias | None = settings.is_alias_out

        expose_in_topology: bool = settings.expose_in_topology

        bandwidth_info: ServiceSpeed | None = settings.bandwidth

        @model_validator(mode="after")
        def validate_is_alias_in_out(self) -> "ModifyNsiStpForm":
            validate_both_aliases_empty_or_not(self.is_alias_in, self.is_alias_out)
            return self

    before_user_input_dict = ModifyNsiStpForm().model_dump()  # type: ignore
    user_input = yield ModifyNsiStpForm
    user_input_dict = user_input.model_dump()

    yield from base_summary(nsistp.product.name, user_input_dict, old_data=before_user_input_dict)

    return user_input_dict | {"subscription": nsistp}


@subscription_update
@step("Update subscription")
def update_subscription(
    subscription: NsistpProvisioning,
    service_ports: list[dict],
    topology: str,
    stp_id: str,
    stp_description: str,
    is_alias_in: str | None,
    is_alias_out: str | None,
    expose_in_topology: bool,
    bandwidth_info: int | None,
) -> State:
    nsistp_fill_sap(subscription, service_ports)

    settings = subscription.settings
    settings.topology = topology
    settings.stp_id = stp_id
    settings.stp_description = stp_description
    settings.is_alias_in = is_alias_in
    settings.is_alias_out = is_alias_out
    settings.expose_in_topology = expose_in_topology
    settings.bandwidth = bandwidth_info

    return {"subscription": subscription}


@modify_workflow("Modify NSISTP", initial_input_form=initial_input_form_generator)
def modify_nsistp() -> StepList:
    return begin >> update_subscription >> update_subscription_description
