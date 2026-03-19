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
from pydantic_forms.types import State

from orchestrator.workflow import StepList, step, begin
from orchestrator.workflows.utils import task

logger = structlog.get_logger(__name__)


@step("Perform a dummy step")
def perform_dummy_step() -> State:
    logger.debug("Perform a dummy step")
    return { "task_performed": True }

@task("Perform a dummy task")
def task_perform_dummy_task() -> StepList:
    return (
            begin
            >> perform_dummy_step
    )
