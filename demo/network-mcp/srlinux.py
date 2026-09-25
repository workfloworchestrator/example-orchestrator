"""SR Linux access for the network tools: JSON-RPC state reads, pings and their parsing."""

import os

import httpx

NODES = [n.strip() for n in os.environ.get("NETWORK_NODES", "").split(",") if n.strip()]
AUTH = (os.environ.get("SRL_USERNAME", "admin"), os.environ.get("SRL_PASSWORD", "NokiaSrl1!"))


def rpc(node: str, method: str, params: dict) -> object:
    if node not in NODES:
        raise ValueError(f"unknown node {node!r}; known nodes: {NODES}")
    response = httpx.post(
        f"http://{node}/jsonrpc",
        auth=AUTH,
        json={"jsonrpc": "2.0", "id": 0, "method": method, "params": params},
        timeout=20,
    )
    response.raise_for_status()
    body = response.json()
    if "error" in body:
        raise RuntimeError(f"{node}: {body['error']}")
    return body["result"]


def get_state(node: str, *paths: str) -> object:
    result = rpc(node, "get", {"commands": [{"path": p, "datastore": "state"} for p in paths]})
    return result[0] if len(paths) == 1 else result


def interface_summary(interface: dict) -> dict:
    """The fields an operator looks at first; full state stays available via get_interface."""
    stats = interface.get("statistics", {})
    return {
        "name": interface.get("name"),
        "description": interface.get("description"),
        "admin-state": interface.get("admin-state"),
        "oper-state": interface.get("oper-state"),
        "last-change": interface.get("last-change"),
        "addresses": [
            address.get("ip-prefix")
            for sub in interface.get("subinterface", [])
            for family in ("ipv4", "ipv6")
            for address in sub.get(family, {}).get("address", [])
        ],
        "in-packets": stats.get("in-packets"),
        "out-packets": stats.get("out-packets"),
        "in-error-packets": stats.get("in-error-packets"),
        "out-error-packets": stats.get("out-error-packets"),
        "in-discarded-packets": stats.get("in-discarded-packets"),
    }


def link_address(node: str, interface: str) -> str | None:
    """The global IPv6 address configured on a core-link interface (the data plane is IPv6-only)."""
    summary = interface_summary(get_state(node, f"/interface[name={interface}]"))
    return next((a.split("/")[0] for a in summary["addresses"] if a.startswith("fc00:")), None)


def ping_stats(text: str) -> dict:
    """Loss and round-trip time from SR Linux ping output."""
    stats: dict = {"loss_percent": None, "rtt_avg_ms": None, "rtt_max_ms": None}
    for line in text.splitlines():
        if "packet loss" in line:
            stats["loss_percent"] = float(line.split("%")[0].split()[-1])
        if line.startswith("rtt"):
            _, avg, mx, _ = line.split("=")[1].split()[0].split("/")  # min/avg/max/mdev
            stats["rtt_avg_ms"], stats["rtt_max_ms"] = float(avg), float(mx)
    return stats


def ping(node: str, target: str, count: int) -> str:
    """Ping from a node's default network instance; the raw CLI output."""
    output = rpc(node, "cli", {"commands": [f"ping {target} network-instance default -c {count}"]})
    return output[0].get("text", "") if isinstance(output, list) and output else str(output)


def measure(node_from: str, node_to: str, interface_to: str, count: int = 5) -> dict | None:
    """Loss and round-trip time across one link, pinged from one end to the other end's own address."""
    target = link_address(node_to, interface_to)
    if target is None:
        return None
    return {
        "from": node_from,
        "to": f"{node_to} ({target})",
        "packets": count,
        **ping_stats(ping(node_from, target, count)),
    }
