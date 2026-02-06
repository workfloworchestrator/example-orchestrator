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
from orchestrator.forms.validators import DisplaySubscription
from orchestrator.workflow import StepList, begin
from orchestrator.workflows.utils import terminate_workflow

from pydantic_forms.types import InputForm, UUIDstr

logger = structlog.get_logger(__name__)


def terminate_initial_input_form_generator(subscription_id: UUIDstr, customer_id: UUIDstr) -> InputForm:
    temp_subscription_id = subscription_id

    class TerminateNsistpForm(FormPage):
        subscription_id: DisplaySubscription = temp_subscription_id  # type: ignore

    return TerminateNsistpForm


@terminate_workflow("Terminate nsistp", initial_input_form=terminate_initial_input_form_generator)
def terminate_nsistp() -> StepList:
    return (
        begin
        # TODO: fill in additional steps if needed
    )
