# End-to-end testing

This directory documents the Playwright-based end-to-end test setup for the example orchestrator.

The tests live in `tests/e2e` and use `pytest-playwright` with the synchronous Playwright API.

## Local setup

Start the local application stack first:

```bash
./start.sh
```

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

## Running tests in CI

CI should run headless. A Playwright container is recommended because it provides consistent browser binaries and browser system dependencies:

```bash
podman run --rm --network host \
  -v "$PWD:/work:Z" \
  -w /work \
  mcr.microsoft.com/playwright/python:v1.60.0-noble \
  pytest tests/e2e
```

If the CI environment exposes the UI at a non-local URL, set:

```bash
ORCH_UI_URL=https://orchestrator-ui.example.test
```

or pass:

```bash
pytest tests/e2e --orchestrator-ui-url https://orchestrator-ui.example.test
```

Do not use `--headed` in CI.

## Browser strategy

The intended modes are:

| Mode | Command style | Browser source | Use case |
|---|---|---|---|
| Local headless | `pytest tests/e2e` | Playwright-managed browser | Fast local smoke checks on macOS/Ubuntu/Windows and compatible environments |
| Local headed | `pytest tests/e2e --headed` | Playwright-managed browser | Visual debugging on macOS/Ubuntu/Windows and compatible environments |
| Fedora headed | `pytest tests/e2e --headed --system-browser` | Fedora system Chromium/Chrome | Visual debugging when Playwright-managed browser dependencies are not available on Fedora |
| CI headless | Playwright container | Container browser | Reproducible automated runs |

The `--system-browser` option is mainly for Fedora and other developer machines where a system browser works better than Playwright-managed browser binaries. Developers on macOS, Ubuntu, and Windows should usually install Playwright browsers and run without `--system-browser`.

## Why add an E2E showcase task?

Most workflows in this repository are domain workflows. They depend on product data, NetBox state, subscription lifecycle, and sometimes optional LSO behavior. That makes them useful integration tests, but not ideal as the only coverage for generic UI behavior.

A dedicated system task, for example `E2E Component Showcase`, should be implemented to provide deterministic coverage for:

- every supported frontend form component;
- normal process step progression;
- conditional process branches;
- input/suspended process steps;
- callback/waiting process steps, where supported for tasks;
- controlled process failure states;
- summary/confirmation forms;
- validation error rendering.

The task should not create real products or rely on NetBox inventory. It should use static choices and simple in-memory state so it can run repeatedly in local development and CI.

## Suggested E2E showcase task shape

Suggested location:

```text
workflows/tasks/e2e_showcase.py
```

Suggested registration:

```python
@workflow(
    "E2E Component Showcase",
    initial_input_form=initial_input_form_generator,
    target=Target.SYSTEM,
)
def task_e2e_component_showcase() -> StepList:
    return (
        init
        >> record_initial_input
        >> maybe_run_conditional_step(run_conditional_step)
        >> maybe_suspend_for_confirmation(show_suspended_form)
        >> maybe_wait_for_callback(callback_interaction)
        >> maybe_fail(fail_on_purpose)
        >> done
    )
```

The exact callback/input-step implementation should be validated against orchestrator-core's task support. If callback route/token details are not exposed through the process detail API, the callback scenario may need a small test-only mechanism to surface the callback route.

## Process/workflow patterns to cover

| Pattern | What the UI test should assert | Existing examples |
|---|---|---|
| System task | Task can be selected, started, and reaches a final state | `workflows/tasks/bootstrap_netbox.py`, `workflows/tasks/wipe_netbox.py` |
| Linear steps | Step list progresses in order | Most workflows using `begin >> step_a >> step_b` |
| Conditional step, branch taken | Conditional step appears/runs when the flag is true | `workflows/node/create_node.py`, `workflows/node/shared/steps.py` |
| Conditional step, branch skipped | Conditional step is skipped or absent when the flag is false | `workflows/node/shared/steps.py` |
| Input/suspended step | Process pauses and the UI shows a resume/input form | `services/lso_client.py` uses `@inputstep` |
| Callback step | Process waits for a callback and resumes after callback payload | `services/lso_client.py` uses `callback_step` |
| Failure step | Process reaches failed state and the UI displays the error | `services/lso_client.py` raises `ProcessFailureError` |
| Summary form | User can review submitted values and go back/continue | `workflows/shared.py` `create_summary_form()` |

