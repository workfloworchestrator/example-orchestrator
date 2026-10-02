"""The network demo's command line: seed, break, triage, verify.

uv run python demo/scripts/demo.py seed [--dry-run]   # NetBox bootstrap, 3 nodes, 2 core links (LSO provisions the lab)
uv run python demo/scripts/demo.py reset              # terminate the demo subscriptions
uv run python demo/scripts/demo.py impair loss|down|clear   # break or restore the Amsterdam <-> Paris link
uv run python demo/scripts/demo.py triage [TICKET ...]            # hand tickets to the planner, print the resolutions
uv run python demo/scripts/demo.py verify             # end-to-end sanity check after bring-up

"""

import os
import subprocess
from enum import Enum
from pathlib import Path

import requests
import typer

app = typer.Typer(help=__doc__, add_completion=False, no_args_is_help=True)

TICKETS = Path(__file__).resolve().parent.parent / "tickets"
PLANNER_URL = os.environ.get("PLANNER_URL", "http://localhost:8090/v1/chat/completions")
ORCHESTRATOR = os.environ.get("ORCHESTRATOR_URL", "http://localhost:8080").rstrip("/")
SRL_AUTH = (os.environ.get("SRL_USERNAME", "admin"), os.environ.get("SRL_PASSWORD", "NokiaSrl1!"))

# The link the demo breaks: the Paris end of Amsterdam <-> Paris.
NODE = os.environ.get("IMPAIR_NODE", "clab-orch-demo-par-p")
LINUX_IFACE = os.environ.get("IMPAIR_IFACE", "e1-2")  # the kernel interface inside the container
SRL_IFACE = "ethernet-" + LINUX_IFACE[1:].replace("-", "/")  # e1-2 -> ethernet-1/2

SERVICES = [
    "orchestrator",
    "orchestrator-lso",
    "netbox",
    "network-mcp",
    "network-agent",
    "planner-agent",
    "wfo-agent",
    "a2a-proxy",
]
LAB_NODES = ["clab-orch-demo-ams-pe", "clab-orch-demo-par-p", "clab-orch-demo-lon-pe"]

TRIAGE_PROMPT = """You are handling a support ticket. Diagnose it with your specialist agents. Do not narrate your plan; reply only with this structure:

## Summary
## Findings (facts per source system, identifiers verbatim)
## Root cause (incidents: the node and interface where intent and reality disagree, or "no fault found"; requests: not applicable)
## Impact (affected subscriptions and customers)
## Recommended action

Ticket:

{ticket}"""


# --- helpers ------------------------------------------------------------------


def docker(*args: str, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(["docker", *args], capture_output=True, text=True, check=check)


def running_containers() -> set[str]:
    return set(docker("ps", "--format", "{{.Names}}").stdout.split())


def container_ip(name: str) -> str:
    """The node's address on the compose network; the lab nodes are not in the host's DNS."""
    return docker("inspect", "-f", "{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}", name).stdout.strip()


def jsonrpc(node: str, method: str, params: dict) -> object:
    response = requests.post(
        f"http://{container_ip(node)}/jsonrpc",
        auth=SRL_AUTH,
        json={"jsonrpc": "2.0", "id": 0, "method": method, "params": params},
        timeout=20,
    )
    response.raise_for_status()
    body = response.json()
    if "error" in body:
        raise RuntimeError(f"{node}: {body['error']}")
    return body["result"]


def admin_state(state: str) -> None:
    jsonrpc(
        NODE,
        "set",
        {"commands": [{"action": "update", "path": f"/interface[name={SRL_IFACE}]", "value": {"admin-state": state}}]},
    )
    typer.echo(f"{NODE} {SRL_IFACE} admin-state {state}")


def netem(*qdisc: str) -> None:
    """Apply (or with no arguments clear) a netem qdisc on the link inside the node's container."""
    if qdisc:
        docker("exec", NODE, "tc", "qdisc", "replace", "dev", LINUX_IFACE, "root", "netem", *qdisc)
        typer.echo(f"{NODE} {LINUX_IFACE} netem {' '.join(qdisc)}")
    else:
        docker("exec", NODE, "tc", "qdisc", "del", "dev", LINUX_IFACE, "root", check=False)
        typer.echo(f"{NODE} {LINUX_IFACE} netem cleared")


def ask_planner(prompt: str, timeout: int = 300) -> str:
    payload = {"model": "planner", "messages": [{"role": "user", "content": prompt}]}
    response = requests.post(PLANNER_URL, json=payload, timeout=timeout)
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]


