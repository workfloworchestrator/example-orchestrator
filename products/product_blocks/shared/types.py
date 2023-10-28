from enum import Enum


class EnumBase(str, Enum):
    @classmethod
    def list(cls):
        return [member.value for member in cls]


class NodeStatus(EnumBase):
    """Operational status of a node."""

    Offline = "offline"
    Active = "active"
    Planned = "planned"
    Staged = "staged"
    Failed = "failed"
    Inventory = "inventory"
    Decommissioning = "decommissioning"
