from orchestrator.forms import FormPage
from orchestrator.forms.validators import DisplaySubscription
from orchestrator.types import InputForm, State, SubscriptionLifecycle, UUIDstr
from orchestrator.workflow import StepList, begin, step
from orchestrator.workflows.steps import set_status
from orchestrator.workflows.utils import terminate_workflow

from products.product_types.port import PortProvisioning
from workflows.port.shared.steps import update_port_in_ims


def terminate_initial_input_form_generator(subscription_id: UUIDstr, organisation: UUIDstr) -> InputForm:
    temp_subscription_id = subscription_id

    class TerminateForm(FormPage):
        subscription_id: DisplaySubscription = temp_subscription_id  # type: ignore

    return TerminateForm


@step("Release port")
def release_port(subscription: PortProvisioning) -> State:
    """Release port."""
    subscription.port.port_description = ""
    subscription.port.enabled = False

    return {"subscription": subscription}


@terminate_workflow("Terminate port", initial_input_form=terminate_initial_input_form_generator)
def terminate_port() -> StepList:
    return begin >> set_status(SubscriptionLifecycle.PROVISIONING) >> release_port >> update_port_in_ims
