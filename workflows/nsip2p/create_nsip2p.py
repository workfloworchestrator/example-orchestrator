# Copyright 2019-2026 SURF, Geant.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import uuid
from functools import partial
from nwastdlib.vlans import VlanRanges
from orchestrator.targets import Target
from orchestrator.types import SubscriptionLifecycle
from orchestrator.workflow import StepList, begin, step
from orchestrator.workflows.steps import store_process_subscription
from orchestrator.workflows.utils import create_workflow
from pydantic import AfterValidator, ConfigDict
from pydantic_forms.core import FormPage
from pydantic_forms.types import FormGenerator, State, UUIDstr
from pydantic_forms.validators import Choice
from typing import Annotated, TypeAlias, cast

from products.product_blocks.sap import SAPBlockInactive
from products.product_types.nsip2p import Nsip2pInactive, Nsip2pProvisioning
from products.product_types.port import Port
from products.services.description import description
from workflows.l2vpn.create_l2vpn import ims_create_vlans, ims_create_l2vpn, ims_create_l2vpn_terminations, update_vlans_on_ports, provision_l2vpn_in_nrm
from workflows.l2vpn.shared.forms import ports_selector
from workflows.shared import validate_vlan, validate_vlan_reserved_by_product, validate_vlan_not_used_by_product

# Only allow exactly 2 ports for NSIP2P
AllowedNumberOfNsip2pPorts = Annotated[int, ConfigDict(ge=2, le=2, title="Allowed number of NSIP2P ports")]


def initial_input_form_generator(product_name: str) -> FormGenerator:
    class CreateNsip2pForm(FormPage):
        model_config = ConfigDict(title=product_name)
        number_of_ports: AllowedNumberOfNsip2pPorts = 2  # Always 2
        speed: int
        speed_policer: bool | None = False

    user_input = yield CreateNsip2pForm
    user_input_dict = user_input.model_dump()
    PortsChoiceList: TypeAlias = cast(
        type[Choice], ports_selector(2)
    )

    # Validation: VLAN must be reserved by NSISTP and not used by another NSIP2P
    _validate_vlan_reserved_by_nsistp = partial(
        validate_vlan_reserved_by_product,
        port_field_name="ports",
        product_type="Nsistp",
    )
    _validate_vlan_not_used_by_nsip2p = partial(
        validate_vlan_not_used_by_product,
        port_field_name="ports",
        product_type="Nsip2p",
    )

    class SelectPortsForm(FormPage):
        model_config = ConfigDict(title=product_name)
        ports: PortsChoiceList
        # Only one VLAN per port, but stored as VlanRanges for compatibility
        vlan: Annotated[
            VlanRanges,
            AfterValidator(validate_vlan),
            AfterValidator(_validate_vlan_reserved_by_nsistp),
            AfterValidator(_validate_vlan_not_used_by_nsip2p),
        ] = VlanRanges(0)

    select_ports = yield SelectPortsForm
    select_ports_dict = select_ports.model_dump()
    ports = [str(item) for item in select_ports_dict["ports"]]

    # Enforce exactly 2 ports
    if len(ports) != 2:
        raise ValueError("NSIP2P must have exactly 2 ports selected.")
    # Enforce only one VLAN per port
    if not select_ports_dict["vlan"].is_single_vlan:
        raise ValueError("Only one VLAN may be selected per port for NSIP2P.")

    return user_input_dict | select_ports_dict | {"ports": ports}


@step("Construct NSIP2P Subscription model")
def construct_nsip2p_model(
    product: UUIDstr,
    ports: list[UUIDstr],
    speed: int,
    speed_policer: bool,
    vlan: VlanRanges,
) -> State:
    # Enforce exactly 2 SAPs
    if len(ports) != 2:
        raise ValueError("NSIP2P must have exactly 2 SAPs (ports)")
    # Enforce only one VLAN per port
    if not vlan.is_single_vlan:
        raise ValueError("Only one VLAN may be selected per port for NSIP2P.")
    subscription = Nsip2pInactive.from_product_id(
        product_id=product,
        customer_id=str(uuid.uuid4()),
        status=SubscriptionLifecycle.INITIAL,
    )
    subscription.virtual_circuit.speed = speed
    subscription.virtual_circuit.speed_policer = speed_policer

    def to_sap(port: UUIDstr) -> SAPBlockInactive:
        port_subscription = Port.from_subscription(port)
        sap = SAPBlockInactive.new(subscription_id=subscription.subscription_id)
        sap.port = port_subscription.port
        sap.vlan = vlan
        return sap

    subscription.virtual_circuit.saps = [to_sap(port) for port in ports]
    subscription = Nsip2pProvisioning.from_other_lifecycle(subscription, SubscriptionLifecycle.PROVISIONING)
    subscription.description = description(subscription)
    return {
        "subscription": subscription,
        "subscription_id": subscription.subscription_id,
        "subscription_description": subscription.description,
    }

# Provisioning steps: reuse/adapt L2VPN steps, but only for 2 SAPs and single VLAN per port
# If further customization is needed for NSIP2P, add/override steps here

@create_workflow("Create NSIP2P", initial_input_form=initial_input_form_generator)
def create_nsip2p() -> StepList:
    return (
        begin
        >> construct_nsip2p_model
        >> store_process_subscription(Target.CREATE)
        >> ims_create_vlans
        >> ims_create_l2vpn
        >> ims_create_l2vpn_terminations
        >> provision_l2vpn_in_nrm
        >> update_vlans_on_ports
    )
