"""Keep the two LibreChat routes usable together, including workflow forms."""

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
    assert spec["preset"]["model"] in endpoint["models"]["default"]
    assert endpoint["baseURL"] == "http://wfo-agent:8080/v1"
    assert endpoint["headers"]["X-Agent-Client"] == "librechat"
    assert endpoint["headers"]["X-Conversation-Id"] == "{{LIBRECHAT_BODY_CONVERSATIONID}}"
    assert endpoint["titleConvo"] is False
    assert endpoint["name"] in config["modelSpecs"]["addedEndpoints"]


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
