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
from random import randrange

from more_itertools import unzip
from nwastdlib.vlans import VlanRanges
from orchestrator.targets import Target
from orchestrator.types import SubscriptionLifecycle
from orchestrator.workflow import StepList, begin, step
from orchestrator.workflows.steps import store_process_subscription
from orchestrator.workflows.utils import create_workflow
from pydantic import AfterValidator, ConfigDict
from pydantic_core.core_schema import ValidationInfo
from pydantic_forms.core import FormPage
from pydantic_forms.types import FormGenerator, State, UUIDstr
from pydantic_forms.validators import Choice
from typing import Annotated, TypeAlias, cast

from products.product_blocks.sap import SAPBlockInactive
from products.product_types.nsip2p import Nsip2pInactive, Nsip2pProvisioning
from products.product_types.port import Port
from products.services.description import description
from workflows.l2vpn.shared.forms import ports_selector
from workflows.shared import validate_vlan, validate_vlan_reserved_by_product, validate_vlan_not_used_by_product
from workflows.shared import validate_vlan, validate_vlan_reserved_by_product, validate_vlan_not_used_by_product, \
    update_ports_in_netbox, create_saps_in_netbox, create_l2vpn_in_netbox, create_l2vpn_terminations_in_netbox


def initial_input_form_generator(product_name: str) -> FormGenerator:
    class CreateNsip2pForm(FormPage):
        model_config = ConfigDict(title=product_name)

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


@step("Create VLANs in IMS")
def ims_create_vlans(subscription: Nsip2pProvisioning) -> State:
    saps = subscription.virtual_circuit.saps

    sap_payloads = create_saps_in_netbox(saps, subscription)
    vlan_group_payloads, vlan_payloads = unzip(sap_payloads)

    return {
        "subscription": subscription,
        "vlan_group_payloads": list(vlan_group_payloads),
        "vlan_payloads": list(vlan_payloads),
    }


@step("Create NSIP2P in IMS")
def ims_create_nsip2p(subscription: Nsip2pProvisioning) -> State:
    vc = subscription.virtual_circuit

    vc.ims_id, payload = create_l2vpn_in_netbox(vc, subscription)

    return {"subscription": subscription, "payload": payload}


@step("Create NSIP2P terminations in IMS")
def ims_create_nsip2p_terminations(subscription: Nsip2pProvisioning) -> State:
    vc = subscription.virtual_circuit

    payloads = create_l2vpn_terminations_in_netbox(vc)

    return {"payloads": payloads}


@step("Provision NSIP2P in NRM")
def provision_nsip2p_in_nrm(subscription: Nsip2pProvisioning) -> State:
    """Dummy step that only creates a random NRM ID, replace with actual call to NRM."""
    subscription.virtual_circuit.nrm_id = randrange(2**16)
    return {"subscription": subscription}


@step("Update VLANs on connected ports in IMS")
def update_vlans_on_ports(subscription: Nsip2pProvisioning) -> State:
    saps = subscription.virtual_circuit.saps
    payloads = update_ports_in_netbox(saps)
    return {"payloads": payloads}

# Provisioning steps: reuse/adapt L2VPN steps, but only for 2 SAPs and single VLAN per port
# If further customization is needed for NSIP2P, add/override steps here

@create_workflow("Create NSIP2P", initial_input_form=initial_input_form_generator)
def create_nsip2p() -> StepList:
    return (
        begin
        >> construct_nsip2p_model
        >> store_process_subscription(Target.CREATE)
        >> ims_create_vlans
        >> ims_create_nsip2p
        >> ims_create_nsip2p_terminations
        >> provision_nsip2p_in_nrm
        >> update_vlans_on_ports
    )
