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

from products.product_types.core_link import CoreLink, CoreLinkProvisioning


def subscription_description(subscription: SubscriptionModel) -> str:
    """The suggested pattern is to implement a subscription service that generates a subscription specific
    description, in case that is not present the description will just be set to the product name.
    """
    return f"{subscription.product.name} subscription"


logger = structlog.get_logger(__name__)


def initial_input_form_generator(subscription_id: UUIDstr) -> FormGenerator:
    subscription = CoreLink.from_subscription(subscription_id)
    core_link = subscription.core_link

    # TODO fill in additional fields if needed

    class ModifyCoreLinkForm(FormPage):
        organisation: OrganisationId = subscription.customer_id  # type: ignore

        divider_1: Divider

        ports: list = ReadOnlyField(core_link.ports)
        ims_id: int = ReadOnlyField(core_link.ims_id)
        under_maintenance: bool = ReadOnlyField(core_link.under_maintenance)

    user_input = yield ModifyCoreLinkForm
    user_input_dict = user_input.dict()

    yield from create_summary_form(user_input_dict, subscription)

    return user_input_dict | {"subscription": subscription}


def create_summary_form(user_input: dict, subscription: CoreLink) -> Generator:
    product_summary_fields = [
        "ports",
        "ims_id",
        "under_maintenance",
    ]

    before = [str(getattr(subscription.core_link, nm)) for nm in product_summary_fields]
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
    subscription: CoreLinkProvisioning,
) -> State:
    # TODO: get all modified fields
    return {"subscription": subscription}


@step("Update subscription description")
def update_subscription_description(subscription: CoreLink) -> State:
    subscription.description = subscription_description(subscription)
    return {"subscription": subscription}


additional_steps = begin


@modify_workflow("Modify core_link", initial_input_form=initial_input_form_generator, additional_steps=additional_steps)
def modify_core_link() -> StepList:
    return (
        begin
        >> set_status(SubscriptionLifecycle.PROVISIONING)
        >> update_subscription
        >> update_subscription_description
        # TODO add additional steps if needed
        >> set_status(SubscriptionLifecycle.ACTIVE)
    )
