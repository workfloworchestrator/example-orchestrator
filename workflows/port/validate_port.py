import structlog
from orchestrator.types import State
from orchestrator.workflow import StepList, begin, step
from orchestrator.workflows.utils import validate_workflow

from products.product_types.port import Port

logger = structlog.get_logger(__name__)


@step("Load initial state")
def load_initial_state_port(subscription: Port) -> State:
    return {
        "subscription": subscription,
    }


@validate_workflow("Validate port")
def validate_port() -> StepList:
    return begin >> load_initial_state_port
