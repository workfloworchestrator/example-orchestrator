import structlog
from orchestrator.types import State
from orchestrator.workflow import StepList, begin, step
from orchestrator.workflows.utils import validate_workflow

from products.product_types.core_link import CoreLink

logger = structlog.get_logger(__name__)


@step("Load initial state")
def load_initial_state_core_link(subscription: CoreLink) -> State:
    return {
        "subscription": subscription,
    }


@validate_workflow("Validate core_link")
def validate_core_link() -> StepList:
    return begin >> load_initial_state_core_link
