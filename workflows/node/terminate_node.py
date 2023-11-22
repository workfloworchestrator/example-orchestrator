from orchestrator.forms import FormPage
from orchestrator.forms.validators import DisplaySubscription
from orchestrator.types import InputForm, State, UUIDstr
from orchestrator.workflow import StepList, begin, step
from orchestrator.workflows.utils import terminate_workflow

from products.product_types.node import Node
from services import netbox


def terminate_initial_input_form_generator(subscription_id: UUIDstr, organisation: UUIDstr) -> InputForm:
    temp_subscription_id = subscription_id

    class TerminateForm(FormPage):
        subscription_id: DisplaySubscription = temp_subscription_id  # type: ignore

    return TerminateForm


@step("Load initial state")
def load_initial_state(subscription: Node) -> State:
    return {"ims_id": subscription.node.ims_id}


@step("Delete node from IMS")
def delete_node_from_ims(ims_id: int) -> State:
    """Delete node from IMS."""

    # This relies on Netbox to delete the loopback interface and associated IP addresses as well.
    netbox.delete_device(id=ims_id)

    return {}


@terminate_workflow("Terminate node", initial_input_form=terminate_initial_input_form_generator)
def terminate_node() -> StepList:
    return begin >> load_initial_state >> delete_node_from_ims
