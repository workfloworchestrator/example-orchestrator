from orchestrator.forms import FormPage
from orchestrator.forms.validators import DisplaySubscription
from orchestrator.types import InputForm, State, UUIDstr
from orchestrator.workflow import StepList, begin, step
from orchestrator.workflows.utils import terminate_workflow

from products.product_types.core_link import CoreLink
from products.services.netbox.netbox import build_payload
from services import netbox


def terminate_initial_input_form_generator(subscription_id: UUIDstr, organisation: UUIDstr) -> InputForm:
    temp_subscription_id = subscription_id

    class TerminateForm(FormPage):
        subscription_id: DisplaySubscription = temp_subscription_id  # type: ignore

    return TerminateForm


@step("Disconnect ports in IMS")
def disconnect_ports(subscription: CoreLink) -> None:
    netbox.delete_cable(id=subscription.core_link.ims_id)


@step("Unassign IPv6 addresses")
def unassign_ip_addresses(subscription: CoreLink) -> None:
    netbox.delete_prefix(id=subscription.core_link.ipv6_prefix_ipam_id)
    netbox.delete_ip_address(id=subscription.core_link.ports[0].ipv6_ipam_id)
    netbox.delete_ip_address(id=subscription.core_link.ports[1].ipv6_ipam_id)


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
    return begin >> disconnect_ports >> unassign_ip_addresses >> disable_ports
