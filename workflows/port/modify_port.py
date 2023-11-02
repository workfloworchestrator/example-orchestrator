from collections.abc import Generator

import structlog
from orchestrator.domain import SubscriptionModel
from orchestrator.forms import FormPage
from orchestrator.forms.validators import Divider, MigrationSummary, OrganisationId
from orchestrator.types import FormGenerator, State, SubscriptionLifecycle, UUIDstr
from orchestrator.workflow import StepList, begin, step
from orchestrator.workflows.steps import set_status
from orchestrator.workflows.utils import modify_workflow
from pydantic_forms.core import ReadOnlyField

from products.product_types.port import Port, PortProvisioning


def subscription_description(subscription: SubscriptionModel) -> str:
    """The suggested pattern is to implement a subscription service that generates a subscription specific
    description, in case that is not present the description will just be set to the product name.
    """
    return f"{subscription.product.name} subscription"


logger = structlog.get_logger(__name__)


def initial_input_form_generator(subscription_id: UUIDstr) -> FormGenerator:
    subscription = Port.from_subscription(subscription_id)
    port = subscription.port

    # TODO fill in additional fields if needed

    class ModifyPortForm(FormPage):
        organisation: OrganisationId = subscription.customer_id  # type: ignore

        divider_1: Divider

        port_mode: str = ReadOnlyField(port.port_mode)
        auto_negotiation: bool = ReadOnlyField(port.auto_negotiation)
        lldp: bool = ReadOnlyField(port.lldp)
        ims_id: int = ReadOnlyField(port.ims_id)
        nrm_id: int = ReadOnlyField(port.nrm_id)
        port_name: str = port.port_name
        port_description: str = port.port_description

    user_input = yield ModifyPortForm
    user_input_dict = user_input.dict()

    yield from create_summary_form(user_input_dict, subscription)

    return user_input_dict | {"subscription": subscription}


def create_summary_form(user_input: dict, subscription: Port) -> Generator:
    product_summary_fields = [
        "port_name",
        "port_description",
        "port_mode",
        "auto_negotiation",
        "lldp",
        "node",
        "ims_id",
        "nrm_id",
    ]

    before = [str(getattr(subscription.port, nm)) for nm in product_summary_fields]
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
        divider_1: Divider

    # TODO fill in additional details if needed

    yield SummaryForm


@step("Update subscription")
def update_subscription(
    subscription: PortProvisioning,
    port_name: str,
    port_description: str,
) -> State:
    # TODO: get all modified fields
    subscription.port.port_name = port_name
    subscription.port.port_description = port_description
    return {"subscription": subscription}


@step("Update subscription description")
def update_subscription_description(subscription: Port) -> State:
    subscription.description = subscription_description(subscription)
    return {"subscription": subscription}


additional_steps = begin


@modify_workflow("Modify port", initial_input_form=initial_input_form_generator, additional_steps=additional_steps)
def modify_port() -> StepList:
    return (
        begin
        >> set_status(SubscriptionLifecycle.PROVISIONING)
        >> update_subscription
        >> update_subscription_description
        # TODO add additional steps if needed
        >> set_status(SubscriptionLifecycle.ACTIVE)
    )
