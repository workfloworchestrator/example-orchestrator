# workflows/nsistp/validate_nsistp.py
import structlog
from orchestrator.workflow import StepList, begin, step
from orchestrator.workflows.utils import validate_workflow
from pydantic_forms.types import State

from products.product_types.nsistp import Nsistp

logger = structlog.get_logger(__name__)


@step("Load initial state")
def load_initial_state_nsistp(subscription: Nsistp) -> State:
    return {
        "subscription": subscription,
    }


@validate_workflow("Validate nsistp")
def validate_nsistp() -> StepList:
    return begin >> load_initial_state_nsistp
