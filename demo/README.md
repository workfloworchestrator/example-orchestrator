# Network demo

A setup that shows the AI agents working against a **real (emulated)
network**, for demos and for anyone who wants to try the agents on a network: the workshop's containerlab topology of three Nokia SR
Linux nodes, provisioned by the orchestrator through LSO/Ansible, with an extra
read-only **network agent** whose tools read live device state.

Every use case starts as a **ticket**, the way work reaches a NOC: customer
support, a monitoring alert, a change request. `demo/tickets/` holds four
static tickets standing in for the ticket system, `demo.py triage`
hands one to the planner, and the planner's answer is the resolution.

Everything specific to the demo lives in this folder. The base stack and the
agents profile are reused: the planner in `docker/planner-agent` already
lists the network agent as an optional peer, and the demo only swaps in its
own planner prompt (`PLANNER_INSTRUCTIONS`, set in `demo.env`). The network
agent and its MCP server are the only agents the demo adds.

```
LibreChat → a2a-proxy → planner ─A2A─┬─► wfo-agent ──MCP──► orchestrator
                                     ├─► inventory-agent ──MCP──► netbox-mcp → NetBox
                                     └─► network-agent ──MCP──► network-mcp → SR Linux nodes (JSON-RPC)
                                                                     ▲
                        containerlab: ams-pe ── par-p ── lon-pe ─────┘  (clab/srlinux01.clab.yaml)
```

| Piece                           | Where                                                                                                                                                     | Role                                                                                                                                 |
| ------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------ |
| `docker-compose.demo.yml`       | included from `docker-compose.yml`, profile `network`                                                                                                     | `network-mcp` + `network-agent`                                                                                                      |
| `network-mcp/`                  | FastMCP server over SR Linux JSON-RPC: `server.py` app, `tools.py` the tools (a mounted router), `srlinux.py` device access, `wfo.py` orchestrator intent | read-only device state tools; `check_core_links` verifies every core-link subscription on the devices and measures loss/RTT per link |
| `network-agent/`                | docker-agent (cagent) manifest                                                                                                                            | the specialist the planner delegates to                                                                                              |
| `planner-agent/instructions.md` | demo planner prompt (intent vs reality, tickets)                                                                                                          | mounted over the generic one via `PLANNER_INSTRUCTIONS`                                                                              |
| `scripts/demo.py`               | the demo CLI: `seed`, `reset`, `impair`, `triage`, `verify` (typer, `uv run`)                                                                             | everything you run                                                                                                                       |
| `scripts/seed.py`               | workshop "Seeding data" steps via core's `Populator`                                                                                                      | reproducible demo state (`demo.py seed`)                                                                                             |
| `tickets/`                      | four static tickets, one per use case                                                                                                                     | stand in for the ticket system                                                                                                       |
| `demo.env` | compose env file: profiles, LSO, planner prompt | `docker compose --env-file .env --env-file demo/demo.env` |

To run the demo on a public server with HTTPS hostnames (Traefik + Let's
Encrypt), see [HTTPS.md](HTTPS.md).

## Prerequisites

