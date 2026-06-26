from typing import Annotated, Any, TypeAlias, cast

from annotated_types import Ge, Le
from orchestrator.core import workflow
from orchestrator.core.config.assignee import Assignee
from orchestrator.core.forms import FormPage
from orchestrator.core.forms.validators import Divider, Label
from orchestrator.core.targets import Target
from orchestrator.core.utils.errors import ProcessFailureError
from orchestrator.core.workflow import StepList, callback_step, conditional, done, init, inputstep, step
from pydantic import AfterValidator, ConfigDict, model_validator

from pydantic_forms.types import FormGenerator, State
from pydantic_forms.validators import Choice, LongText, callout, choice_list, read_only_field
from pydantic_forms.validators.components.callout import CalloutMessageType

ShowcaseInteger = Annotated[int, Ge(1), Le(10)]

ShowcaseCallout = callout(
    header="Showcase",
    message="This task exercises generic form components and process states.",
    message_type=CalloutMessageType.PRIMARY,
)


def must_not_be_reserved(value: str) -> str:
    if value.casefold() == "reserved":
        raise ValueError("The value 'reserved' is intentionally rejected by the showcase task")
    return value


ValidatedText = Annotated[str, AfterValidator(must_not_be_reserved)]


def single_choice_selector() -> type[Choice]:
    choices = {
        "alpha": "Alpha",
        "beta": "Beta",
        "gamma": "Gamma",
    }
    return Choice("E2ESingleChoiceEnum", zip(choices.keys(), choices.items()))  # type: ignore


def multi_choice_selector() -> type[list[Choice]]:
    choices = {
        "one": "One",
        "two": "Two",
        "three": "Three",
    }
    return choice_list(
        Choice("E2EMultiChoiceEnum", zip(choices.keys(), choices.items())),  # type: ignore
        min_items=1,
        max_items=3,
        unique_items=True,
    )


def initial_input_form_generator() -> FormGenerator:
    SingleChoice: TypeAlias = cast(type[Choice], single_choice_selector())
    MultiChoice: TypeAlias = cast(type[list[Choice]], multi_choice_selector())

    class E2EShowcaseForm(FormPage):
        model_config = ConfigDict(title="Component Showcase")

        callout_1: ShowcaseCallout = None  # type: ignore[valid-type]
        general_settings: Label

        text_value: ValidatedText
        optional_text: str | None = None
        long_text: LongText | None = None
        read_only_value: read_only_field("This value is read-only")  # type: ignore[valid-type]

        divider_1: Divider

        integer_value: int
        constrained_integer: ShowcaseInteger
        boolean_value: bool = False
        single_choice: SingleChoice
        multi_choice: MultiChoice

        divider_2: Divider

        run_conditional_step: bool = True
        show_suspended_step: bool = False
        wait_for_callback: bool = False
        fail_on_purpose: bool = False

        @model_validator(mode="after")
        def validate_process_flags(self) -> "E2EShowcaseForm":
            if self.wait_for_callback and self.fail_on_purpose:
                raise ValueError("Choose either wait_for_callback or fail_on_purpose, not both")
            return self

    user_input = yield E2EShowcaseForm
    user_input_dict = user_input.model_dump()

    class E2EShowcaseSummary(FormPage):
        model_config = ConfigDict(title="Component Showcase Summary")

        submitted_values: LongText = "\n".join(f"{key}: {value}" for key, value in sorted(user_input_dict.items()))
        continue_task: bool = True

    summary_input = yield E2EShowcaseSummary
    return user_input_dict | summary_input.model_dump()


@step("Record initial input")
def record_initial_input(
    text_value: str,
    optional_text: str | None,
    integer_value: int,
    constrained_integer: int,
    boolean_value: bool,
    single_choice: str,
    multi_choice: list[str],
    continue_task: bool,
) -> State:
    return {
        "e2e_initial_input": {
            "text_value": text_value,
            "optional_text": optional_text,
            "integer_value": integer_value,
            "constrained_integer": constrained_integer,
            "boolean_value": boolean_value,
            "single_choice": single_choice,
            "multi_choice": multi_choice,
            "continue_task": continue_task,
        }
    }


@step("Conditional step")
def run_conditional_step() -> State:
    return {"e2e_conditional_step_ran": True}


@inputstep("Suspended confirmation", assignee=Assignee("SYSTEM"))
def show_suspended_form(state: State) -> FormGenerator:
    class E2ESuspendedForm(FormPage):
        model_config = ConfigDict(title="Suspended Confirmation")

        suspended_label: Label
        confirmation_text: str
        confirmation_details: LongText | None = None
        confirmed: bool = False

    user_input = yield E2ESuspendedForm
    return state | {"e2e_suspended_input": user_input.model_dump()}


@step("Callback action")
def request_callback(callback_route: str) -> State:
    return {"e2e_callback_route": callback_route}


@step("Callback validation")
def validate_callback(callback_result: dict[str, Any]) -> State:
    return {"e2e_callback_result": callback_result}


@step("Deliberate failure")
def fail_when_requested(fail_on_purpose: bool) -> State:
    if fail_on_purpose:
        raise ProcessFailureError(
            message="Deliberate failure",
            details={"reason": "fail_on_purpose was selected"},
        )
    return {"e2e_failure_step_checked": True}


run_when_requested = conditional(lambda state: state.get("run_conditional_step") is True)
suspend_when_requested = conditional(lambda state: state.get("show_suspended_step") is True)
callback_when_requested = conditional(lambda state: state.get("wait_for_callback") is True)


@workflow(initial_input_form=initial_input_form_generator, target=Target.SYSTEM)
def task_showcase() -> StepList:
    return (
        init
        >> record_initial_input
        >> run_when_requested(run_conditional_step)
        >> suspend_when_requested(show_suspended_form)
        >> callback_when_requested(
            callback_step(
                name="Callback step",
                action_step=request_callback,
                validate_step=validate_callback,
            )
        )
        >> fail_when_requested
        >> done
    )
