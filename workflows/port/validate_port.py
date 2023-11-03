from pprint import pformat

from deepdiff import DeepDiff
from orchestrator.types import State
from orchestrator.workflow import StepList, begin, step
from orchestrator.workflows.utils import validate_workflow

from products.product_types.port import Port
from products.services.netbox.netbox import build_payload
from services import netbox


def pretty_print_deepdiff(diff: DeepDiff) -> str:
    return pformat(diff.to_dict(), indent=2, compact=False)


@step("validate port in IMS")
def validate_port_in_ims(subscription: Port) -> State:
    interface = netbox.get_interface(id=subscription.port.ims_id)
    actual = netbox.InterfacePayload(
        device=interface.device.id,
        name=interface.name,
        type=interface.type.value,
        description=interface.description,
        enabled=interface.enabled,
        speed=interface.speed,
    )
    expected = build_payload(subscription.port, subscription)
    if ims_diff := DeepDiff(actual, expected, ignore_order=False):
        raise AssertionError("Found difference in IMS:\nActual => Expected\n" + pretty_print_deepdiff(ims_diff))

    return {"port_in_sync_with_ims": True}


@validate_workflow("Validate port")
def validate_port() -> StepList:
    return begin >> validate_port_in_ims
