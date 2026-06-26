import re

from playwright.sync_api import Page, expect

SHOWCASE_TITLE = "Component Showcase"


### Helper functions


def open_showcase_task(page: Page, base_url: str) -> None:
    page.goto(f"{base_url}/tasks")
    page.get_by_role("button", name=re.compile("New task")).click()
    page.get_by_role("option", name=re.compile(SHOWCASE_TITLE)).click()
    expect(page).to_have_url(re.compile(r"/tasks/new/task_showcase$"))
    expect(page.get_by_test_id("pydantic-form-header")).to_have_text(SHOWCASE_TITLE)


def fill_showcase_form(
    page: Page,
    *,
    text_value: str = "hello showcase",
    run_conditional_step: bool = True,
    show_suspended_step: bool = False,
    fail_on_purpose: bool = False,
) -> None:
    page.get_by_test_id("text_value").fill(text_value)
    page.get_by_test_id("optional_text").fill("optional showcase")
    page.get_by_test_id("long_text").fill("long showcase details")
    page.get_by_test_id("integer_value").fill("4")
    page.get_by_test_id("constrained_integer").fill("5")
    page.get_by_test_id("boolean_value").check()
    select_combo_option(page, "single_choice.search-input", "Beta")
    select_combo_option(page, "multi_choice.0.search-input", "One")

    if not run_conditional_step:
        page.get_by_test_id("run_conditional_step").uncheck()
    if show_suspended_step:
        page.get_by_test_id("show_suspended_step").check()
    if fail_on_purpose:
        page.get_by_test_id("fail_on_purpose").check()


def select_combo_option(page: Page, test_id: str, value: str) -> None:
    combo = page.get_by_test_id(test_id)
    combo.click()
    combo.fill(value)
    page.keyboard.press("Enter")


def submit_initial_and_summary(page: Page) -> None:
    page.get_by_test_id("button-submit-form-submit").click()
    expect(page.get_by_role("heading", name="Component Showcase Summary")).to_be_visible()
    expect(page.get_by_test_id("submitted_values")).to_contain_text("text_value: hello showcase")
    expect(page.get_by_test_id("submitted_values")).to_contain_text("single_choice: beta")
    page.get_by_test_id("button-submit-form-submit").click()


def expect_process_status(page: Page, status: str) -> None:
    expect(page.get_by_text(status, exact=True)).to_be_visible(timeout=30_000)


### Tests


def test_showcase_task_is_listed(page: Page, base_url: str) -> None:
    """Verify the showcase task is available from the New task dropdown."""
    page.goto(f"{base_url}/tasks")

    page.get_by_role("button", name=re.compile("New task")).click()

    expect(page.get_by_role("option", name=re.compile(SHOWCASE_TITLE))).to_be_visible()


def test_showcase_happy_path_completes(page: Page, base_url: str) -> None:
    """Submit valid showcase input and verify the task completes with expected steps."""
    open_showcase_task(page, base_url)
    fill_showcase_form(page)

    submit_initial_and_summary(page)

    expect(page).to_have_url(re.compile(r"/tasks/[0-9a-f-]+$"), timeout=30_000)
    expect_process_status(page, "COMPLETED")
    expect(page.get_by_text("Record initial input").first).to_be_visible()
    expect(page.get_by_text("Conditional step").first).to_be_visible()


def test_showcase_validation_errors_keep_user_on_form(page: Page, base_url: str) -> None:
    """Enter invalid values, assert validation is shown, then correct and continue."""
    open_showcase_task(page, base_url)
    fill_showcase_form(page, text_value="reserved")
    page.get_by_test_id("constrained_integer").fill("11")

    page.get_by_test_id("button-submit-form-submit").click()

    expect(page).to_have_url(re.compile(r"/tasks/new/task_showcase$"))
    expect(page.get_by_text("Component Showcase Summary")).not_to_be_visible()
    expect(page.get_by_text(re.compile("reserved|less than or equal|10", re.IGNORECASE))).to_be_visible()

    page.get_by_test_id("text_value").fill("corrected showcase")
    page.get_by_test_id("constrained_integer").fill("5")
    page.get_by_test_id("button-submit-form-submit").click()
    expect(page.get_by_role("heading", name="Component Showcase Summary")).to_be_visible()


def test_showcase_conditional_step_can_be_skipped(page: Page, base_url: str) -> None:
    """Disable the conditional flag and verify the conditional step is skipped."""
    open_showcase_task(page, base_url)
    fill_showcase_form(page, run_conditional_step=False)

    submit_initial_and_summary(page)

    expect_process_status(page, "COMPLETED")
    conditional_step = page.get_by_text("Conditional step").locator("xpath=ancestor::*[contains(., 'skipped')][1]")
    expect(conditional_step).to_contain_text("skipped")


def test_showcase_suspended_step_can_be_resumed(page: Page, base_url: str) -> None:
    """Trigger the suspended input step, submit its resume form, and verify completion."""
    open_showcase_task(page, base_url)
    fill_showcase_form(page, show_suspended_step=True)

    submit_initial_and_summary(page)

    expect(page.get_by_role("heading", name="Suspended Confirmation")).to_be_visible(timeout=30_000)
    expect_process_status(page, "SUSPENDED")
    page.get_by_test_id("confirmation_text").fill("resume showcase")
    page.get_by_test_id("confirmation_details").fill("resume details")
    page.get_by_test_id("confirmed").check()
    page.get_by_test_id("button-submit-form-submit").click()

    expect_process_status(page, "COMPLETED")
    expect(page.get_by_text("Suspended confirmation").first).to_be_visible()


def test_showcase_deliberate_failure_is_rendered(page: Page, base_url: str) -> None:
    """Request the failure path and verify the failed state and traceback control render."""
    open_showcase_task(page, base_url)
    fill_showcase_form(page, fail_on_purpose=True)

    submit_initial_and_summary(page)

    expect_process_status(page, "FAILED")
    expect(page.get_by_text("Deliberate failure").first).to_be_visible()
    expect(page.get_by_role("button", name="Show traceback")).to_be_visible()
