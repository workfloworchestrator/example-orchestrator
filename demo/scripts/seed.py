"""Seed the demo network state the workshop builds by hand, through the
orchestrator's process API, using orchestrator-core's ``Populator`` (the same
tool SURF's own devtools populators build on). Used by ``demo.py seed|reset``.

Follows the workshop's "Seeding data" page step by step:
  1. NetBox bootstrap task, then reserve the two loopback addresses it asks for
  2. three "node Nokia" subscriptions named after the containerlab nodes
  3. two "core link 10G" subscriptions following clab/srlinux01.clab.yaml

Each workflow runs against the live stack: with LSO enabled the node and core
link workflows push configuration to the SR Linux nodes and pause at
"Confirm provisioning proxy results"; ``Populator.run()`` confirms and resumes
such pauses itself. Idempotent: subscriptions that already exist are skipped,
and a create process an interrupted run left suspended is continued.

Settings: BASE_API_URL (default http://localhost:8080/api), NETBOX_URL,
NETBOX_TOKEN.
"""

import json
import logging
import os
from time import sleep

import requests
import structlog
from more_itertools import first
from orchestrator.core.devtools.populator import BASE_API_URL, JSONSchema, Populator

NETBOX = os.environ.get("NETBOX_URL", "http://localhost:8000")
NETBOX_TOKEN = os.environ.get("NETBOX_TOKEN", "nbt_sDx3hakFeTCZ.lnGwrK42a7z1IelVaigWXqaAB0GKSpbOSZKTrLdb")

CUSTOMER = "SURF"
NODE_TYPE = "Nokia 7220 IXR-D2"  # the containerlab nodes are `ixrd2`
NODES = [  # (name, site, role) — names are the containerlab container hostnames
    ("clab-orch-demo-ams-pe", "Amsterdam", "Provider Edge"),
    ("clab-orch-demo-par-p", "Paris", "Provider"),
    ("clab-orch-demo-lon-pe", "London", "Provider Edge"),
]
CORE_LINKS = [  # (node a, port a, node b, port b) — the links in clab/srlinux01.clab.yaml
    ("clab-orch-demo-ams-pe", "ethernet-1/1", "clab-orch-demo-par-p", "ethernet-1/2"),
    ("clab-orch-demo-par-p", "ethernet-1/1", "clab-orch-demo-lon-pe", "ethernet-1/2"),
]
RESERVED_LOOPBACKS = ["10.0.127.0/32", "fc00:0:0:127::/128"]

# The populator narrates every field it resolves (and warns on optional ones it
# cannot); real failures raise, so keep the log at error level.
structlog.configure(wrapper_class=structlog.make_filtering_bound_logger(logging.ERROR))
logger = structlog.get_logger(__name__)


def option_by_label(field: JSONSchema, label: str) -> str:
    """Pick a choice field's value by the label the UI shows (exact match first)."""
    options = field.get("options") or {value: value for value in field.get("enum", [])}
    exact = [value for value, option in options.items() if option == label]
    partial = [value for value, option in options.items() if label in option]
    try:
        return first(exact + partial)
    except ValueError:
        raise SystemExit(f"no option labeled {label!r}; available: {list(options.values())}") from None


class DemoPopulator(Populator):
    """Shared defaults: the workshop customer instead of the populator's SURF-internal default."""

    def __init__(self, product_name: str) -> None:
        if not hasattr(self, "log"):
            self.log = logger.bind()  # the base class needs a logger before it resolves the product
        super().__init__(product_name)

    def get_form_data(self, form: JSONSchema) -> dict:
        """Omit optional fields the populator could not resolve so the form's own defaults apply.

        The base class submits every property; read-only callouts, labels and optional
        inputs then arrive as ``None``, which the form models reject.
        """
        data = super().get_form_data(form)
        required = set(form.get("required", []))
        return {name: value for name, value in data.items() if value is not None or name in required}

    def run_task(self, task_name: str) -> None:
        """Run a workflow task (no product, no subscription): start it and answer its forms."""
        self._start_workflow(task_name)
        while not self.done:
            sleep(1)
            if self.human_input_needed():
                self.provide_user_input(
                    "PUT", BASE_API_URL / "processes" / self.process_id / "resume", self.get_current_form()
                )
        self.reset()

    def human_input_needed(self) -> bool:
        """Keep polling while LSO runs a playbook; the base class does not know ``awaiting_callback``."""
        state = self.session.get(BASE_API_URL / "processes" / self.process_id, timeout=30).json()
        if state.get("last_status") == "awaiting_callback":
            self.last_state = state
            return False
        return super().human_input_needed()

    def adopt(self, process_id: str) -> None:
        """Continue an unfinished process (left behind by an interrupted run) in ``run()``."""
        self.log = self.log.bind(process_id=process_id)
        self.process_id, self.started, self.done = process_id, True, False

    def add_default_values(self) -> None:
        super().add_default_values()
        self.default_input_values.pop("customer_id", None)

    def resolve_customer_id(self, field: JSONSchema) -> str:
        return option_by_label(field, CUSTOMER)


class NodePopulator(DemoPopulator):
    def __init__(self, name: str, site: str, role: str) -> None:
        self.log = logger.bind(node=name)
        self.name, self.site, self.role = name, site, role
        super().__init__("node Nokia")

    def add_default_values(self) -> None:
        super().add_default_values()
        self.default_input_values.update({"auto_add_interfaces": True, "node_status": "active", "node_name": self.name})

    def resolve_type_id(self, field: JSONSchema) -> str:
        return option_by_label(field, NODE_TYPE)

    def resolve_role_id(self, field: JSONSchema) -> str:
        return option_by_label(field, self.role)

    def resolve_site_id(self, field: JSONSchema) -> str:
        return option_by_label(field, self.site)


