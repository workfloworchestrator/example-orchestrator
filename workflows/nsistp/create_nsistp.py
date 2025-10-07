# workflows/nsistp/create_nsistp.py
# from typing import TypeAlias, cast


from typing import Annotated

import structlog
from orchestrator.domain import SubscriptionModel
from orchestrator.forms import FormPage
from orchestrator.forms.validators import CustomerId, Divider, Label
from orchestrator.targets import Target
from orchestrator.types import SubscriptionLifecycle
from orchestrator.workflow import StepList, begin, step
from orchestrator.workflows.steps import store_process_subscription
from orchestrator.workflows.utils import create_workflow
from pydantic import AfterValidator, ConfigDict, model_validator
from pydantic_forms.types import FormGenerator, State, UUIDstr

from products.product_types.nsistp import NsistpInactive, NsistpProvisioning
from products.services.netbox.netbox import build_payload
from services import netbox
from workflows.nsistp.shared.forms import (
    IsAlias,
    ServiceSpeed,
    StpDescription,
    StpId,
    Topology,
    nsistp_fill_sap,
    ports_selector,
    validate_both_aliases_empty_or_not,
)
from workflows.nsistp.shared.vlan import (
    CustomVlanRanges,
    validate_vlan,
    validate_vlan_not_in_use,
)
from workflows.shared import create_summary_form


def subscription_description(subscription: SubscriptionModel) -> str:
    """Generate subscription description.

    The suggested pattern is to implement a subscription service that generates a subscription specific
    description, in case that is not present the description will just be set to the product name.
    """
    return f"{subscription.product.name} subscription"


logger = structlog.get_logger(__name__)


def initial_input_form_generator(product_name: str) -> FormGenerator:
    # TODO add additional fields to form if needed

    class CreateNsiStpForm(FormPage):
        model_config = ConfigDict(title=product_name)

        # TODO: check whether this should be removed
        customer_id: CustomerId

        nsistp_settings: Label
        divider_1: Divider

        # TODO: could this be multiple service ports??
        subscription_id: Annotated[
            UUIDstr,
            ports_selector(),
        ]
        vlan: Annotated[
            CustomVlanRanges,
            AfterValidator(validate_vlan),
            AfterValidator(validate_vlan_not_in_use),
        ]

        topology: Topology
        stp_id: StpId
        stp_description: StpDescription | None = None
        is_alias_in: IsAlias | None = None
        is_alias_out: IsAlias | None = None
        expose_in_topology: bool = True
        bandwidth: ServiceSpeed

        @model_validator(mode="after")
        def validate_is_alias_in_out(self) -> "CreateNsiStpForm":
            validate_both_aliases_empty_or_not(self.is_alias_in, self.is_alias_out)
            return self

    user_input = yield CreateNsiStpForm
    user_input_dict = user_input.dict()

    summary_fields = [
        "subscription_id",
        "vlan",
        "topology",
        "stp_id",
        "stp_description",
        "is_alias_in",
        "is_alias_out",
        "expose_in_topology",
        "bandwidth",
    ]
    yield from create_summary_form(user_input_dict, product_name, summary_fields)

    return user_input_dict


@step("Construct Subscription model")
def construct_nsistp_model(
    product: UUIDstr,
    customer_id: UUIDstr,
    subscription_id,
    vlan,
    topology: str,
    stp_id: str,
    stp_description: str | None,
    is_alias_in: str | None,
    is_alias_out: str | None,
    expose_in_topology: bool | None,
    bandwidth: int | None,
) -> State:
    nsistp = NsistpInactive.from_product_id(
        product_id=product,
        customer_id=customer_id,
        status=SubscriptionLifecycle.INITIAL,
    )
    nsistp.nsistp.topology = topology
    nsistp.nsistp.stp_id = stp_id
    nsistp.nsistp.stp_description = stp_description
    nsistp.nsistp.is_alias_in = is_alias_in
    nsistp.nsistp.is_alias_out = is_alias_out
    nsistp.nsistp.expose_in_topology = expose_in_topology
    nsistp.nsistp.bandwidth = bandwidth

    # TODO: change to support CustomVlanRanges
    vlan_int = int(vlan) if not isinstance(vlan, int) else vlan

    nsistp_fill_sap(nsistp, subscription_id, vlan_int)

    nsistp = NsistpProvisioning.from_other_lifecycle(
        nsistp, SubscriptionLifecycle.PROVISIONING
    )
    nsistp.description = subscription_description(nsistp)

    return {
        "subscription": nsistp,
        "subscription_id": nsistp.subscription_id,  # necessary to be able to use older generic step functions
        "subscription_description": nsistp.description,
    }


@step("Create VLANs in IMS (Netbox)")
def ims_create_vlans(subscription: NsistpProvisioning) -> State:
    payload = build_payload(subscription.nsistp.sap, subscription)
    subscription.nsistp.sap.ims_id = netbox.create(payload)

    return {"subscription": subscription, "payloads": [payload]}


additional_steps = begin


@create_workflow(
    "Create nsistp",
    initial_input_form=initial_input_form_generator,
    additional_steps=additional_steps,
)
def create_nsistp() -> StepList:
    return (
        begin
        >> construct_nsistp_model
        >> store_process_subscription(Target.CREATE)
        >> ims_create_vlans
        # TODO add provision step(s)
    )
