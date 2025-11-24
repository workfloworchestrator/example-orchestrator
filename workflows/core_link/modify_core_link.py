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


from pydantic_forms.types import UUIDstr
from orchestrator.workflow import StepList, begin, step
from orchestrator.workflows.utils import modify_workflow, ensure_provisioning_status
from pydantic_forms.core import FormPage
from pydantic_forms.types import FormGenerator, State

from products.product_types.core_link import CoreLink, CoreLinkProvisioning
from products.services.description import description
from workflows.shared import modify_summary_form


def initial_input_form_generator(subscription_id: UUIDstr) -> FormGenerator:
    subscription = CoreLink.from_subscription(subscription_id)
    core_link = subscription.core_link

    class ModifyCoreLinkForm(FormPage):
        # organisation: OrganisationId = subscription.customer_id  # type: ignore

        under_maintenance: bool = core_link.under_maintenance

    user_input = yield ModifyCoreLinkForm
    user_input_dict = user_input.model_dump()

    summary_fields = ["under_maintenance"]
    yield from modify_summary_form(user_input_dict, subscription.core_link, summary_fields)

    return user_input_dict | {"subscription": subscription}


@ensure_provisioning_status
@step("Update subscription")
def update_subscription(subscription: CoreLinkProvisioning, under_maintenance: bool) -> State:
    subscription.core_link.under_maintenance = under_maintenance
    subscription.description = description(subscription)

    return {"subscription": subscription}


@step("Update core link in NRM")
def update_core_link_in_nrm(subscription: CoreLink) -> State:
    """Dummy step, replace with actual call to NRM."""
    return {"subscription": subscription}


@modify_workflow("Modify core_link", initial_input_form=initial_input_form_generator)
def modify_core_link() -> StepList:
    return (
        begin
        >> update_subscription
        >> update_core_link_in_nrm
    )
