# End-to-end testing

This directory documents the Playwright-based end-to-end test setup for the example orchestrator.

The tests live in `tests/e2e` and use `pytest-playwright` with the synchronous Playwright API.

## Local setup

Start the local application stack first (see the README for details):

Wait until the relevant services are up:

```text
orchestrator      healthy
orchestrator-ui   up
```

The local defaults are:

```text
Orchestrator UI:       http://localhost:3000
Orchestrator backend:  http://localhost:8080
NetBox:                http://localhost:8000
```

Install/update the Python development environment with `uv`:

```bash
uv sync --group dev
```

Install Playwright-managed browsers when your operating system supports them:

```bash
uv run python -m playwright install chromium
```

This is the preferred local setup on macOS, Ubuntu, Windows, and most developer environments where Playwright can install browsers and their dependencies normally.

Fedora can be different: Playwright can install browser binaries, but it does not always install all browser system dependencies automatically. For Fedora headed runs, use a system browser instead. Either Chromium or Google Chrome works:

```bash
sudo dnf install chromium
```

The test fixture auto-detects `chromium`, `chromium-browser`, and `google-chrome` when `--system-browser` is used.

## Running tests locally

Run headless with the default Playwright browser setup:

```bash
uv run python -m pytest tests/e2e
```

Run headed with Playwright-managed browsers, typically on macOS, Ubuntu, and Windows:

```bash
uv run python -m pytest tests/e2e --headed
```

Run headed against a locally installed system browser, typically on Fedora:

```bash
uv run python -m pytest tests/e2e --headed --system-browser
```

Slow down headed runs while developing tests:

```bash
uv run python -m pytest tests/e2e --headed --slowmo 250
```

or, on Fedora/system-browser mode:

```bash
uv run python -m pytest tests/e2e --headed --system-browser --slowmo 250
```

The default UI URL is `http://localhost:3000`, so local development does not need any URL option. To override it:

```bash
uv run python -m pytest tests/e2e --orchestrator-ui-url http://localhost:3000
```

or:

```bash
ORCH_UI_URL=http://localhost:3000 uv run python -m pytest tests/e2e
```

## Browser strategy

The intended modes are:

| Mode | Command style | Browser source | Use case |
|---|---|---|---|
| Local headless | `pytest tests/e2e` | Playwright-managed browser | Fast local smoke checks on macOS/Ubuntu/Windows and compatible environments |
| Local headed | `pytest tests/e2e --headed` | Playwright-managed browser | Visual debugging on macOS/Ubuntu/Windows and compatible environments |
| Fedora headed | `pytest tests/e2e --headed --system-browser` | Fedora system Chromium/Chrome | Visual debugging when Playwright-managed browser dependencies are not available on Fedora |
| CI headless | `uv run pytest tests/e2e/` | Playwright-managed browser | Reproducible automated runs in GitHub Actions |

The `--system-browser` option is mainly for Fedora and other developer machines where a system browser works easier than Playwright-managed browser binaries. Developers on macOS, Ubuntu, and Windows should usually install Playwright browsers and run without `--system-browser`.
