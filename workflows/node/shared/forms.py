from orchestrator.types import State
from surf.utils.exceptions import FieldValueError


def validate_something(foo: str | None, values: State) -> str | None:
    if foo:
        message = "TODO: implement this!"
        raise FieldValueError(message)

    return foo