- The base stack and the agents as described in the root README:
  [Quickstart](../README.md#quickstart), the [AI agents](../README.md#ai-agents)
  section for the LLM key, and, on Apple Silicon,
  [Docker runtimes](../README.md#docker-runtimes) (memory and SR Linux notes).
- [containerlab](https://containerlab.dev/install/) on the host; it attaches
  the SR Linux nodes to the compose network.

## Bring it up

```bash
docker compose --env-file .env --env-file demo/demo.env up -d --wait   # root .env + profiles lso,agents,network, LSO, demo planner prompt
(cd clab && sudo containerlab deploy)                   # three SR Linux nodes on the compose network
uv run python demo/scripts/demo.py seed                 # bootstrap NetBox, 3 nodes, 2 core links
```

`demo/demo.env` is a compose env file. An explicit `--env-file` replaces the
default root `.env`, so pass both, to every `docker compose` command you run
for the demo (or export `COMPOSE_ENV_FILES=.env,demo/demo.env` once).

`demo.py seed` follows the workshop's
[Seeding data](https://workfloworchestrator.org/workshops/example-orchestrator/execute-workflows/)
page exactly (same node names `clab-orch-demo-ams-pe`, `-par-p`, `-lon-pe`,
sites and core links), but through the process API, built on orchestrator-core's
own `orchestrator.core.devtools.populator.Populator` (the base class SURF's
devtools populators use): it walks the workflow forms, resolves choices by
their labels, and confirms the LSO "Confirm provisioning proxy results" pauses
itself. Hence `uv run`: it needs the example-orchestrator project environment.
With LSO enabled the node and core-link workflows push loopbacks, IS-IS and link
interfaces to the SR Linux nodes, so the emulated network really carries the
modelled services. It is idempotent; `--dry-run` lists what would be created.

Sanity check: `uv run python demo/scripts/demo.py verify` checks the services, the lab nodes,
JSON-RPC and MCP tool access, the seeded subscriptions, and finally asks the
planner _"Is the core link between Amsterdam and Paris healthy?"_ through the
proxy; expect interface, LLDP and IS-IS state from both ends, cross-referenced
with the subscription. The same question works in LibreChat
(http://localhost:3080).

## The use cases

Four use cases, deliberately no more. Each is one ticket, one fault (or
none), one `demo.py triage` run. Inject the fault, run the ticket, read the
resolution; `demo.py impair clear` between them.

| #   | ticket                                                       | source                                          | inject first   | what the agents show                                                                                                                                                   |
| --- | ------------------------------------------------------------ | ----------------------------------------------- | -------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1   | `T-1001` Amsterdam ↔ London down                             | customer support: symptom only, no device names | `impair down`  | sites → path → core-link subscriptions → both ends on the devices; names `clab-orch-demo-par-p ethernet-1/2` as administratively disabled under an active subscription |
| 2   | `T-1002` interface oper-state down on `par-p ethernet-1/2`   | monitoring alert: precise, no context           | `impair down`  | the same fault from the other side: port → subscription → customer, expected state vs fault, impact                                                                    |
| 3   | `T-1003` packet loss Amsterdam ↔ London                      | customer support: degraded, nothing down        | `impair loss`  | configuration and IS-IS are clean, the link check measures loss on the lossy hop → transport, not config                                                               |
| 4 | `T-1005` change request: maintenance on `par-p ethernet-1/2` | change management                               | none           | impact assessment: which subscription and customer, is it healthy and in use, alternate path or not, what to flag as under maintenance                                 |

```sh
uv run python demo/scripts/demo.py impair down
uv run python demo/scripts/demo.py triage demo/tickets/T-1001-*.md   # one ticket
uv run python demo/scripts/demo.py triage                             # every ticket
uv run python demo/scripts/demo.py impair clear
```

Suggested order: 1 and 2 back to back (one fault, two views), reset, 3 (same
customer symptom as 1, different root cause: the agents tell them apart
because one reads configuration state and the other measures the data plane),
reset, then 4 as the non-incident closer.

Follow-up questions are the one place to type: after a resolution, ask the
planner in LibreChat (http://localhost:3080) something like _"Why is the
Paris-London link fine, then?"_, the human-in-the-loop moment. Keep even
those close to the ticket; improvising broad questions invites detours.

Why the network agent has a `check_core_links` tool: it reads the core-link
subscriptions (intent) from the orchestrator, checks both ends of each on
the devices (reality) and, when a link's state is clean, pings across it for
loss and round-trip time, deterministically, in one call. Without it the
planner had to pass the right transit-node port and pick ping targets
itself, and across several runs it guessed wrong or got distracted about
once in two (once pinging an address that does not exist and reporting
100 % loss on a healthy network), which is not acceptable. With it, every
ticket is one delegation and the diagnosis was correct on every run.
`find_core_link` is the same idea for "what runs over this port".

This was tested the other way round too: a device-only `check_links(links)`
where the planner copies the node/interface pairs from the wfo agent's
subscription descriptions. Two runs of the (then five) tickets scored 1/5 and 3/5:
the wfo delegation came back empty when phrased loosely, the port question
counted a second link on the same node as affected, and once the planner
copied `clab-orch-demo-fra-pe`, a node that does not exist, into the
check. Reading the intent inside the tool (`wfo.py`, 38 lines) is the price
of a demo that is right every time.

Things worth knowing:

- Nothing after bring-up needs `sudo`: `demo.py impair` applies loss
  with `tc` inside the (privileged) SR Linux container and toggles
  admin state through SR Linux's JSON-RPC. Only `containerlab deploy` is
  root.
- The provisioned data plane is **IPv6-only** on the core links (the
  workshop's playbooks put `fc00:0:0:10::/127`s on them); loopbacks have both
  families but only the IPv6 ones (`fc00:0:0:127::<n>`) route across the
  network. The network agent knows this; an IPv4 ping failing is not a fault.
- The workshop's manual "reserve `10.0.127.0/32` / `fc00:0:0:127::/128`"
  step is already covered by placeholder addresses the bootstrap task creates;
  `demo.py seed` reports them as already registered.

## Reset between runs

```bash
uv run python demo/scripts/demo.py impair clear   # clear impairments
(cd clab && sudo containerlab destroy --cleanup && sudo containerlab deploy)
uv run python demo/scripts/demo.py reset   # terminate the demo subscriptions (runs the LSO deprovisioning)
uv run python demo/scripts/demo.py seed    # re-provision from scratch
```

`demo.py reset` terminates; it does not delete. The terminated
subscriptions stay in the orchestrator next to the new active ones, as they
would in production, and the agents are instructed to filter on status; a
stack that has been reset a few times is a slightly more honest dataset,
not a broken one. A full wipe is `docker compose --env-file .env --env-file demo/demo.env down -v`
followed by the bring-up steps.
