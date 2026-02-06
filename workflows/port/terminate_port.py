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


from orchestrator.types import SubscriptionLifecycle
from orchestrator.workflow import StepList, begin, step
from orchestrator.workflows.steps import set_status
from orchestrator.workflows.utils import terminate_workflow

from products.product_types.port import PortProvisioning
from pydantic_forms.core import FormPage
from pydantic_forms.types import InputForm, State, UUIDstr
from pydantic_forms.validators import DisplaySubscription
from workflows.port.shared.steps import update_port_in_ims


def terminate_initial_input_form_generator(subscription_id: UUIDstr) -> InputForm:
    temp_subscription_id = subscription_id

    class TerminateForm(FormPage):
        subscription_id: DisplaySubscription = temp_subscription_id  # type: ignore

    return TerminateForm


@step("Release port")
def release_port(subscription: PortProvisioning) -> State:
    """Release port."""
    subscription.port.port_description = ""
    subscription.port.enabled = False

    return {"subscription": subscription}


@terminate_workflow("Terminate port", initial_input_form=terminate_initial_input_form_generator)
def terminate_port() -> StepList:
    return begin >> set_status(SubscriptionLifecycle.PROVISIONING) >> release_port >> update_port_in_ims
