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


from orchestrator.types import InputForm, UUIDstr
from orchestrator.workflow import StepList, begin, step
from orchestrator.workflows.utils import terminate_workflow
from pydantic_forms.core import FormPage
from pydantic_forms.types import State
from pydantic_forms.validators import DisplaySubscription

from products.product_types.core_link import CoreLink
from products.services.netbox.netbox import build_payload
from services import netbox


#def terminate_initial_input_form_generator(subscription_id: UUIDstr, organisation: UUIDstr) -> InputForm:
def terminate_initial_input_form_generator(subscription_id: UUIDstr) -> InputForm:
    temp_subscription_id = subscription_id

    class TerminateForm(FormPage):
        subscription_id: DisplaySubscription = temp_subscription_id  # type: ignore

    return TerminateForm


@step("Disconnect ports in IMS")
def disconnect_ports(subscription: CoreLink) -> None:
    netbox.delete_cable(id=subscription.core_link.ims_id)


@step("Unassign side B IPv6 address")
def unassign_side_b_ipv6_prefix(subscription: CoreLink) -> None:
    netbox.delete_ip_address(id=subscription.core_link.ports[1].ipv6_ipam_id)


@step("Unassign side A IPv6 address")
def unassign_side_a_ipv6_prefix(subscription: CoreLink) -> None:
    netbox.delete_ip_address(id=subscription.core_link.ports[0].ipv6_ipam_id)


@step("Unassign IPv6 prefix")
def unassign_ipv6_prefix(subscription: CoreLink) -> None:
    netbox.delete_prefix(id=subscription.core_link.ipv6_prefix_ipam_id)


@step("disable ports in IMS")
def disable_ports(subscription: CoreLink) -> State:
    """Disable ports in IMS"""
    subscription.core_link.ports[0].enabled = False
    payload_port_a = build_payload(subscription.core_link.ports[0], subscription)
    netbox.update(payload_port_a, id=subscription.core_link.ports[0].ims_id)
    subscription.core_link.ports[1].enabled = False
    payload_port_b = build_payload(subscription.core_link.ports[1], subscription)
    netbox.update(payload_port_b, id=subscription.core_link.ports[1].ims_id)

    return {"subscription": subscription, "payload_port_a": payload_port_a, "payload_port_b": payload_port_b}


@terminate_workflow("Terminate core_link", initial_input_form=terminate_initial_input_form_generator)
def terminate_core_link() -> StepList:
    return (
        begin
        >> disconnect_ports
        >> unassign_side_b_ipv6_prefix
        >> unassign_side_a_ipv6_prefix
        >> unassign_ipv6_prefix
        >> disable_ports
    )
