# Copyright 2019-2025 SURF, ESnet, GÉANT.
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

import typer
from nwastdlib.logging import initialise_logging
from orchestrator import app_settings
from orchestrator.cli.main import app as core_cli
from orchestrator.db import init_database
from orchestrator.log_config import LOGGER_OVERRIDES


def init_cli_app() -> typer.Typer:
    initialise_logging(LOGGER_OVERRIDES)
    init_database(app_settings)
    return core_cli()


if __name__ == "__main__":
    init_cli_app()
