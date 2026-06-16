from orchestrator.core.db import ALL_DB_MODELS
from orchestrator.core.db.database import BaseModel as DbBaseModel

from db.models import (
    CustomerTable,
)

__all__ = [
    "CustomerTable",
]

ALL_DB_MODELS_EXAMPLE_ORCHESTRATOR: list[type[DbBaseModel]] = [
    CustomerTable,
]

ALL_DB_MODELS.extend(ALL_DB_MODELS_EXAMPLE_ORCHESTRATOR)
