# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

An example implementation on top of [orchestrator-core](https://workfloworchestrator.org/orchestrator-core/) (WFO), pinned in `pyproject.toml` (`orchestrator-core[mcp]`). It models a virtual NREN: nodes, core links, customer ports, L2VPNs, NSISTP and NSIP2P, provisioned into NetBox (the IMS) and optionally into devices through LSO/Ansible. Python is pinned to 3.13 to match the orchestrator-core Docker image.

## Commands

The app is meant to run in Docker Compose; there is no local "run the server" workflow outside it.

```bash
docker compose up                                        # orchestrator :8080, UI :3000, netbox :8000 (admin/admin), federation :4000, postgres, redis
COMPOSE_PROFILES=lso LSO_ENABLED=True docker compose up  # + LSO with the Ansible playbooks in ansible/
COMPOSE_PROFILES=agents docker compose up -d             # + AI agent stack (needs AGENT_MODEL/AGENT_API_KEY in root .env)

uv sync --group dev                                      # local dev env (lint + e2e tests)
uv run pre-commit run --all-files                        # what CI runs: yamllint, ruff check --fix, ruff format
uv run pytest tests/e2e/                                 # Playwright e2e; needs the compose stack up
uv run pytest tests/e2e/test_showcase.py::<test_name>    # single test
uv run pytest tests/e2e --headed --slowmo 250            # debug; add --system-browser on Fedora
```

The orchestrator container's entrypoint (`docker/orchestrator/entrypoint.sh`) runs `uv sync`, `python main.py db upgrade heads`, rebuilds the search indexes (`python main.py index ...`), then starts uvicorn with `--reload`, so code edits hot-reload. The WFO CLI is `python main.py` (run it inside the container, e.g. `docker compose exec orchestrator python main.py db ...`).

CI (`.github/workflows/ci.yml`) runs pre-commit, then brings up the full stack, fails if any service is unhealthy **or if any compose log line contains "error"** (excluding `uvicorn.error`), then runs the e2e tests. `UV_LOCKED=true` in CI, so `uv.lock` must be up to date.

Ruff: line length 120, rules `F` + `I` only, relative imports banned.

## Architecture

The code follows the WFO standard layout (explained at length in README.md); the non-obvious parts are how pieces get wired together.

**Entry points and registration by import side effect.** `wsgi.py` (API) and `main.py` (CLI) import `db`, `products` and (API only) `workflows` purely for side effects:
- `products/__init__.py` maps every product *name* (e.g. `"core link 10G"`) to its product type class in `SUBSCRIPTION_MODEL_REGISTRY`.
- `workflows/__init__.py` registers every workflow with `LazyWorkflowInstance("workflows.<product>.<file>", "<workflow_name>")`.
- `db/models.py` registers the custom `CustomerTable`.
- `graphql_utils/` adds custom GraphQL models and the federation subscription interface, registered in `wsgi.py`.

**Adding a product or workflow touches several places that must agree:** the domain model in `products/`, the registry entry in `products/__init__.py`, the workflow modules plus `LazyWorkflowInstance` lines, an Alembic migration in `migrations/versions/schema/` that inserts the product/product blocks/fixed inputs/workflows into the DB (names and `product_type` must match the registry and the class), and GUI labels in `translations/en-GB.json`. `templates/*.yaml` are the configs for orchestrator-core's `generate` CLI, which scaffolds all of this. Migrations use orchestrator-core's multiple-heads setup (`alembic.ini`, filenames `YYYY-MM-DD_<rev>_<slug>.py`); look at an existing one before writing a new one.

**Domain models are lifecycle-typed.** Each product type and product block is defined three times as a class chain `XInactive` → `XProvisioning` → `X` (ACTIVE), with fields becoming non-optional as the lifecycle advances (see `products/product_blocks/core_port.py`). Workflows move a subscription between them with `from_other_lifecycle`. Product blocks nest (a core link holds core ports which reference node blocks), so product blocks are shared across products.

**Workflows** live in `workflows/<product>/{create,modify,terminate,validate}_<product>.py`, with per-product helpers in `workflows/<product>/shared/` and cross-product form selectors/summary forms in `workflows/shared.py`. Steps are `@step` functions whose arguments are filled from the JSON-serialized process `State` by name and type, and which return a dict merged back into the state, so parameter type hints matter. Input forms are generators yielding `FormPage` classes. `workflows/tasks/` holds non-subscription tasks (NetBox bootstrap/wipe, showcase). Some L2VPN IMS steps are known not to be idempotent.

**External systems.** `services/netbox.py` is the NetBox client (pynetbox); `products/services/netbox/` builds NetBox payloads from product blocks, and `products/services/description.py` builds subscription descriptions. Both dispatch on the domain model type via `utils/singledispatch.py`. `services/lso_client.py` wraps LSO playbook execution (`lso_interaction` pauses the workflow until results are confirmed); those steps are skipped unless the env var `LSO_ENABLED == "True"`. App-specific settings (NetBox URL/token, IP prefixes) are in `settings.py`.

**Docker configuration.** Each service reads `docker/<service>/<service>.env`, overridable via gitignored files in `docker/overrides/<service>/` (see `docker/overrides/configuration.md`). A local orchestrator-core checkout in `docker/overrides/orchestrator-core` or `CORE_DIR=...` is installed editable with hot reload. All ports bind to `127.0.0.1` by default; `BIND_ADDRESS_<SERVICE>` overrides that.

**AI agents and the network demo.** `docker-compose.yml` `include:`s `docker-compose.agents.yml` (profile `agents`) and `demo/docker-compose.demo.yml` (profile `network`). Chain: LibreChat → `a2a-proxy` → `planner-agent` → (A2A) `wfo-agent` (tools from the orchestrator's built-in `/mcp`, enabled by `MCP_ENABLED=True`) and `inventory-agent` (via `netbox-mcp`). The cagent agents are fully defined by `docker/<name>-agent/agent.yaml` + `instructions.md`; the planner learns about peers from their A2A agent cards, so restart `planner-agent` after restarting a peer. `demo/` adds a containerlab SR Linux lab (`clab/`), a read-only `network-mcp`/`network-agent`, ticket-driven use cases, and `demo/scripts/demo.py` (`seed`, `reset`, `impair`, `triage`, `verify`); pass `--env-file .env --env-file demo/demo.env` to every compose command for the demo. See `demo/README.md`.

**Public HTTPS deployment of the demo.** `demo/docker-compose.traefik.yml` is an overlay, never used on its own. It adds Traefik with Let's Encrypt HTTP-01 in front of `gui.`/`api.`/`chat.`/`netbox.`/`traefik.${DEMO_DOMAIN}`, all behind one IP-allowlist middleware (`ALLOWED_IPS`). That allowlist is the only protection, because the apps run without auth. Public URLs and fresh secrets are injected via `environment:` (which wins over `env_file`), so the tracked `docker/*/*.env` files stay unchanged. The overlay also unpublishes postgres's host port (`ports: !reset []`). Settings live in the gitignored `demo/networkdemo.env`, with a template in `networkdemo.env.example`. Set up with `demo/HTTPS.md`; per shell:

```bash
export COMPOSE_FILE=docker-compose.yml:demo/docker-compose.traefik.yml
export COMPOSE_ENV_FILES=.env,demo/demo.env,demo/networkdemo.env   # later files win
```

Traefik must be v3.6+ (Docker Engine 29 rejects older API clients). On a first start the orchestrator can outlast its health check while it reloads; if `up --wait` reports it unhealthy, run it again once the logs show "Application startup complete".
