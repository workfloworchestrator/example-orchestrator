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


import structlog
from orchestrator.forms import FormPage
from orchestrator.forms.validators import Divider
from orchestrator.types import SubscriptionLifecycle
from orchestrator.workflow import StepList, begin, step
from orchestrator.workflows.steps import set_status
from orchestrator.workflows.utils import modify_workflow
from pydantic_forms.types import FormGenerator, State, UUIDstr
from pydantic_forms.validators import read_only_field

from products.product_types.nsistp import Nsistp, NsistpProvisioning
from products.services.description import description
from workflows.nsistp.shared.forms import IsAlias, ServiceSpeed, StpDescription, Topology
from workflows.shared import modify_summary_form

logger = structlog.get_logger(__name__)


def initial_input_form_generator(subscription_id: UUIDstr) -> FormGenerator:
    subscription = Nsistp.from_subscription(subscription_id)
    nsistp = subscription.nsistp

    class ModifyNsistpForm(FormPage):
        stp_id: read_only_field(nsistp.stp_id)

        divider_1: Divider

        topology: Topology = nsistp.topology
        stp_description: StpDescription | None = nsistp.stp_description
        is_alias_in: IsAlias | None = nsistp.is_alias_in
        is_alias_out: IsAlias | None = nsistp.is_alias_out
        expose_in_topology: bool | None = nsistp.expose_in_topology
        bandwidth: ServiceSpeed | None = nsistp.bandwidth

    user_input = yield ModifyNsistpForm
    user_input_dict = user_input.dict()

    summary_fields = [
        "topology",
        "stp_id",
        "stp_description",
        "is_alias_in",
        "is_alias_out",
        "expose_in_topology",
        "bandwidth",
    ]
    yield from modify_summary_form(user_input_dict, subscription.nsistp, summary_fields)

    return user_input_dict | {"subscription": subscription}


@step("Update subscription")
def update_subscription(
    subscription: NsistpProvisioning,
    topology: str,
    stp_description: str | None,
    is_alias_in: str | None,
    is_alias_out: str | None,
    expose_in_topology: bool | None,
    bandwidth: int | None,
) -> State:
    subscription.nsistp.topology = topology
    subscription.nsistp.stp_description = stp_description
    subscription.nsistp.is_alias_in = is_alias_in
    subscription.nsistp.is_alias_out = is_alias_out
    subscription.nsistp.expose_in_topology = expose_in_topology
    subscription.nsistp.bandwidth = bandwidth

    return {"subscription": subscription}


@step("Update subscription description")
def update_subscription_description(subscription: Nsistp) -> State:
    subscription.description = description(subscription)
    return {"subscription": subscription}


@modify_workflow("Modify nsistp", initial_input_form=initial_input_form_generator)
def modify_nsistp() -> StepList:
    return (
        begin
        >> set_status(SubscriptionLifecycle.PROVISIONING)
        >> update_subscription
        >> update_subscription_description
        >> set_status(SubscriptionLifecycle.ACTIVE)
    )
