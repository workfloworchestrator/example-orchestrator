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
from pydantic_forms.types import State

from orchestrator.workflow import StepList, begin, step
from surf.products.product_types.sn8_nsistp import Nsistp
from surf.workflows.helpers import validate_subscription_description, validate_subscription_status_is_active
from surf.workflows.workflow import validate_workflow


@step("Check data in coredb")
def check_core_db(subscription: Nsistp) -> State:
    validate_subscription_status_is_active(subscription)
    validate_subscription_description(subscription)

    return {"check_core_db": True}


@validate_workflow("Validate NSISTP")
def validate_nsistp() -> StepList:
    return begin >> check_core_db
