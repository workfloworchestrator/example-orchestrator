"""Keep the two LibreChat routes usable together, including workflow forms."""

import json
import os
import shutil
import subprocess
import tomllib
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]


def test_workflow_model_has_a_direct_form_capable_connection():
    config = yaml.safe_load((ROOT / "docker/librechat/librechat.yaml").read_text())
    spec = next(spec for spec in config["modelSpecs"]["list"] if spec["name"] == "wfo")
    endpoint = next(
        endpoint for endpoint in config["endpoints"]["custom"] if endpoint["name"] == spec["preset"]["endpoint"]
    )

    assert spec["askUserQuestion"] is True
    assert spec["label"] == "WFO (HITL)"
    assert spec["preset"]["model"] in endpoint["models"]["default"]
    assert endpoint["baseURL"] == "http://wfo-agent:8080/v1"
    assert endpoint["headers"]["X-Agent-Client"] == "librechat"
    assert endpoint["headers"]["X-Conversation-Id"] == "{{LIBRECHAT_BODY_CONVERSATIONID}}"
    assert endpoint["titleConvo"] is False
    # The preset supplies HITL; the raw endpoint would duplicate it without forms.
    assert endpoint["name"] not in config["modelSpecs"]["addedEndpoints"]


def test_planner_is_still_selectable_alongside_model_specs():
    config = yaml.safe_load((ROOT / "docker/librechat/librechat.yaml").read_text())
    endpoint = next(
        endpoint for endpoint in config["endpoints"]["custom"] if "planner" in endpoint["models"]["default"]
    )

    # LibreChat filters by the custom endpoint's name, not the word "custom".
    assert endpoint["name"] in config["modelSpecs"]["addedEndpoints"]
    assert endpoint["baseURL"] == "http://a2a-proxy:8080/v1"
    assert endpoint["titleConvo"] is False


def test_core_package_lock_and_image_versions_match():
    project = tomllib.loads((ROOT / "pyproject.toml").read_text())
    locked = tomllib.loads((ROOT / "uv.lock").read_text())
    compose = yaml.safe_load((ROOT / "docker-compose.yml").read_text())
    dependency = next(dep for dep in project["project"]["dependencies"] if dep.startswith("orchestrator-core["))
    version = dependency.split("==", 1)[1]
    core = next(package for package in locked["package"] if package["name"] == "orchestrator-core")

    assert core["version"] == version
    assert compose["services"]["orchestrator"]["image"] == (
        "${ORCH_BACKEND_TAG:-ghcr.io/workfloworchestrator/orchestrator-core:" + version + "}"
    )


def compose_config(*overlays):
    compose = shutil.which("docker-compose") or "/usr/libexec/docker/cli-plugins/docker-compose"
    command = [compose] if Path(compose).is_file() else ["docker", "compose"]
    env = {**os.environ, "AGENT_API_KEY": "compose-config-test"}
    result = subprocess.run(
        [
            *command,
            "--profile",
            "agents",
            "-f",
            "docker-compose.yml",
            *(argument for overlay in overlays for argument in ("-f", overlay)),
            "config",
            "--format",
            "json",
        ],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(result.stdout)


def test_agui_overlay_builds_the_ui_and_keeps_the_agent_on_the_server():
    ui = compose_config("docker-compose.agui.yml")["services"]["orchestrator-ui"]
    assert ui["environment"]["ORCHESTRATOR_AGENT_URL"] == "/api/agent/agui/"
    assert ui["environment"]["ORCHESTRATOR_AGENT_UPSTREAM"] == "http://wfo-agent:8080"
    assert "wfo-agent" in ui["depends_on"]
    assert ui["build"]["context"].endswith("example-orchestrator-ui")
    base = yaml.safe_load((ROOT / "docker-compose.yml").read_text())
    assert "ORCHESTRATOR_AGENT_URL" not in base["services"]["orchestrator-ui"].get("environment", {})


def test_selinux_overlay_labels_all_orchestrator_and_planner_bind_mounts():
    base = compose_config("docker-compose.agui.yml")["services"]
    labeled = compose_config("docker-compose.agui.yml", "selinux-override.yml")["services"]

    for service in ("orchestrator", "planner-agent"):
        mounts = {mount["target"]: mount for mount in labeled[service]["volumes"]}
        for original in base[service]["volumes"]:
            if original["type"] != "bind":
                continue
            mount = mounts[original["target"]]
            assert mount["source"] == original["source"]
            assert mount.get("read_only", False) == original.get("read_only", False)
            assert mount["bind"].get("selinux") == "z", f"{service}: {mount['target']}"
