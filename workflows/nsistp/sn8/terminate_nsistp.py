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
from typing import Annotated, TypeAlias
from uuid import UUID

from more_itertools import flatten
from pydantic import Field, model_validator
from pydantic_forms.types import InputForm, State

from nwastdlib.vlans import VlanRanges
from orchestrator.forms import FormPage
from orchestrator.forms.validators import DisplaySubscription
from orchestrator.workflow import StepList, begin, step
from surf.forms.validators import JiraTicketId
from surf.products.product_types.nsi_lp import NsiLightPath
from surf.products.product_types.sn8_nsistp import Nsistp
from surf.products.services.nsistp import nsi_lp_get_by_port_id
from surf.workflows.workflow import terminate_workflow


@step("Load initial state")
def load_initial_state(subscription: Nsistp) -> State:
    return {"subscription": subscription}


def get_in_use_by_nsi_lp(nsistp: Nsistp) -> list[NsiLightPath]:
    nsi_lps_by_port = nsi_lp_get_by_port_id(nsistp.settings.sap.port_subscription_id)

    def check_in_use_by_nsi_lp(nsi_lp: NsiLightPath) -> bool:
        nsi_lp_vlans = VlanRanges(flatten(sap.vlanrange for sap in nsi_lp.vc.saps))
        return (nsi_lp_vlans - nsistp.vlan_range) != nsi_lp_vlans

    return [nsi_lp for nsi_lp in nsi_lps_by_port if check_in_use_by_nsi_lp(nsi_lp)]


def validate_not_in_use_by_nsi_lp(subscription_id: UUID) -> None:
    nsistp = Nsistp.from_subscription(subscription_id)
    if in_use_by_nsi_lps := get_in_use_by_nsi_lp(nsistp):
        in_use_by_nsi_lp_ids = ",".join(str(nsi_lp.subscription_id) for nsi_lp in in_use_by_nsi_lps)
        raise ValueError(
            f"NSISTP cannot be removed with more than 1 vlan in use by NSILPs, NSILP's that still use vlans of NSISTP ({in_use_by_nsi_lp_ids})."
        )


def terminate_initial_input_form_generator(subscription_id: UUID) -> InputForm:
    SubscriptionId: TypeAlias = Annotated[DisplaySubscription, Field(subscription_id)]

    class TerminateForm(FormPage):
        subscription_id: SubscriptionId
        ticket_id: JiraTicketId | None = None

        @model_validator(mode="after")
        def check_not_in_use_by_nsi_lp(self) -> "TerminateForm":
            validate_not_in_use_by_nsi_lp(self.subscription_id)
            return self

    return TerminateForm


@terminate_workflow("Terminate NSISTP", initial_input_form=terminate_initial_input_form_generator)
def terminate_nsistp() -> StepList:
    return begin >> load_initial_state
