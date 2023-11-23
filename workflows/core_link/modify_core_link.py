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


from orchestrator.forms import FormPage
from orchestrator.types import FormGenerator, State, SubscriptionLifecycle, UUIDstr
from orchestrator.workflow import StepList, begin, step
from orchestrator.workflows.steps import set_status
from orchestrator.workflows.utils import modify_workflow

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
    user_input_dict = user_input.dict()

    summary_fields = ["under_maintenance"]
    yield from modify_summary_form(user_input_dict, subscription.core_link, summary_fields)

    return user_input_dict | {"subscription": subscription}


@step("Update subscription")
def update_subscription(subscription: CoreLinkProvisioning, under_maintenance: bool) -> State:
    subscription.core_link.under_maintenance = under_maintenance

    return {"subscription": subscription}


@step("Update subscription description")
def update_subscription_description(subscription: CoreLink) -> State:
    subscription.description = description(subscription)
    return {"subscription": subscription}


@step("Core link under maintenance?")
def core_link_under_maintenance(subscription: CoreLinkProvisioning) -> State:
    # TODO: implement interface to NRM
    # update_core_link_in_nrm(subscription.core_link.nrm_id, maintenance=subscription.core_link.under_maintenance)

    return {"maintenance": subscription.core_link.under_maintenance}


@modify_workflow("Modify core_link", initial_input_form=initial_input_form_generator)
def modify_core_link() -> StepList:
    return (
        begin
        >> set_status(SubscriptionLifecycle.PROVISIONING)
        >> update_subscription
        >> update_subscription_description
        >> core_link_under_maintenance
        >> set_status(SubscriptionLifecycle.ACTIVE)
    )
