"""The orchestrator's intent for the network tools: active core-link subscriptions and their customers."""

import json
import os

import httpx

ORCHESTRATOR = os.environ.get("ORCHESTRATOR_URL", "http://orchestrator:8080").rstrip("/")


def customer_name(subscription_id: str) -> str:
    """The subscription's customer name; the REST API only carries the customer id, GraphQL resolves it."""
    query = "{ subscription(id: %s) { customer { fullname } } }" % json.dumps(subscription_id)
    data = httpx.post(f"{ORCHESTRATOR}/api/graphql", json={"query": query}, timeout=20).json()
    return ((data.get("data") or {}).get("subscription") or {}).get("customer", {}).get("fullname", "unknown")


def core_link_subscriptions() -> list[dict]:
    """Active core link subscriptions with both ends, straight from the orchestrator (the intent)."""
    hits = httpx.get(f"{ORCHESTRATOR}/api/subscriptions/search", params={"query": "core link"}, timeout=20).json()
    links = []
    for hit in hits:
        if hit["status"] != "active" or not hit["description"].startswith("core link"):
            continue
        model = httpx.get(f"{ORCHESTRATOR}/api/subscriptions/domain-model/{hit['subscription_id']}", timeout=20).json()
        ports = model["core_link"]["ports"]
        links.append(
            {
                "subscription_id": hit["subscription_id"],
                "description": hit["description"],
                "customer": customer_name(hit["subscription_id"]),
                "node_a": ports[0]["node"]["node_name"],
                "interface_a": ports[0]["port_name"],
                "node_b": ports[1]["node"]["node_name"],
                "interface_b": ports[1]["port_name"],
            }
        )
    return links
