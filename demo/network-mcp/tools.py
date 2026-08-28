"""The network tools: SR Linux state (srlinux.py) checked against the orchestrator's intent (wfo.py).

Every public function is a tool on ``router``, a sub-server that server.py
mounts (FastMCP's equivalent of an API router). Every SR Linux call is a
*state* read (or a ping); there is deliberately no set/config tool.
"""

import srlinux
import wfo
from fastmcp import FastMCP

router = FastMCP("network-tools")


@router.tool()
def list_nodes() -> list[str]:
    """The SR Linux nodes this server can query (containerlab hostnames = NetBox device names)."""
    return srlinux.NODES


@router.tool()
def get_interfaces(node: str, include_disabled: bool = False) -> list[dict]:
    """Summary of a node's interfaces: admin/oper state, description, addresses, packet and error counters.

    Unused (admin-disabled, undescribed) ports are omitted unless include_disabled is set.
    """
    state = srlinux.get_state(node, "/interface[name=*]")
    interfaces = state.get("srl_nokia-interfaces:interface", []) if isinstance(state, dict) else []
    summaries = [srlinux.interface_summary(i) for i in interfaces]
    if include_disabled:
        return summaries
    return [i for i in summaries if i["admin-state"] == "enable" or i["description"] or i["addresses"]]


@router.tool()
def get_interface(node: str, interface: str) -> object:
    """Full state of one interface, e.g. 'ethernet-1/1' or 'lo1' (subinterfaces, addresses, counters)."""
    return srlinux.get_state(node, f"/interface[name={interface}]")


@router.tool()
def get_lldp_neighbors(node: str) -> list[dict]:
    """LLDP neighbors per interface: which remote node and port is physically connected."""
    state = srlinux.get_state(node, "/system/lldp/interface[name=*]/neighbor")
    return [
        {
            "interface": interface.get("name"),
            "neighbor-system": neighbor.get("system-name"),
            "neighbor-port": neighbor.get("port-id"),
            "last-update": neighbor.get("last-update"),
        }
        for interface in (state.get("interface", []) if isinstance(state, dict) else [])
        for neighbor in interface.get("neighbor", [])
    ]


@router.tool()
def get_isis_adjacencies(node: str) -> object:
    """IS-IS adjacency state in the default network instance (up/down per interface)."""
    return srlinux.get_state(
        node,
        "/network-instance[name=default]/protocols/isis/instance[name=default]/interface[interface-name=*]/adjacency",
    )


@router.tool()
def get_link_state(node_a: str, interface_a: str, node_b: str, interface_b: str) -> dict:
    """Health of one core link seen from both ends at once: admin/oper state, LLDP neighbor and
    IS-IS adjacency per end, plus a verdict. Use the ends as named in the core link subscription."""
    ends = {}
    for node, interface in ((node_a, interface_a), (node_b, interface_b)):
        summary = srlinux.interface_summary(srlinux.get_state(node, f"/interface[name={interface}]"))
        lldp = [n for n in get_lldp_neighbors(node) if n["interface"] == interface]
        isis = srlinux.get_state(
            node,
            f"/network-instance[name=default]/protocols/isis/instance[name=default]/interface[interface-name={interface}.0]/adjacency",
        )
        adjacencies = isis.get("adjacency", []) if isinstance(isis, dict) else []
        ends[node] = {
            "interface": interface,
            "admin-state": summary["admin-state"],
            "oper-state": summary["oper-state"],
            "lldp-neighbor": lldp[0] if lldp else None,
            "isis-adjacency": [{"neighbor": a.get("neighbor-hostname"), "state": a.get("state")} for a in adjacencies],
        }
    problems = []
    for node, end in ends.items():
        if end["admin-state"] != "enable":
            problems.append(
                f"{node} {end['interface']} is administratively disabled (admin-state {end['admin-state']})"
            )
        elif end["oper-state"] != "up":
            problems.append(f"{node} {end['interface']} is oper-state {end['oper-state']} although admin-state enable")
        elif not any(a["state"] == "up" for a in end["isis-adjacency"]):
            problems.append(f"{node} {end['interface']} has no IS-IS adjacency up")
    return {"ends": ends, "healthy": not problems, "problems": problems}


@router.tool()
def list_core_links() -> list[dict]:
    """The active core link subscriptions (the orchestrator's intent) with the node, interface and customer at each end."""
    return wfo.core_link_subscriptions()


@router.tool()
def find_core_link(node: str, interface: str) -> dict:
    """The active core link subscription that uses exactly this node and interface (e.g. clab-orch-demo-par-p, ethernet-1/2),
    with its customer and the far end. Use this to answer "which service runs over this port"; it never returns a core
    link on another interface of the same node."""
    for link in wfo.core_link_subscriptions():
        for end, far in (("a", "b"), ("b", "a")):
            if link[f"node_{end}"] == node and link[f"interface_{end}"] == interface:
                return {**link, "far_end": {"node": link[f"node_{far}"], "interface": link[f"interface_{far}"]}}
    return {"found": False, "node": node, "interface": interface, "message": "no active core link uses this interface"}


@router.tool()
def check_core_links() -> list[dict]:
    """Intent versus reality for every active core link: the device state of both ends of each
    subscription's link, plus packet loss and round-trip time measured across the link when its state is
    clean, with a verdict and the problems found. The first stop for any path, link health, loss or latency
    question; nothing has to be guessed."""
    results = []
    for link in wfo.core_link_subscriptions():
        state = get_link_state(link["node_a"], link["interface_a"], link["node_b"], link["interface_b"])
        measurement = srlinux.measure(link["node_a"], link["node_b"], link["interface_b"]) if state["healthy"] else None
        stats = measurement or {}
        if stats.get("loss_percent"):
            state["problems"].append(
                f"{stats['loss_percent']:g}% packet loss across the link although both ends are up"
            )
        state["healthy"] = not state["problems"]
        results.append(
            {
                "subscription": link["description"],
                "subscription_id": link["subscription_id"],
                "customer": link["customer"],
                **state,
                "measurement": measurement,
            }
        )
    return results


@router.tool()
def get_route(node: str, prefix: str) -> object:
    """Route-table entry for an IPv4 or IPv6 prefix (e.g. '10.0.0.3/32') in the default network instance."""
    family = "ipv6-unicast" if ":" in prefix else "ipv4-unicast"
    key = "ipv6-prefix" if ":" in prefix else "ipv4-prefix"
    return srlinux.get_state(node, f"/network-instance[name=default]/route-table/{family}/route[{key}={prefix}]")


@router.tool()
def ping(node: str, target: str, count: int = 3) -> object:
    """Ping a target address from a node's default network instance (count 1-10)."""
    return srlinux.ping(node, target, max(1, min(count, 10)))
