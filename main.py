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


from orchestrator import OrchestratorCore
from orchestrator.cli.main import app as core_cli
from orchestrator.settings import AppSettings

from graphql_federation import CUSTOM_GRAPHQL_MODELS
import products  # noqa: F401  Side-effects
import workflows  # noqa: F401  Side-effects

app = OrchestratorCore(base_settings=AppSettings())
app.register_graphql(graphql_models=CUSTOM_GRAPHQL_MODELS)

if __name__ == "__main__":
    core_cli()
