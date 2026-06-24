import os
import shutil
from collections.abc import Generator

import pytest
from playwright.sync_api import Browser, BrowserContext, Page, Playwright


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--orchestrator-ui-url",
        action="store",
        default=os.getenv("ORCH_UI_URL", "http://localhost:3000"),
        help="Base URL for the Orchestrator UI.",
    )
    parser.addoption(
        "--system-browser",
        action="store_true",
        default=os.getenv("PW_SYSTEM_BROWSER", "0") == "1",
        help="Use locally installed Chromium instead of Playwright-managed Chromium.",
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
