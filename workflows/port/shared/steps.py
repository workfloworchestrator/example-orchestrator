from orchestrator.types import State
from orchestrator.workflow import step

from products.product_types.port import PortProvisioning
from products.services.netbox.netbox import build_payload
from services import netbox


@step("Update port in IMS")
def update_port_in_ims(subscription: PortProvisioning) -> State:
    """Update port in IMDB"""
    payload = build_payload(subscription.port, subscription)
    netbox.update(payload, id=subscription.port.ims_id)
    return {"subscription": subscription, "payload": payload.dict()}