Domain workflow categories that should eventually get separate integration coverage:

| Category | Existing examples |
|---|---|
| Create workflows | `workflows/node/create_node.py`, `workflows/port/create_port.py`, `workflows/l2vpn/create_l2vpn.py` |
| Modify workflows | `workflows/node/modify_node.py`, `workflows/port/modify_port.py` |
| Terminate workflows | `workflows/node/terminate_node.py`, `workflows/port/terminate_port.py` |
| Validate workflows | `workflows/node/validate_node.py`, `workflows/l2vpn/validate_l2vpn.py` |
| Reconcile workflows | `workflows/l2vpn/modify_l2vpn.py`, `workflows/nsip2p/modify_nsip2p.py` |

## Frontend form elements to cover

| Form element/pattern | Source pattern | Existing examples |
|---|---|---|
| Product selector | create workflow product selection | all create workflows |
| Single select/dropdown | `Choice(...)` | node type/role/site, port mode |
| Multi-select/list of choices | `choice_list(Choice(...), min_items=..., max_items=...)` | L2VPN/NSIP2P port selection |
| Text input | `str` | `node_name`, `port_description`, `topology`, `stp_id` |
| Optional text input | `str | None = None` | `node_description`, `stp_description`, `is_alias_in`, `is_alias_out` |
| Long text | `LongText` | LSO callback result display |
| Integer input | `int` | `speed`, `bandwidth`, `number_of_ports` |
| Constrained integer | `Annotated[int, Ge(...), Le(...)]` | `AllowedNumberOfL2vpnPorts`, `Bandwidth` |
| Boolean checkbox/switch | `bool` / `bool | None` | `auto_add_interfaces`, `auto_negotiation`, `lldp`, `speed_policer` |
| VLAN/range input | `VlanRanges` with validators | L2VPN, NSIP2P, NSISTP |
| Label/header | `Label` | node/port/NSISTP settings sections |
| Divider | `Divider` | NSISTP form |
| Callout/info block | `callout(...)` | node create form |
| Read-only field | `read_only_field(...)` | modify forms |
| Display subscription | `DisplaySubscription` | terminate forms |
| Generated summary | `migration_summary(...)` / `create_summary_form(...)` | create and modify confirmation pages |
| Cross-field validation | `@model_validator(mode="after")` | core link distinct nodes, NSISTP alias pair validation |
| Custom field validation | `AfterValidator(...)` | VLAN, NSISTP topology/STP/isAlias validation |

No native date picker was found in the current workflow forms. There is date parsing logic for NSISTP NURN values in `workflows/nsistp/shared/forms.py`, but it is currently a validated string pattern rather than a date form widget.

## Suggested E2E test cases for the showcase task

| Test case | Input flags | Coverage |
|---|---|---|
| Happy path | optional process flags false | basic form elements, summary, normal steps, completion |
| Validation errors | invalid constrained integer, invalid cross-field combination | validation rendering |
| Conditional branch taken | `run_conditional_step=true` | conditional process behavior |
| Conditional branch skipped | `run_conditional_step=false` | skipped branch behavior |
| Suspended input | `show_suspended_step=true` | waiting/suspended state and resume form |
| Callback | `wait_for_callback=true` | callback waiting state and resume after callback |
| Failure | `fail_on_purpose=true` | failed process state and error UI |

## Notes for AI agents

- Prefer stable locators in E2E tests: role, label, visible name, then `data-testid` if available.
- Do not use Playwright MCP element references in committed tests; they are session-local.
- Keep tests deterministic. The showcase task should use static choices rather than NetBox-derived choices.
- Keep domain workflow tests separate from generic form/process tests. Domain flows are useful, but they require more setup and are more likely to fail due to inventory state.
- Run headed locally with `--headed` when Playwright-managed browsers work; add `--system-browser` for Fedora/system-browser debugging; run CI headless.
- The local default UI URL is `http://localhost:3000`; use `ORCH_UI_URL` for CI overrides.
