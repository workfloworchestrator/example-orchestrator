# Copyright 2019-2023 SURF.
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
from random import randrange
from typing import TypeAlias, cast

from more_itertools import flatten
from orchestrator.targets import Target
from orchestrator.types import SubscriptionLifecycle
from orchestrator.workflow import StepList, begin, step
from orchestrator.workflows.steps import set_status, store_process_subscription
from orchestrator.workflows.utils import create_workflow
from pydantic import ConfigDict
from pydantic_forms.core import FormPage
from pydantic_forms.types import FormGenerator, State, UUIDstr
from pydantic_forms.validators import Choice

from products.product_blocks.sap import SAPBlockInactive
from products.product_types.l2vpn import L2vpn, L2vpnInactive, L2vpnProvisioning
from products.product_types.port import Port
from products.services.description import description
from products.services.netbox.netbox import build_payload
from products.services.netbox.payload.sap import build_sap_vlan_group_payload
from services import netbox
from workflows.l2vpn.shared.forms import ports_selector
from workflows.nsistp.shared.shared import OrchestratorVlanRanges
from workflows.shared import AllowedNumberOfL2vpnPorts


def initial_input_form_generator(product_name: str) -> FormGenerator:
    class CreateL2vpnForm(FormPage):
        model_config = ConfigDict(title=product_name)

        number_of_ports: AllowedNumberOfL2vpnPorts
        speed: int
        speed_policer: bool | None = False

    user_input = yield CreateL2vpnForm
    user_input_dict = user_input.model_dump()
    PortsChoiceList: TypeAlias = cast(
        type[Choice], ports_selector(AllowedNumberOfL2vpnPorts(user_input_dict["number_of_ports"]))  # noqa: F821
    )

    class SelectPortsForm(FormPage):
        model_config = ConfigDict(title=product_name)

        ports: PortsChoiceList
        vlan: OrchestratorVlanRanges

    select_ports = yield SelectPortsForm
    select_ports_dict = select_ports.model_dump()
    ports = [str(item) for item in select_ports_dict["ports"]]

    return user_input_dict | select_ports_dict | {"ports": ports}


@step("Construct Subscription model")
def construct_l2vpn_model(
    product: UUIDstr,
    # organisation: UUIDstr,
    ports: list[UUIDstr],
    speed: int,
    speed_policer: bool,
    vlan: OrchestratorVlanRanges,
) -> State:
    subscription = L2vpnInactive.from_product_id(
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

    subscription = L2vpnProvisioning.from_other_lifecycle(subscription, SubscriptionLifecycle.PROVISIONING)
    subscription.description = description(subscription)

    return {
        "subscription": subscription,
        "subscription_id": subscription.subscription_id,  # necessary to be able to use older generic step functions
        "subscription_description": subscription.description,
    }


@step("Create VLANs in IMS")
def ims_create_vlans(subscription: L2vpnProvisioning) -> State:
    group_payloads = []
    vlan_payloads = []
    for sap in subscription.virtual_circuit.saps:
        group_payload = build_sap_vlan_group_payload(sap, subscription)
        sap.ims_id = netbox.create(group_payload)
        group_payloads = group_payloads + [group_payload]

        vlan_payloads += build_payload(sap, subscription)

    for payload in vlan_payloads:
        netbox.create(payload)

    return {"subscription": subscription, "vlan_group_payloads": group_payloads, "vlan_payloads": vlan_payloads}


@step("Create L2VPN in IMS")
def ims_create_l2vpn(subscription: L2vpnProvisioning) -> State:
    payload = build_payload(subscription.virtual_circuit, subscription)
    subscription.virtual_circuit.ims_id = netbox.create(payload)

    return {"subscription": subscription, "payload": payload}


@step("Create L2VPN terminations in IMS")
def ims_create_l2vpn_terminations(subscription: L2vpnProvisioning) -> State:
    l2vpn = netbox.get_l2vpn(id=subscription.virtual_circuit.ims_id)

    def create_sap_payloads(sap) -> list[netbox.L2vpnTerminationPayload]:
        vlans = netbox.get_vlans(group_id=sap.ims_id)
        return [netbox.L2vpnTerminationPayload(l2vpn=l2vpn.id, assigned_object_id=vlan.id) for vlan in vlans]

    payloads = list(flatten([create_sap_payloads(sap) for sap in subscription.virtual_circuit.saps]))
    for payload in payloads:
        netbox.create(payload)

    return {"payloads": payloads}


@step("Update VLANs on connected ports in IMS")
def update_vlans_on_ports(subscription: L2vpn) -> State:
    """By re-provisioning the connected ports,
    the VLANs from active SAPs will be provisioned in IMS or removed otherwise.
    """
    payloads = []
    for sap in subscription.virtual_circuit.saps:
        port_subscription = Port.from_subscription(sap.port.owner_subscription_id)
        payload = build_payload(port_subscription.port, port_subscription)
        netbox.update(payload, id=port_subscription.port.ims_id)
        payloads.append(payload)

    return {"payloads": payloads}


@step("Provision L2VPN in NRM")
def provision_l2vpn_in_nrm(subscription: L2vpnProvisioning) -> State:
    """Dummy step that only creates a random NRM ID, replace with actual call to NRM."""
    subscription.virtual_circuit.nrm_id = randrange(2**16)
    return {"subscription": subscription}


@create_workflow("Create l2vpn", initial_input_form=initial_input_form_generator)
def create_l2vpn() -> StepList:
    return (
        begin
        >> construct_l2vpn_model
        >> store_process_subscription(Target.CREATE)
        >> ims_create_vlans
        >> ims_create_l2vpn
        >> ims_create_l2vpn_terminations
        >> provision_l2vpn_in_nrm
        >> set_status(SubscriptionLifecycle.ACTIVE)
        >> update_vlans_on_ports
    )
