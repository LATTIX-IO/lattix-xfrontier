from __future__ import annotations

import sys
import types
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

platform_services = types.ModuleType("app.platform_services")


class _DummyService:
    def __init__(self, *_args: object, **_kwargs: object) -> None:
        pass


platform_services.Neo4jRunGraph = _DummyService
platform_services.PostgresStateStore = _DummyService
platform_services.RedisMemoryStore = _DummyService
sys.modules.setdefault("app.platform_services", platform_services)

from app.main import app, store


client = TestClient(app)


def _sample_graph() -> dict[str, list[dict[str, object]]]:
    return {
        "nodes": [
            {"id": "trigger", "title": "Trigger", "type": "trigger", "x": 70, "y": 90, "config": {"trigger_mode": "manual"}},
            {"id": "prompt", "title": "Prompt", "type": "prompt", "x": 280, "y": 90, "config": {"system_prompt_text": "Help the user safely."}},
            {"id": "agent", "title": "Agent", "type": "agent", "x": 520, "y": 90, "config": {"agent_id": "generated-agent", "model": "gpt-5.2"}},
            {"id": "output", "title": "Output", "type": "output", "x": 790, "y": 90, "config": {"destination": "artifact_store", "format": "json"}},
        ],
        "links": [
            {"from": "trigger", "to": "agent", "from_port": "out", "to_port": "in"},
            {"from": "prompt", "to": "agent", "from_port": "prompt", "to_port": "prompt"},
            {"from": "agent", "to": "output", "from_port": "out", "to_port": "in"},
            {"from": "agent", "to": "output", "from_port": "response", "to_port": "result"},
        ],
    }


def test_publish_agent_definition_generates_code_artifacts() -> None:
    agent_id = str(uuid4())
    payload = {
        "id": agent_id,
        "name": "Generated Agent Test",
        "config_json": {
            "graph_json": _sample_graph(),
            "security": {
                "classification": "restricted",
                "allowed_runtime_engines": ["native", "langgraph"],
                "blocked_keywords": ["secret"],
            },
        },
    }

    save_response = client.post("/agent-definitions", json=payload)
    assert save_response.status_code == 200

    publish_response = client.post(f"/agent-definitions/{agent_id}/publish")
    assert publish_response.status_code == 200
    body = publish_response.json()
    assert body["ok"] is True
    assert len(body["generated_artifacts"]) == 2
    assert {artifact["framework"] for artifact in body["generated_artifacts"]} == {
        "langgraph",
        "microsoft-agent-framework",
    }

    detail_response = client.get(f"/agent-definitions/{agent_id}")
    assert detail_response.status_code == 200
    detail = detail_response.json()
    assert len(detail["generated_artifacts"]) == 2
    langgraph_artifact = next(artifact for artifact in detail["generated_artifacts"] if artifact["framework"] == "langgraph")
    assert "EFFECTIVE_SECURITY_POLICY" in langgraph_artifact["content"]
    assert "restricted" in langgraph_artifact["content"]
    assert langgraph_artifact["path"].endswith("langgraph_agent.py")

    artifact_response = client.get(f"/artifacts/{langgraph_artifact['id']}")
    assert artifact_response.status_code == 200
    artifact_detail = artifact_response.json()
    assert artifact_detail["framework"] == "langgraph"
    assert artifact_detail["entity_type"] == "agent"
    assert artifact_detail["content"] == langgraph_artifact["content"]

    store.agent_definitions.pop(agent_id, None)
    store.artifacts = [artifact for artifact in store.artifacts if artifact.id not in {item['id'] for item in body['generated_artifacts']}]


def test_publish_workflow_definition_generates_code_artifacts() -> None:
    workflow_id = str(uuid4())
    payload = {
        "id": workflow_id,
        "name": "Generated Workflow Test",
        "description": "Workflow publish should emit code scaffolds.",
        "graph_json": _sample_graph(),
        "security_config": {
            "classification": "confidential",
            "allowed_runtime_engines": ["native", "langgraph"],
            "require_human_approval": True,
        },
    }

    save_response = client.post("/workflow-definitions", json=payload)
    assert save_response.status_code == 200

    publish_response = client.post(f"/workflow-definitions/{workflow_id}/publish")
    assert publish_response.status_code == 200
    body = publish_response.json()
    assert body["ok"] is True
    assert len(body["generated_artifacts"]) == 2

    maf_artifact = next(artifact for artifact in body["generated_artifacts"] if artifact["framework"] == "microsoft-agent-framework")
    assert "AzureAIClient" in maf_artifact["content"]
    assert "GRAPH_SPEC" in maf_artifact["content"]

    detail_response = client.get(f"/workflow-definitions/{workflow_id}")
    assert detail_response.status_code == 200
    detail = detail_response.json()
    assert len(detail["generated_artifacts"]) == 2

    artifact_list_response = client.get("/artifacts")
    assert artifact_list_response.status_code == 200
    artifact_ids = {artifact["id"] for artifact in artifact_list_response.json()}
    assert maf_artifact["id"] in artifact_ids

    store.workflow_definitions.pop(workflow_id, None)
    store.artifacts = [artifact for artifact in store.artifacts if artifact.id not in {item['id'] for item in body['generated_artifacts']}]
