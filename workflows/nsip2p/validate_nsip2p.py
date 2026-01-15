# Copyright 2019-2026 SURF, Geant.
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

from orchestrator.workflow import StepList, begin, step
from orchestrator.workflows.utils import validate_workflow
from pydantic_forms.types import State

from products.product_types.nsip2p import Nsip2p


@step("Validate NSIP2P in IMS")
def validate_nsip2p_in_ims(subscription: Nsip2p) -> State:
    # TODO: implement IMS validation for virtual circuit, VLAN groups and terminations
    raise AssertionError("NSIP2P validation not implemented")


@validate_workflow("Validate NSIP2P")
def validate_nsip2p() -> StepList:
    return begin >> validate_nsip2p_in_ims

