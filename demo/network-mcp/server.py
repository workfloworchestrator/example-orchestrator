"""Read-only MCP server over the containerlab SR Linux nodes.

Exposes device *state* (not config) through SR Linux's JSON-RPC interface, the
same management API the LSO Ansible playbooks use, so the network agent can
compare what the orchestrator/NetBox intend with what the devices actually do.
The tools live in tools.py as a mounted sub-server; this module is the app.
"""

from fastmcp import FastMCP
from tools import router

mcp = FastMCP(
    "network",
    instructions=(
        "Read-only state of the demo network's SR Linux nodes. Node names are the "
        "containerlab container hostnames, which equal the NetBox device names."
    ),
)
mcp.mount(router)

if __name__ == "__main__":
    mcp.run(transport="http", host="0.0.0.0", port=8000, path="/mcp")
