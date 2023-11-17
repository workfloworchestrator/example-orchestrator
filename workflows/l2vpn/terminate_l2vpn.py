from orchestrator.forms import FormPage
from orchestrator.forms.validators import DisplaySubscription
from orchestrator.types import InputForm, UUIDstr
from orchestrator.workflow import StepList, begin, step
from orchestrator.workflows.utils import terminate_workflow

from products.product_types.l2vpn import L2vpn
from services import netbox


def terminate_initial_input_form_generator(subscription_id: UUIDstr, organisation: UUIDstr) -> InputForm:
    temp_subscription_id = subscription_id

    class TerminateForm(FormPage):
        subscription_id: DisplaySubscription = temp_subscription_id  # type: ignore

    return TerminateForm


@step("Remove L2VPN from IMS")
def ims_remove_l2vpn(subscription: L2vpn) -> None:
    netbox.delete_l2vpn(id=subscription.virtual_circuit.ims_id)
    # We rely on Netbox to delete the vlan terminations together with the l2vpn.


@step("Remove VLANs from IMS")
def ims_remove_vlans(subscription: L2vpn) -> None:
    for sap in subscription.virtual_circuit.saps:
        netbox.delete_vlan(id=sap.ims_id)


@terminate_workflow("Terminate l2vpn", initial_input_form=terminate_initial_input_form_generator)
def terminate_l2vpn() -> StepList:
    return begin >> ims_remove_l2vpn >> ims_remove_vlans
