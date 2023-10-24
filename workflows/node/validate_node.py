import structlog
from orchestrator.types import State
from orchestrator.workflow import StepList, begin, step
from orchestrator.workflows.utils import validate_workflow

from products.product_types.node import Node

logger = structlog.get_logger(__name__)


@step("Load initial state")
def load_initial_state_node(subscription: Node) -> State:
    return {
        "subscription": subscription,
    }


@validate_workflow("Validate node")
def validate_node() -> StepList:
    return begin >> load_initial_state_node
