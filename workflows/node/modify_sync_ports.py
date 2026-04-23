# Copyright 2019-2026 SURF.
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
from orchestrator.workflow import StepList, begin
from orchestrator.workflows.steps import set_status
from orchestrator.workflows.utils import modify_initial_input_form_generator, modify_workflow

from workflows.node.shared.steps import update_interfaces


@modify_workflow(initial_input_form=modify_initial_input_form_generator)
def modify_sync_ports() -> StepList:
    return (
        begin
        >> set_status(SubscriptionLifecycle.PROVISIONING)
        >> update_interfaces
        >> set_status(SubscriptionLifecycle.ACTIVE)
    )
