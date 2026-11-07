from pathlib import Path

import pytest


def test_workflow_gates_deployment_and_declares_runtime():
    yaml = pytest.importorskip("yaml")
    root = Path(__file__).resolve().parents[1]
    workflow = yaml.safe_load((root / ".github/workflows/digest.yml").read_text(encoding="utf-8"))
    assert workflow["permissions"] == {"contents": "read"}
    build = workflow["jobs"]["build"]
    steps = build["steps"]
    names = [step["name"] for step in steps]
    refresh = next(step for step in steps if step["name"] == "Refresh digest")
    assert not any(step.get("continue-on-error") for step in steps)
    assert names.index("Refresh digest") < names.index("Validate current publication") < names.index("Upload Pages artifact")
    validation = next(step for step in steps if step["name"] == "Validate current publication")
    assert '--run-id "$DIGEST_RUN_ID"' in validation["run"]
    assert "github.run_attempt" in build["env"]["DIGEST_RUN_ID"]
    assert refresh["env"]["DIGEST_REQUIRE_EMBEDDINGS"] == "true"
    assert refresh["env"]["OLLAMA_HOST"] == "http://127.0.0.1:1"
    assert names.index("Prepare required embedding model") < names.index("Refresh digest")
    install = next(step for step in steps if step["name"] == "Install dependencies")
    assert '-e ".[dev]"' in install["run"]
    assert next(step for step in steps if step["name"] == "Set up Python")["with"]["python-version"] == "3.11"
    deploy = workflow["jobs"]["deploy"]
    assert deploy["needs"] == "build"
    assert "needs.build.result == 'success'" in deploy["if"]
    assert deploy["permissions"] == {"pages": "write", "id-token": "write"}
    assert all("always()" not in str(step.get("if", "")) for step in steps)
