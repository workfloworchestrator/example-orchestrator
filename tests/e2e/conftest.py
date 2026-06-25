import os
import shutil
import time
from collections.abc import Generator

import pytest
import requests
from playwright.sync_api import Browser, BrowserContext, Page, Playwright

_BOOTSTRAP_TASK_NAME = "task_bootstrap_netbox"
_POLL_INTERVAL = 2  # seconds
_POLL_TIMEOUT = 120  # seconds


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--orchestrator-ui-url",
        action="store",
        default=os.getenv("ORCH_UI_URL", "http://localhost:3000"),
        help="Base URL for the Orchestrator UI.",
    )
    parser.addoption(
        "--orchestrator-api-url",
        action="store",
        default=os.getenv("ORCH_API_URL", "http://localhost:8080/api/v1"),
        help="Base URL for the Orchestrator backend API.",
    )
    parser.addoption(
        "--system-browser",
        action="store_true",
        default=os.getenv("PW_SYSTEM_BROWSER", "0") == "1",
        help="Use locally installed Chromium instead of Playwright-managed Chromium.",
    )


@pytest.fixture(scope="session")
def orchestrator_api_url(pytestconfig: pytest.Config) -> str:
    return pytestconfig.getoption("--orchestrator-api-url").rstrip("/")


def _is_bootstrap_done(api_url: str) -> bool:
    """Return True if a completed bootstrap task process already exists.

    The process list endpoint accepts filters as a single comma-separated
    ``filter`` query param in ``field,value[,field2,value2,...]`` format.
    """
    response = requests.get(
        f"{api_url}/processes",
        params={"filter": f"workflow_name,{_BOOTSTRAP_TASK_NAME},last_status,completed"},
        timeout=10,
    )
    response.raise_for_status()
    # Any completed process in the list means bootstrap already ran.
    return len(response.json()) > 0


def _trigger_bootstrap(api_url: str) -> str:
    """Start the bootstrap task and return the new process ID."""
    response = requests.post(
        f"{api_url}/processes/{_BOOTSTRAP_TASK_NAME}",
        json=[{}],
        timeout=10,
    )
    response.raise_for_status()
    return response.json()["id"]


def _wait_for_process(api_url: str, process_id: str) -> str:
    """Poll until the process reaches a terminal state; return the final status."""
    deadline = time.monotonic() + _POLL_TIMEOUT
    while time.monotonic() < deadline:
        response = requests.get(f"{api_url}/processes/{process_id}", timeout=10)
        response.raise_for_status()
        status = response.json()["last_status"]
        if status not in ("created", "running", "suspended"):
            return status
        time.sleep(_POLL_INTERVAL)
    raise TimeoutError(f"Bootstrap task {process_id} did not complete within {_POLL_TIMEOUT}s")


@pytest.fixture(scope="session", autouse=True)
def netbox_bootstrapped(orchestrator_api_url: str) -> None:
    """Ensure Netbox is bootstrapped before any test runs.

    Checks whether a completed bootstrap process already exists. If not,
    triggers the task and waits for it to finish. Fails the session if the
    task ends in any non-completed terminal state.
    """
    if _is_bootstrap_done(orchestrator_api_url):
        return

    process_id = _trigger_bootstrap(orchestrator_api_url)
    final_status = _wait_for_process(orchestrator_api_url, process_id)
    if final_status != "completed":
        pytest.fail(
            f"Netbox bootstrap task (process {process_id}) ended with status '{final_status}'. "
            "Check the orchestrator logs for details."
        )


@pytest.fixture(scope="session")
def browser(
    playwright: Playwright,
    browser_name: str,
    browser_channel: str | None,
    browser_type_launch_args: dict,
    pytestconfig: pytest.Config,
) -> Generator[Browser, None, None]:
    launch_options = dict(browser_type_launch_args)

    if pytestconfig.getoption("--system-browser") and browser_name == "chromium":
        if browser_channel:
            launch_options["channel"] = browser_channel
        elif shutil.which("chromium") or shutil.which("chromium-browser"):
            launch_options["channel"] = "chromium"
        elif shutil.which("google-chrome"):
            launch_options["channel"] = "chrome"
        else:
            pytest.fail("--system-browser requires chromium, chromium-browser, or google-chrome on PATH")

    browser = playwright[browser_name].launch(**launch_options)
    yield browser
    browser.close()


@pytest.fixture(scope="function")
def context(browser: Browser) -> Generator[BrowserContext, None, None]:
    context = browser.new_context(
        viewport={"width": 1280, "height": 720},
        locale="en-US",
    )
    yield context
    context.close()


@pytest.fixture(scope="function")
def page(context: BrowserContext) -> Generator[Page, None, None]:
    page = context.new_page()
    page.set_default_timeout(10_000)
    yield page
    page.close()


@pytest.fixture(scope="session")
def base_url(pytestconfig: pytest.Config) -> str:
    return pytestconfig.getoption("--orchestrator-ui-url").rstrip("/")
