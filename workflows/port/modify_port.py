from orchestrator.forms import FormPage
from orchestrator.forms.validators import Label
from orchestrator.types import FormGenerator, State, SubscriptionLifecycle, UUIDstr
from orchestrator.workflow import StepList, begin, step
from orchestrator.workflows.steps import set_status
from orchestrator.workflows.utils import modify_workflow
from pydantic_forms.core import ReadOnlyField

from products.product_types.port import Port, PortProvisioning
from products.services.description import description
from workflows.port.shared.steps import update_port_in_ims
from workflows.shared import modify_summary_form


def initial_input_form_generator(subscription_id: UUIDstr) -> FormGenerator:
    subscription = Port.from_subscription(subscription_id)
    port = subscription.port

    class ModifyPortForm(FormPage):
        # organisation: OrganisationId = subscription.customer_id  # type: ignore

        port_settings: Label

        node_name: str = ReadOnlyField(port.node.node_name)
        port_name: str = ReadOnlyField(port.port_name)
        port_type: str = ReadOnlyField(port.port_type)
        port_mode: str = ReadOnlyField(port.port_mode)
        port_description: str = port.port_description
        auto_negotiation: bool = port.auto_negotiation
        lldp: bool = port.lldp

    user_input = yield ModifyPortForm
    user_input_dict = user_input.dict()

    summary_fields = ["port_description", "auto_negotiation", "lldp"]
    yield from modify_summary_form(user_input_dict, subscription, summary_fields)

    return user_input_dict | {"subscription": subscription}


@step("Update subscription")
def update_subscription(
    subscription: PortProvisioning,
    port_description: str,
    auto_negotiation: bool,
    lldp: bool,
) -> State:
    subscription.port.port_description = port_description
    subscription.port.auto_negotiation = auto_negotiation
    subscription.port.lldp = lldp
    subscription.description = description(subscription)

    return {"subscription": subscription}


@modify_workflow("Modify port", initial_input_form=initial_input_form_generator)
def modify_port() -> StepList:
    return (
        begin
        >> set_status(SubscriptionLifecycle.PROVISIONING)
        >> update_subscription
        >> update_port_in_ims
        >> set_status(SubscriptionLifecycle.ACTIVE)
    )
