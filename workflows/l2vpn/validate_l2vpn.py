import structlog
from orchestrator.types import State
from orchestrator.workflow import StepList, begin, step
from orchestrator.workflows.utils import validate_workflow

from products.product_types.l2vpn import L2vpn

logger = structlog.get_logger(__name__)


@step("Load initial state")
def load_initial_state_l2vpn(subscription: L2vpn) -> State:
    return {
        "subscription": subscription,
    }


@validate_workflow("Validate l2vpn")
def validate_l2vpn() -> StepList:
    return begin >> load_initial_state_l2vpn
