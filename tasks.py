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
from typing import Any
from uuid import UUID

from celery import Celery
from celery.signals import setup_logging, worker_shutting_down
from structlog import get_logger

from nwastdlib.logging import initialise_logging
from orchestrator.db import init_database
from orchestrator.db.database import ENGINE_ARGUMENTS
from orchestrator.domain import SUBSCRIPTION_MODEL_REGISTRY
from orchestrator.log_config import LOGGER_OVERRIDES, logger_config
from orchestrator.services.tasks import initialise_celery
from orchestrator.settings import app_settings
from orchestrator.types import BroadcastFunc
from orchestrator.websocket import (
    broadcast_process_update_to_websocket,
    init_websocket_manager,
)
from orchestrator.websocket.websocket_manager import WebSocketManager
from orchestrator.workflows import ALL_WORKFLOWS
from settings import backend, broker


logger = get_logger(__name__)


LOGGER_OVERRIDES_CELERY = LOGGER_OVERRIDES | dict(
    [
        logger_config("celery"),
        logger_config("kombu"),
    ]
)


@setup_logging.connect  # type: ignore[misc]
def on_setup_logging(**kwargs: Any) -> None:
    initialise_logging(additional_loggers=LOGGER_OVERRIDES_CELERY)


def process_broadcast_fn(process_id: UUID) -> None:
    # Catch all exceptions as broadcasting failure is noncritical to workflow completion
    try:
        broadcast_process_update_to_websocket(process_id)
    except Exception as e:
        logger.exception(e)


class OrchestratorWorker(Celery):
    websocket_manager: WebSocketManager
    process_broadcast_fn: BroadcastFunc

    def on_init(self) -> None:
        # ENGINE_ARGUMENTS["pool_size"] = 10
        init_database(app_settings)

        # Prepare the wrapped_websocket_manager
        # Note: cannot prepare the redis connections here as broadcasting is async
        self.websocket_manager = init_websocket_manager(app_settings)
        self.process_broadcast_fn = process_broadcast_fn

        # Load the products and load the workflows
        import products  # noqa: F401  Side-effects
        import workflows  # noqa: F401  Side-effects

        logger.info(
            "Loaded the workflows and products",
            workflows=len(ALL_WORKFLOWS.values()),
            products=len(SUBSCRIPTION_MODEL_REGISTRY.values()),
        )
        # register_forms()

    def close(self) -> None:
        super().close()


celery = OrchestratorWorker(
    f"{app_settings.SERVICE_NAME}-worker", broker=broker, include=["orchestrator.services.tasks"]
)

if app_settings.TESTING:
    celery.conf.update(backend=backend, task_ignore_result=False)
else:
    celery.conf.update(task_ignore_result=True)

celery.conf.update(
    result_expires=3600,
    worker_prefetch_multiplier=1,
    worker_send_task_event=True,
    task_send_sent_event=True,
)

# Needed if we load this as a Celery worker because in that case there is no 'main app'
initialise_celery(celery)


@worker_shutting_down.connect  # type: ignore
def worker_shutting_down_handler(sig, how, exitcode, **kwargs) -> None:
    celery.close()


# TODO figure out what's missing in the workflow registration - without this I can't run any workflows
# [error    ] Worker failed to execute workflow [orchestrator.services.tasks] details=Invalid workflow: module workflows.tasks.bootstrap_netbox does not exist or has invalid imports process_id=c1011606-b06d-419b-9a2f-69319610e7a5
print("IMPORTING..")
from workflows.tasks.bootstrap_netbox import task_bootstrap_netbox # noqa
print("IMPORTED")
