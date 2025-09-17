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
from typing import TypeAlias, cast
from uuid import UUID

from pydantic import ConfigDict, model_validator
from pydantic_forms.types import FormGenerator, State, UUIDstr

from orchestrator.forms import FormPage
from orchestrator.forms.validators import CustomerId, Divider, Label, ListOfOne
from orchestrator.targets import Target
from orchestrator.types import SubscriptionLifecycle
from orchestrator.workflow import StepList, begin, step
from orchestrator.workflows.steps import store_process_subscription
from surf.forms.validator.bandwidth import ServiceSpeed
from surf.forms.validator.service_port import ServicePort
from surf.forms.validators import JiraTicketId
from surf.products.product_types.sn8_nsistp import NsistpInactive, NsistpProvisioning
from surf.products.services.subscription import subscription_description
from surf.workflows.nsistp.sn8.shared.forms import (
    IsAlias,
    StpDescription,
    StpId,
    Topology,
    nsistp_fill_sap,
    nsistp_service_port,
    validate_both_aliases_empty_or_not,
)
from surf.workflows.shared.summary_form import base_summary
from surf.workflows.workflow import create_workflow


def initial_input_form_generator(product_name: str) -> FormGenerator:
    FormNsistpServicePort: TypeAlias = cast(type[ServicePort], nsistp_service_port())

    SingleServicePort = ListOfOne[FormNsistpServicePort]

    class CreateNsiStpForm(FormPage):
        model_config = ConfigDict(title=product_name)

        customer_id: CustomerId
        ticket_id: JiraTicketId

        label_nsistp_settings: Label
        divider: Divider

        service_ports: SingleServicePort

        topology: Topology

        stp_id: StpId
        stp_description: StpDescription | None = None

        is_alias_in: IsAlias | None = None
        is_alias_out: IsAlias | None = None

        expose_in_topology: bool = True

        bandwidth_info: ServiceSpeed

        @model_validator(mode="after")
        def validate_is_alias_in_out(self) -> "CreateNsiStpForm":
            validate_both_aliases_empty_or_not(self.is_alias_in, self.is_alias_out)
            return self

    user_input = yield CreateNsiStpForm

    user_input_dict = user_input.model_dump()
    yield from base_summary(product_name, user_input_dict)

    return user_input_dict


@step("Create subscription")
def construct_nsistp_subscription(
    customer_id: UUIDstr,
    product: UUID,
    service_ports: list[dict],
    topology: str,
    stp_id: str,
    stp_description: str | None,
    is_alias_in: str,
    is_alias_out: str,
    expose_in_topology: bool,
    bandwidth_info: int,
) -> State:
    nsistp = NsistpInactive.from_product_id(product, customer_id)

    settings = nsistp.settings
    settings.topology = topology
    settings.stp_id = stp_id
    settings.stp_description = stp_description
    settings.is_alias_in = is_alias_in
    settings.is_alias_out = is_alias_out
    settings.expose_in_topology = expose_in_topology
    settings.bandwidth = bandwidth_info

    nsistp_fill_sap(nsistp, service_ports)

    nsistp = NsistpProvisioning.from_other_lifecycle(nsistp, SubscriptionLifecycle.PROVISIONING)
    nsistp.description = subscription_description(nsistp)

    return {
        "subscription": nsistp,
        "subscription_id": nsistp.subscription_id,
        "subscription_description": nsistp.description,
    }


@create_workflow("Create NSISTP", initial_input_form=initial_input_form_generator)
def create_nsistp() -> StepList:
    return begin >> construct_nsistp_subscription >> store_process_subscription(Target.CREATE)