def check(passed: bool, message: str, hint: str = "") -> bool:
    mark = typer.style("OK  ", fg="green") if passed else typer.style("FAIL", fg="red")
    typer.echo(f"  {mark} {message}" + ("" if passed else f" {hint}"))
    return passed


# --- commands -----------------------------------------------------------------


@app.command(name="seed")
def seed_cmd(
    dry_run: bool = typer.Option(False, "--dry-run", help="print what would be created without starting workflows"),
) -> None:
    """Bootstrap NetBox and create the 3 nodes and 2 core links (skips what exists)."""
    import seed  # imports orchestrator-core, which is slow and chatty; only where it is needed

    seed.seed(dry_run=dry_run)


@app.command()
def reset() -> None:
    """Terminate the demo subscriptions (core links first, then nodes; LSO deprovisions the devices)."""
    import seed

    typer.echo("reset: terminating demo subscriptions")
    seed.reset()


class Impairment(str, Enum):
    loss = "loss"
    down = "down"
    clear = "clear"


@app.command()
def impair(kind: Impairment) -> None:
    """Break the Amsterdam <-> Paris link at the Paris end, or restore it.

    loss: 30% packet loss (link state stays clean) - down: administratively disable the port - clear: undo all
    """
    if kind is Impairment.loss:
        netem("loss", "30%")
    elif kind is Impairment.down:
        admin_state("disable")
    else:
        netem()
        admin_state("enable")


@app.command()
def triage(
    tickets: list[Path] = typer.Argument(None, help="ticket files; default: every ticket in demo/tickets"),
) -> None:
    """Hand tickets to the planner and print its diagnosis; the ticket file is the prompt, nobody types."""
    if not tickets:
        tickets = sorted(TICKETS.glob("*.md"))
    for ticket in tickets:
        text = ticket.read_text()
        typer.echo("\n=== " + typer.style(text.splitlines()[0].lstrip("# "), bold=True))
        typer.echo(ask_planner(TRIAGE_PROMPT.format(ticket=text)))


@app.command()
def verify() -> None:
    """Check services, lab nodes, device access, MCP tools, seeded subscriptions and one planner answer."""
    results = []
    running = running_containers()

    typer.echo("1. compose services")
    results += [check(service in running, f"{service} running") for service in SERVICES]

    typer.echo("2. containerlab nodes")
    results += [
        check(node in running, f"{node} running", "(cd clab && sudo containerlab deploy)") for node in LAB_NODES
    ]

    typer.echo("3. SR Linux JSON-RPC")
    try:
        jsonrpc(LAB_NODES[0], "get", {"commands": [{"path": "/system/name/host-name", "datastore": "state"}]})
        results.append(check(True, "JSON-RPC answers"))
    except Exception as exc:  # noqa: BLE001 - any failure is the finding
        results.append(check(False, "JSON-RPC unreachable", str(exc)))

    typer.echo("4. network MCP tools")
    probe = (
        "import asyncio, server\nfrom fastmcp import Client\n"
        "async def main():\n"
        "    async with Client(server.mcp) as c:\n"
        "        assert 'check_core_links' in [t.name for t in await c.list_tools()]\n"
        "        assert (await c.call_tool('get_interfaces', {'node': (await c.call_tool('list_nodes', {})).data[0]})).data\n"
        "asyncio.run(main())\n"
    )
    result = docker("exec", "network-mcp", "python", "-c", probe, check=False)
    results.append(check(result.returncode == 0, "MCP tools respond", result.stderr.strip()[-200:]))

    typer.echo("5. demo subscriptions")
    import seed

    count = len(seed.demo_subscriptions())
    results.append(check(count >= 5, f"{count} active demo subscriptions (3 nodes + 2 core links)", "(demo.py seed)"))

    typer.echo("6. planner answers through the proxy")
    try:
        answer = ask_planner(
            "Is the core link between Amsterdam and Paris healthy? Check both ends on the devices.", timeout=170
        )
        results.append(check(True, "planner answered"))
        typer.echo("\n".join("     " + line for line in answer.splitlines()[:20]))
    except Exception as exc:  # noqa: BLE001
        results.append(check(False, "no answer from planner", str(exc)))

    raise typer.Exit(0 if all(results) else 1)


if __name__ == "__main__":
    app()
