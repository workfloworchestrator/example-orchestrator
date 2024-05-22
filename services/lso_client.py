# Copyright 2023-2024 GÉANT Vereniging.
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
"""The LSO client service, which interacts with :term:`LSO` running externally.

:term:`LSO` is responsible for executing Ansible playbooks, that deploy subscriptions.
"""

import json
import logging
from os import getenv
from typing import Any

import requests
from orchestrator import step
from orchestrator.config.assignee import Assignee
from orchestrator.types import State
from orchestrator.utils.errors import ProcessFailureError
from orchestrator.workflow import conditional, Step, StepList, begin, callback_step, inputstep
from pydantic_forms.core import FormPage
from pydantic_forms.types import FormGenerator
from pydantic_forms.validators import LongText

logger = logging.getLogger(__name__)


def _send_request(parameters: dict, callback_route: str) -> None:
    """Send a request to :term:`LSO`. The callback address is derived using the process ID provided.

    :param parameters: JSON body for the request, which will almost always at least consist of a subscription object,
        and a boolean value to indicate a dry run.
    :type parameters: dict
    :param callback_route: The callback route that should be used to resume the workflow.
    :type callback_route: str
    :rtype: None
    """
    # Build up a callback URL of the Provisioning Proxy to return its results to.
    callback_url = f"{getenv('ORCHESTRATOR_URL')}{callback_route}"
    debug_msg = f"[provisioning proxy] Callback URL set to {callback_url}"
    logger.debug(debug_msg)

    parameters.update({"callback": callback_url})
    url = getenv("LSO_PLAYBOOK_URL")

    request = requests.post(url, json=parameters, timeout=10)
    request.raise_for_status()


def execute_playbook(
    playbook_name: str,
    callback_route: str,
    inventory: dict[str, Any] | str,
    extra_vars: dict[str, Any],
) -> None:
    """Execute a playbook remotely through the provisioning proxy.

    When providing this method with an inventory, the format should be compatible with the Ansible YAML-based format.
    For example, an inventory consisting of two hosts, which each a unique host variable assigned to them looks as
    follows:

    .. code-block:: json

        "inventory": {
            "all": {
                "hosts": {
                    "host1.local": {
                        "foo": "bar"
                    },
                    "host2.local": {
                        "key": "value"
                    }
                }
            }
        }

    .. warning::
       Note the fact that the collection of all hosts is a dictionary, and not a list of strings. Ansible expects each
       host to be a key-value pair. The key is the :term:`FQDN` of a host, and the value always ``null``.

    The extra vars can be a simple dict consisting of key-value pairs, for example:

    .. code-block:: json

        "extra_vars": {
            "dry_run": true,
            "commit_comment": "I am a robot!",
            "verb": "deploy"
        }

    :param str playbook_name: Filename of the playbook that is to be executed. It must be present on the remote system
                              running the provisioning proxy, otherwise it will return an error.
    :param str callback_route: The endpoint at which :term:`GSO` expects a callback to continue the workflow executing
                               this step.
    :param dict[str, Any] inventory: An inventory of machines at which the playbook is targeted. Must be in
                                     YAML-compatible format.
    :param dict[str, Any] extra_vars: Any extra variables that the playbook relies on. This can include a subscription
                                      object, a boolean value indicating a dry run, a commit comment, etc.
    """
    parameters = {
        "playbook_name": playbook_name,
        "inventory": inventory,
        "extra_vars": extra_vars,
    }

    _send_request(parameters, callback_route)


@step("Evaluate provisioning proxy result")
def _evaluate_results(callback_result: dict) -> State:
    if callback_result["return_code"] != 0:
        raise ProcessFailureError(message="Provisioning proxy failure", details=callback_result)

    return {"callback_result": callback_result}


@step("Ignore provisioning proxy result")
def _ignore_results(callback_result: dict) -> State:
    return {"callback_result": callback_result}


@inputstep("Confirm provisioning proxy results", assignee=Assignee("SYSTEM"))
def _show_results(state: State) -> FormGenerator:
    if "callback_result" not in state:
        return state

    class ConfirmRunPage(FormPage):
        class Config:
            title: str = f"Execution for {state['subscription']['product']['name']} completed."

        run_status: str = state["callback_result"]["status"]
        run_results: LongText = json.dumps(state["callback_result"], indent=4)

    yield ConfirmRunPage
    state.pop("run_results")
    return state


def lso_interaction(provisioning_step: Step) -> StepList:
    """Interact with the provisioning proxy :term:`LSO` using a callback step.

    An asynchronous interaction with the provisioning proxy. This is an external system that executes Ansible playbooks
    to provision service subscriptions. If the playbook fails, this step will also fail, allowing for the user to retry
    provisioning from the UI.

    :param provisioning_step: A workflow step that performs an operation remotely using the provisioning proxy.
    :type provisioning_step: :class:`Step`
    :return: A list of steps that is executed as part of the workflow.
    :rtype: :class:`StepList`
    """
    lso_is_enabled = conditional(lambda _: getenv("LSO_ENABLED") == "True")
    return (
        begin
        >> lso_is_enabled(
            begin
            >> callback_step(
                name=provisioning_step.name,
                action_step=provisioning_step,
                validate_step=_evaluate_results,
            )
            >> _show_results
        )
    )


def indifferent_lso_interaction(provisioning_step: Step) -> StepList:
    """Interact with the provisioning proxy :term:`LSO` using a callback step.

    This interaction is identical from the one described in ``lso_interaction()``, with one functional difference.
    Whereas the ``lso_interaction()`` will make the workflow step fail on unsuccessful interaction, this step will not.
    It is therefore indifferent about the outcome of the Ansible playbook that is executed.

    .. warning::
       Using this interaction requires the operator to carefully evaluate the outcome of a playbook themselves. If a
       playbook fails, this will not cause the workflow to fail.

    :param provisioning_step: A workflow step that performs an operation remotely using the provisioning proxy.
    :type provisioning_step: :class:`Step`
    :return: A list of steps that is executed as part of the workflow.
    :rtype: :class:`StepList`
    """
    lso_is_enabled = conditional(lambda _: getenv("LSO_ENABLED") == "True")
    return (
        begin
        >> lso_is_enabled(
            begin
            >> callback_step(
                name=provisioning_step.name,
                action_step=provisioning_step,
                validate_step=_ignore_results,
            )
            >> _show_results
        )
    )
