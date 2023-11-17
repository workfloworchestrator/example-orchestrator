from collections.abc import Generator

from orchestrator.forms import FormPage
from orchestrator.forms.validators import MigrationSummary
from orchestrator.types import FormGenerator, State, SubscriptionLifecycle, UUIDstr
from orchestrator.workflow import StepList, begin, step
from orchestrator.workflows.steps import set_status
from orchestrator.workflows.utils import modify_workflow

from products.product_types.l2vpn import L2vpn, L2vpnProvisioning
from products.services.description import description


def initial_input_form_generator(subscription_id: UUIDstr) -> FormGenerator:
    subscription = L2vpn.from_subscription(subscription_id)
    virtual_circuit = subscription.virtual_circuit

    class ModifyL2vpnForm(FormPage):
        speed: int = virtual_circuit.speed
        speed_policer: bool = virtual_circuit.speed_policer

    user_input = yield ModifyL2vpnForm
    user_input_dict = user_input.dict()

    yield from create_summary_form(user_input_dict, subscription)

    return user_input_dict | {"subscription": subscription}


def create_summary_form(user_input: dict, subscription: L2vpn) -> Generator:
    product_summary_fields = [
        "speed",
        "speed_policer",
    ]

    before = [str(getattr(subscription.virtual_circuit, nm)) for nm in product_summary_fields]
    after = [str(user_input[nm]) for nm in product_summary_fields]

    class ProductSummary(MigrationSummary):
        data = {
            "labels": product_summary_fields,
            "headers": ["Before", "After"],
            "columns": [before, after],
        }

    class SummaryForm(FormPage):
        class Config:
            title = f"{subscription.product.name} Summary"

        product_summary: ProductSummary

    yield SummaryForm


@step("Update subscription")
def update_subscription(
    subscription: L2vpnProvisioning,
    speed: int,
    speed_policer: bool,
) -> State:
    subscription.virtual_circuit.speed = speed
    subscription.virtual_circuit.speed_policer = speed_policer

    return {"subscription": subscription}


@step("Update subscription description")
def update_subscription_description(subscription: L2vpn) -> State:
    subscription.description = description(subscription)
    return {"subscription": subscription}


@modify_workflow("Modify l2vpn", initial_input_form=initial_input_form_generator)
def modify_l2vpn() -> StepList:
    return (
        begin
        >> set_status(SubscriptionLifecycle.PROVISIONING)
        >> update_subscription
        >> update_subscription_description
        # TODO add step to update description in IMS
        >> set_status(SubscriptionLifecycle.ACTIVE)
    )
