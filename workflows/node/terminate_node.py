from orchestrator.forms import FormPage
from orchestrator.forms.validators import DisplaySubscription
from orchestrator.types import InputForm, State, UUIDstr
from orchestrator.workflow import StepList, begin, step
from orchestrator.workflows.utils import terminate_workflow

from products.product_types.node import Node


@step("Load initial state")
def load_initial_state(subscription: Node) -> State:
    # TODO: optionally add additional values.
    # Copy values to the root of the state for easy access

    return {
        "subscription": subscription,
    }


def terminate_initial_input_form_generator(subscription_id: UUIDstr, organisation: UUIDstr) -> InputForm:
    temp_subscription_id = subscription_id

    class TerminateForm(FormPage):
        subscription_id: DisplaySubscription = temp_subscription_id  # type: ignore

    return TerminateForm


additional_steps = begin


@terminate_workflow(
    "Terminate node", initial_input_form=terminate_initial_input_form_generator, additional_steps=additional_steps
)
def terminate_node() -> StepList:
    return (
        begin
        >> load_initial_state
        # TODO: fill in additional steps if needed
    )
