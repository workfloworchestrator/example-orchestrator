from orchestrator.types import State
from orchestrator.workflow import step

from products.product_types.node import NodeProvisioning
from products.services.netbox.netbox import build_payload
from services import netbox


@step("Update node in IMS")
def update_node_in_imdb(subscription: NodeProvisioning) -> State:
    """Update node in IMDB"""
    payload = build_payload(subscription.node, subscription)
    netbox.update(payload, id=subscription.node.ims_id)
    return {"subscription": subscription, "payload": payload.dict()}
