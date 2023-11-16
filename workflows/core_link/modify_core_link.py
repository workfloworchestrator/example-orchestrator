from collections.abc import Generator

from orchestrator.forms import FormPage
from orchestrator.forms.validators import MigrationSummary
from orchestrator.types import FormGenerator, State, SubscriptionLifecycle, UUIDstr
from orchestrator.workflow import StepList, begin, step
from orchestrator.workflows.steps import set_status
from orchestrator.workflows.utils import modify_workflow

from products.product_types.core_link import CoreLink, CoreLinkProvisioning
from products.services.description import description


def initial_input_form_generator(subscription_id: UUIDstr) -> FormGenerator:
    subscription = CoreLink.from_subscription(subscription_id)
    core_link = subscription.core_link

    class ModifyCoreLinkForm(FormPage):
        # organisation: OrganisationId = subscription.customer_id  # type: ignore

        under_maintenance: bool = core_link.under_maintenance

    user_input = yield ModifyCoreLinkForm
    user_input_dict = user_input.dict()

    yield from create_summary_form(user_input_dict, subscription)

    return user_input_dict | {"subscription": subscription}


def create_summary_form(user_input: dict, subscription: CoreLink) -> Generator:
    product_summary_fields = [
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

    yield SummaryForm


@step("Update subscription")
def update_subscription(subscription: CoreLinkProvisioning, under_maintenance: bool) -> State:
    subscription.core_link.under_maintenance = under_maintenance

    return {"subscription": subscription}


@step("Update subscription description")
def update_subscription_description(subscription: CoreLink) -> State:
    subscription.description = description(subscription)
    return {"subscription": subscription}


@step("Core link under maintenance?")
def core_link_under_maintenance(subscription: CoreLinkProvisioning) -> State:
    # TODO: implement interface to NRM
    # update_core_link_in_nrm(subscription.core_link.nrm_id, maintenance=subscription.core_link.under_maintenance)

    return {"maintenance": subscription.core_link.under_maintenance}


@modify_workflow("Modify core_link", initial_input_form=initial_input_form_generator)
def modify_core_link() -> StepList:
    return (
        begin
        >> set_status(SubscriptionLifecycle.PROVISIONING)
        >> update_subscription
        >> update_subscription_description
        >> core_link_under_maintenance
        >> set_status(SubscriptionLifecycle.ACTIVE)
    )