class CoreLinkPopulator(DemoPopulator):
    def __init__(self, node_a: str, port_a: str, node_b: str, port_b: str) -> None:
        self.log = logger.bind(link=f"{node_a} {port_a} <-> {port_b} {node_b}")
        self.node_a, self.port_a, self.node_b, self.port_b = node_a, port_a, node_b, port_b
        super().__init__("core link 10G")

    def add_default_values(self) -> None:
        super().add_default_values()
        self.default_input_values["under_maintenance"] = False

    def resolve_node_subscription_id_a(self, field: JSONSchema) -> str:
        return option_by_label(field, self.node_a)

    def resolve_node_subscription_id_b(self, field: JSONSchema) -> str:
        return option_by_label(field, self.node_b)

    def resolve_port_ims_id_a(self, field: JSONSchema) -> str:
        return option_by_label(field, self.port_a)

    def resolve_port_ims_id_b(self, field: JSONSchema) -> str:
        return option_by_label(field, self.port_b)


# --- helpers around the populators ------------------------------------------


IN_FLIGHT = ("active", "initial", "provisioning")


def demo_subscriptions(statuses: tuple[str, ...] = ("active",)) -> list[dict]:
    """The demo subscriptions in the given statuses, via GraphQL (the search index lags behind status changes)."""
    subscriptions = []
    for status in statuses:
        query = (
            '{ subscriptions(filterBy: [{field: "status", value: %s}], first: 500) '
            "{ page { subscriptionId status description } } }" % json.dumps(status)
        )
        page = requests.post(BASE_API_URL / "graphql", json={"query": query}, timeout=30).json()["data"][
            "subscriptions"
        ]["page"]
        subscriptions += [
            {"subscription_id": s["subscriptionId"], "status": s["status"].lower(), "description": s["description"]}
            for s in page
            if "clab-orch-demo" in s["description"]
        ]
    return subscriptions


def existing(fragment: str) -> dict | None:
    return next((s for s in demo_subscriptions(IN_FLIGHT) if fragment in s["description"]), None)


def open_process(subscription_id: str) -> str | None:
    """The subscription's unfinished process, if an earlier run left one behind."""
    query = "{ subscription(id: %s) { processes { page { processId lastStatus } } } }" % json.dumps(subscription_id)
    data = requests.post(BASE_API_URL / "graphql", json={"query": query}, timeout=30).json()
    page = data["data"]["subscription"]["processes"]["page"]
    return next((p["processId"] for p in page if p["lastStatus"] not in ("COMPLETED", "ABORTED")), None)


def ensure(populator: DemoPopulator, fragment: str, label: str) -> None:
    """Create the subscription, or finish it if an interrupted run left its process suspended."""
    sub = existing(fragment)
    if sub and sub["status"] == "active":
        print(f"  {label} exists, skipping")
        return
    if sub and (process_id := open_process(sub["subscription_id"])):
        print(f"  {label}: continuing process {process_id}")
        populator.adopt(process_id)
    else:
        populator.start_create_workflow()
    print(f"  {label}: subscription {populator.run()}")


def run_bootstrap_task() -> None:
    """The NetBox bootstrap is a task (no product); any product populator can drive it."""
    try:
        DemoPopulator("node Nokia").run_task("task_bootstrap_netbox")
        print("  bootstrap completed")
    except Exception as exc:  # NetBox rejects the duplicates when already bootstrapped
        print(f"  bootstrap task did not complete ({exc}); assuming NetBox is already bootstrapped")


def reserve_loopbacks() -> None:
    headers = {"Authorization": f"Token {NETBOX_TOKEN}"}
    for address in RESERVED_LOOPBACKS:
        response = requests.post(
            f"{NETBOX}/api/ipam/ip-addresses/",
            json={"address": address, "status": "reserved"},
            headers=headers,
            timeout=30,
        )
        if response.status_code == 400 and "Duplicate" in response.text:
            print(f"  {address} already registered in NetBox, skipping")
        else:
            print(f"  reserved {address} ({response.status_code})")


def reset() -> None:
    """Terminate the demo subscriptions (core links first, then nodes) with each product's terminate workflow."""
    for kind, product in (("core link", "core link 10G"), ("node", "node Nokia")):
        # re-query per kind: terminating the core links changes what is left to terminate
        for sub in [s for s in demo_subscriptions() if s["description"].startswith(kind)]:
            print(f"  terminating {sub['description']}")
            populator = DemoPopulator(product)
            populator.start_terminate_workflow(sub["subscription_id"])
            populator.run()


def seed(dry_run: bool = False) -> None:
    """Bootstrap NetBox, then create the nodes and core links that are not there yet."""
    print("1. NetBox bootstrap")
    if not dry_run:
        run_bootstrap_task()
        reserve_loopbacks()

    print("2. nodes")
    for name, site, role in NODES:
        if dry_run:
            state = "exists" if existing(f"node {name}") else f"would create ({NODE_TYPE}, {role}, {site})"
            print(f"  node {name}: {state}")
            continue
        ensure(NodePopulator(name, site, role), f"node {name}", name)

    print("3. core links")
    for node_a, port_a, node_b, port_b in CORE_LINKS:
        fragment = f"{node_a} {port_a} <-> {port_b} {node_b}"
        if dry_run:
            print(f"  core link {fragment}: {'exists' if existing(fragment) else 'would create'}")
            continue
        ensure(CoreLinkPopulator(node_a, port_a, node_b, port_b), fragment, f"{node_a} <-> {node_b}")
    print("done")
