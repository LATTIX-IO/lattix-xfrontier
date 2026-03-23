from __future__ import annotations

import os
import sys
import types
from collections import defaultdict
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient
from frontier_runtime.security import mint_token

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

platform_services = types.ModuleType("app.platform_services")


class _FakePostgresStateStore:
    def __init__(self, *_args: object, **_kwargs: object) -> None:
        self.enabled = True
        self._payload: dict[str, object] | None = None

    def initialize(self) -> None:
        return

    def load_state(self) -> dict[str, object] | None:
        return self._payload

    def save_state(self, payload: dict[str, object]) -> None:
        self._payload = dict(payload)


class _FakeRedisMemoryStore:
    def __init__(self, *_args: object, **_kwargs: object) -> None:
        self.enabled = True
        self._entries: dict[str, list[dict[str, object]]] = defaultdict(list)

    def healthcheck(self) -> bool:
        return True

    def get_entries(self, session_id: str, *, limit: int = 100) -> list[dict[str, object]]:
        return self._entries.get(session_id, [])[-limit:]

    def append_entry(self, session_id: str, entry: dict[str, object]) -> None:
        self._entries.setdefault(session_id, []).append(dict(entry))

    def load_entries(self, session_id: str, entries: list[dict[str, object]]) -> None:
        for entry in entries:
            self.append_entry(session_id, entry)

    def clear_entries(self, session_id: str) -> None:
        self._entries[session_id] = []


class _FakeLongTermMemoryStore:
    def __init__(self, *_args: object, **_kwargs: object) -> None:
        self.enabled = True
        self._entries: dict[tuple[str, str, str], list[dict[str, object]]] = defaultdict(list)
        self._consolidation_candidates: dict[str, dict[str, object]] = {}

    def initialize(self) -> None:
        return

    def healthcheck(self) -> bool:
        return True

    def append_entry(
        self,
        *,
        bucket_id: str,
        session_id: str,
        memory_scope: str,
        entry: dict[str, object],
        source: str,
        task_id: str | None = None,
    ) -> None:
        payload = dict(entry)
        payload.setdefault("bucket_id", bucket_id)
        payload.setdefault("session_id", session_id)
        payload.setdefault("memory_scope", memory_scope)
        payload.setdefault("source", source)
        payload.setdefault("task_id", task_id or "")
        payload.setdefault("tier", "long-term")
        self._entries[(bucket_id, session_id, memory_scope)].append(payload)

    def get_entries(
        self,
        *,
        bucket_id: str | None = None,
        session_id: str | None = None,
        memory_scope: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, object]]:
        matches: list[dict[str, object]] = []
        for (stored_bucket, stored_session, stored_scope), entries in self._entries.items():
            if bucket_id and stored_bucket != bucket_id:
                continue
            if session_id and stored_session != session_id:
                continue
            if memory_scope and stored_scope != memory_scope:
                continue
            matches.extend(dict(item) for item in entries)
        return matches[-limit:]

    def search_entries(
        self,
        query_text: str,
        *,
        bucket_id: str | None = None,
        session_id: str | None = None,
        memory_scope: str | None = None,
        limit: int = 10,
    ) -> list[dict[str, object]]:
        needle = str(query_text or "").lower()
        matches = [
            entry
            for entry in self.get_entries(bucket_id=bucket_id, session_id=session_id, memory_scope=memory_scope, limit=1000)
            if needle in str(entry.get("content") or "").lower()
        ]
        return matches[:limit] if matches else self.get_entries(bucket_id=bucket_id, session_id=session_id, memory_scope=memory_scope, limit=limit)

    def clear_entries(
        self,
        *,
        bucket_id: str | None = None,
        session_id: str | None = None,
        memory_scope: str | None = None,
    ) -> None:
        to_delete: list[tuple[str, str, str]] = []
        for key in self._entries:
            stored_bucket, stored_session, stored_scope = key
            if bucket_id and stored_bucket != bucket_id:
                continue
            if session_id and stored_session != session_id:
                continue
            if memory_scope and stored_scope != memory_scope:
                continue
            to_delete.append(key)
        for key in to_delete:
            self._entries.pop(key, None)

    def enqueue_consolidation_candidate(
        self,
        *,
        bucket_id: str,
        session_id: str,
        memory_scope: str,
        entry: dict[str, object],
        source: str,
        task_id: str | None = None,
        candidate_kind: str = "promotion",
    ) -> None:
        entry_id = str(entry.get("id") or uuid4())
        candidate_id = f"consolidation:{entry_id}"
        payload = dict(entry)
        payload.update(
            {
                "id": candidate_id,
                "entry_id": entry_id,
                "bucket_id": bucket_id,
                "session_id": session_id,
                "memory_scope": memory_scope,
                "source": source,
                "task_id": task_id or "",
                "candidate_kind": candidate_kind,
                "status": "pending",
            }
        )
        self._consolidation_candidates[candidate_id] = payload

    def list_consolidation_candidates(
        self,
        *,
        bucket_id: str | None = None,
        memory_scope: str | None = None,
        status: str | None = "pending",
        limit: int = 100,
    ) -> list[dict[str, object]]:
        items = list(self._consolidation_candidates.values())
        if bucket_id:
            items = [item for item in items if str(item.get("bucket_id") or "") == bucket_id]
        if memory_scope:
            items = [item for item in items if str(item.get("memory_scope") or "") == memory_scope]
        if status:
            items = [item for item in items if str(item.get("status") or "") == status]
        return items[-limit:]

    def mark_consolidation_candidate(
        self,
        candidate_id: str,
        *,
        status: str,
        extra_metadata: dict[str, object] | None = None,
    ) -> None:
        candidate = self._consolidation_candidates.get(candidate_id)
        if not candidate:
            return
        candidate["status"] = status
        if extra_metadata:
            metadata = candidate.get("metadata") if isinstance(candidate.get("metadata"), dict) else {}
            metadata.update(extra_metadata)
            candidate["metadata"] = metadata
        self._consolidation_candidates[candidate_id] = candidate


class _FakeNeo4jRunGraph:
    def __init__(self, *_args: object, **_kwargs: object) -> None:
        self.enabled = True
        self.run_records: list[dict[str, object]] = []
        self.memory_projections: list[dict[str, object]] = []

    def healthcheck(self) -> bool:
        return True

    def record_run(self, **_kwargs: object) -> None:
        self.run_records.append(dict(_kwargs))

    def project_memory_summary(self, *, projection: dict[str, object]) -> None:
        self.memory_projections.append(dict(projection))

    def query_memory_context(
        self,
        *,
        bucket_id: str,
        memory_scope: str,
        query_text: str = "",
        limit: int = 10,
    ) -> dict[str, object]:
        owner_id = f"owner:{bucket_id}"
        projections = [
            projection
            for projection in self.memory_projections
            if str(projection.get("owner", {}).get("id") or "") == owner_id
        ]
        memories = []
        topics_by_id: dict[str, dict[str, object]] = {}
        relations: list[dict[str, object]] = []
        query = str(query_text or "").lower().strip()
        for projection in projections[-limit:]:
            memory = projection.get("memory") if isinstance(projection.get("memory"), dict) else {}
            content = str(memory.get("content") or "")
            if query and query not in content.lower():
                continue
            if memory:
                payload = dict(memory)
                payload.setdefault("tier", "world-graph")
                memories.append(payload)
            for topic in projection.get("topics", []):
                if isinstance(topic, dict) and str(topic.get("id") or ""):
                    topics_by_id[str(topic.get("id") or "")] = dict(topic)
            for relation in projection.get("relations", []):
                if isinstance(relation, dict):
                    relations.append(dict(relation))
        return {
            "memories": memories[-limit:],
            "topics": list(topics_by_id.values())[:limit],
            "relations": relations[:limit * 3],
        }


platform_services.Neo4jRunGraph = _FakeNeo4jRunGraph
platform_services.PostgresStateStore = _FakePostgresStateStore
platform_services.PostgresLongTermMemoryStore = _FakeLongTermMemoryStore
platform_services.RedisMemoryStore = _FakeRedisMemoryStore
sys.modules.setdefault("app.platform_services", platform_services)

import app.main as main_module
from app.main import app, store
from app.request_security import validate_route_inventory


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


def test_workflow_definition_defaults_graph_schema_version_when_missing() -> None:
    workflow_id = str(uuid4())
    payload = {
        "id": workflow_id,
        "name": "Schema Version Workflow",
        "description": "Workflow save should normalize graph schema version.",
        "graph_json": _sample_graph(),
    }

    response = client.post("/workflow-definitions", json=payload)
    assert response.status_code == 200

    stored = store.workflow_definitions[workflow_id]
    assert stored.graph_json.get("schema_version") == "frontier-graph/1.0"

    store.workflow_definitions.pop(workflow_id, None)


def test_workflow_definition_rejects_unsupported_graph_schema_version() -> None:
    workflow_id = str(uuid4())
    payload = {
        "id": workflow_id,
        "name": "Unsupported Schema Workflow",
        "description": "Workflow save should reject unsupported graph schema versions.",
        "graph_json": {
            **_sample_graph(),
            "schema_version": "frontier-graph/9.9",
        },
    }

    response = client.post("/workflow-definitions", json=payload)
    assert response.status_code == 400
    detail = response.json()["detail"]
    assert "unsupported graph schema version" in detail["message"].lower()
    assert detail["issues"][0]["code"] == "GRAPH_SCHEMA_VERSION_UNSUPPORTED"
    assert workflow_id not in store.workflow_definitions


def test_graph_run_rejects_unsupported_graph_schema_version() -> None:
    response = client.post(
        "/graph/runs",
        json={
            "schema_version": "frontier-graph/2.0",
            "nodes": _sample_graph()["nodes"],
            "links": _sample_graph()["links"],
            "input": {"message": "hello"},
        },
    )

    assert response.status_code == 400
    detail = response.json()["detail"]
    assert detail["message"] == "Graph validation failed"
    assert detail["validation"]["issues"][0]["code"] == "GRAPH_SCHEMA_VERSION_UNSUPPORTED"


def test_workflow_definition_versions_and_rollback_restore_prior_snapshot() -> None:
    workflow_id = str(uuid4())
    original_artifacts = list(store.artifacts)

    try:
        save_v1 = client.post(
            "/workflow-definitions",
            json={
                "id": workflow_id,
                "name": "Initial Workflow",
                "description": "First draft of the workflow.",
                "graph_json": _sample_graph(),
            },
        )
        assert save_v1.status_code == 200

        updated_graph = _sample_graph()
        updated_graph["nodes"][1]["config"] = {"system_prompt_text": "Use the updated instructions."}
        save_v2 = client.post(
            "/workflow-definitions",
            json={
                "id": workflow_id,
                "name": "Updated Workflow",
                "description": "Second draft of the workflow.",
                "graph_json": updated_graph,
            },
        )
        assert save_v2.status_code == 200

        publish = client.post(f"/workflow-definitions/{workflow_id}/publish")
        assert publish.status_code == 200

        versions_response = client.get(f"/workflow-definitions/{workflow_id}/versions")
        assert versions_response.status_code == 200
        versions = versions_response.json()["versions"]
        assert [item["action"] for item in versions] == ["publish", "save", "save"]

        initial_revision = next(item for item in versions if item["action"] == "save" and item["version"] == 1)
        revision_detail = client.get(f"/workflow-definitions/{workflow_id}/versions/{initial_revision['id']}")
        assert revision_detail.status_code == 200
        assert revision_detail.json()["snapshot"]["name"] == "Initial Workflow"

        rollback = client.post(
            f"/workflow-definitions/{workflow_id}/rollback",
            json={"revision_id": initial_revision["id"]},
        )
        assert rollback.status_code == 200
        rollback_body = rollback.json()
        assert rollback_body["status"] == "draft"
        assert rollback_body["version"] == 4
        assert rollback_body["restored_from"]["id"] == initial_revision["id"]

        restored = store.workflow_definitions[workflow_id]
        assert restored.name == "Initial Workflow"
        assert restored.description == "First draft of the workflow."
        assert restored.generated_artifacts == []

        versions_after = client.get(f"/workflow-definitions/{workflow_id}/versions").json()["versions"]
        assert versions_after[0]["action"] == "rollback"
        assert versions_after[0]["metadata"]["source_revision_id"] == initial_revision["id"]
    finally:
        store.workflow_definitions.pop(workflow_id, None)
        store.workflow_definition_revisions.pop(workflow_id, None)
        store.artifacts = original_artifacts


def test_agent_definition_versions_and_rollback_clear_generated_artifacts() -> None:
    agent_id = str(uuid4())
    original_artifacts = list(store.artifacts)

    try:
        save_v1 = client.post(
            "/agent-definitions",
            json={
                "id": agent_id,
                "name": "Versioned Agent",
                "config_json": {
                    "system_prompt": "Respond with the original voice.",
                    "graph_json": _sample_graph(),
                },
            },
        )
        assert save_v1.status_code == 200

        publish = client.post(f"/agent-definitions/{agent_id}/publish")
        assert publish.status_code == 200
        assert len(store.agent_definitions[agent_id].generated_artifacts) == 2

        changed_graph = _sample_graph()
        changed_graph["nodes"][2]["config"] = {"agent_id": "generated-agent", "model": "gpt-5.4"}
        save_v2 = client.post(
            "/agent-definitions",
            json={
                "id": agent_id,
                "name": "Versioned Agent v2",
                "config_json": {
                    "system_prompt": "Respond with the updated voice.",
                    "graph_json": changed_graph,
                },
            },
        )
        assert save_v2.status_code == 200

        versions_response = client.get(f"/agent-definitions/{agent_id}/versions")
        assert versions_response.status_code == 200
        versions = versions_response.json()["versions"]
        assert [item["action"] for item in versions] == ["save", "publish", "save"]

        published_revision = next(item for item in versions if item["action"] == "publish")
        rollback = client.post(
            f"/agent-definitions/{agent_id}/rollback",
            json={"revision_id": published_revision["id"]},
        )
        assert rollback.status_code == 200
        rollback_body = rollback.json()
        assert rollback_body["status"] == "draft"
        assert rollback_body["version"] == 4

        restored = store.agent_definitions[agent_id]
        assert restored.name == "Versioned Agent"
        assert restored.generated_artifacts == []
        assert restored.config_json["system_prompt"] == "Respond with the original voice."

        versions_after = client.get(f"/agent-definitions/{agent_id}/versions").json()["versions"]
        assert versions_after[0]["action"] == "rollback"
        assert versions_after[0]["metadata"]["source_revision_id"] == published_revision["id"]
    finally:
        store.agent_definitions.pop(agent_id, None)
        store.agent_definition_revisions.pop(agent_id, None)
        store.artifacts = original_artifacts


def test_guardrail_ruleset_versions_and_rollback_restore_prior_config() -> None:
    ruleset_id = str(uuid4())

    try:
        save_v1 = client.post(
            "/guardrail-rulesets",
            json={
                "id": ruleset_id,
                "name": "Versioned Guardrail",
                "config_json": {"blocked_keywords": ["secret"], "tripwire_action": "reject_content"},
            },
        )
        assert save_v1.status_code == 200

        publish = client.post(f"/guardrail-rulesets/{ruleset_id}/publish")
        assert publish.status_code == 200

        save_v2 = client.post(
            "/guardrail-rulesets",
            json={
                "id": ruleset_id,
                "name": "Versioned Guardrail v2",
                "config_json": {"blocked_keywords": ["secret", "token"], "tripwire_action": "reject_content"},
            },
        )
        assert save_v2.status_code == 200

        versions_response = client.get(f"/guardrail-rulesets/{ruleset_id}/versions")
        assert versions_response.status_code == 200
        versions = versions_response.json()["versions"]
        assert [item["action"] for item in versions] == ["save", "publish", "save"]

        published_revision = next(item for item in versions if item["action"] == "publish")
        revision_detail = client.get(f"/guardrail-rulesets/{ruleset_id}/versions/{published_revision['id']}")
        assert revision_detail.status_code == 200
        assert revision_detail.json()["snapshot"]["status"] == "published"

        rollback = client.post(
            f"/guardrail-rulesets/{ruleset_id}/rollback",
            json={"revision_id": published_revision["id"]},
        )
        assert rollback.status_code == 200
        rollback_body = rollback.json()
        assert rollback_body["status"] == "draft"
        assert rollback_body["version"] == 4

        restored = store.guardrail_rulesets[ruleset_id]
        assert restored.name == "Versioned Guardrail"
        assert restored.config_json["blocked_keywords"] == ["secret"]

        versions_after = client.get(f"/guardrail-rulesets/{ruleset_id}/versions").json()["versions"]
        assert versions_after[0]["action"] == "rollback"
        assert versions_after[0]["metadata"]["source_revision_id"] == published_revision["id"]
    finally:
        store.guardrail_rulesets.pop(ruleset_id, None)
        store.guardrail_ruleset_revisions.pop(ruleset_id, None)


def test_workflow_save_after_publish_preserves_active_published_snapshot() -> None:
    workflow_id = str(uuid4())

    try:
        create = client.post(
            "/workflow-definitions",
            json={
                "id": workflow_id,
                "name": "Published Workflow",
                "description": "First published description.",
                "graph_json": _sample_graph(),
            },
        )
        assert create.status_code == 200

        publish = client.post(f"/workflow-definitions/{workflow_id}/publish")
        assert publish.status_code == 200
        published_pointer = store.workflow_definitions[workflow_id].published_revision_id
        assert published_pointer

        edit_after_publish = client.post(
            "/workflow-definitions",
            json={
                "id": workflow_id,
                "name": "Published Workflow Draft",
                "description": "Unpublished draft change.",
                "graph_json": _sample_graph(),
            },
        )
        assert edit_after_publish.status_code == 200

        current = store.workflow_definitions[workflow_id]
        assert current.status == "draft"
        assert current.published_revision_id == published_pointer

        published_listing = client.get("/workflows/published")
        assert published_listing.status_code == 200
        published_workflow = next(item for item in published_listing.json() if item["id"] == workflow_id)
        assert published_workflow["name"] == "Published Workflow"
        assert published_workflow["description"] == "First published description."
    finally:
        store.workflow_definitions.pop(workflow_id, None)
        store.workflow_definition_revisions.pop(workflow_id, None)


def test_agent_and_guardrail_runtime_resolution_use_pinned_published_revisions() -> None:
    agent_id = str(uuid4())
    ruleset_id = str(uuid4())

    try:
        ruleset_create = client.post(
            "/guardrail-rulesets",
            json={
                "id": ruleset_id,
                "name": "Pinned Ruleset",
                "config_json": {"blocked_keywords": ["alpha"], "tripwire_action": "reject_content"},
            },
        )
        assert ruleset_create.status_code == 200
        ruleset_publish = client.post(f"/guardrail-rulesets/{ruleset_id}/publish")
        assert ruleset_publish.status_code == 200
        published_ruleset_pointer = store.guardrail_rulesets[ruleset_id].published_revision_id
        assert published_ruleset_pointer

        ruleset_draft = client.post(
            "/guardrail-rulesets",
            json={
                "id": ruleset_id,
                "name": "Pinned Ruleset Draft",
                "config_json": {"blocked_keywords": ["beta"], "tripwire_action": "reject_content"},
            },
        )
        assert ruleset_draft.status_code == 200
        assert store.guardrail_rulesets[ruleset_id].status == "draft"
        assert store.guardrail_rulesets[ruleset_id].published_revision_id == published_ruleset_pointer

        workflow_using_ruleset = client.post(
            "/workflow-definitions",
            json={
                "id": str(uuid4()),
                "name": "Ruleset Consumer",
                "description": "Should validate against pinned published ruleset.",
                "graph_json": _sample_graph(),
                "security_config": {"guardrail_ruleset_id": ruleset_id},
            },
        )
        assert workflow_using_ruleset.status_code == 200

        agent_create = client.post(
            "/agent-definitions",
            json={
                "id": agent_id,
                "name": "Pinned Agent",
                "config_json": {
                    "system_prompt": "Published system prompt.",
                    "graph_json": _sample_graph(),
                },
            },
        )
        assert agent_create.status_code == 200
        agent_publish = client.post(f"/agent-definitions/{agent_id}/publish")
        assert agent_publish.status_code == 200
        published_agent_pointer = store.agent_definitions[agent_id].published_revision_id
        assert published_agent_pointer

        agent_draft = client.post(
            "/agent-definitions",
            json={
                "id": agent_id,
                "name": "Pinned Agent Draft",
                "config_json": {
                    "system_prompt": "Draft system prompt.",
                    "graph_json": _sample_graph(),
                },
            },
        )
        assert agent_draft.status_code == 200
        assert store.agent_definitions[agent_id].status == "draft"
        assert store.agent_definitions[agent_id].published_revision_id == published_agent_pointer

        resolved_published_agent = main_module._resolve_published_agent_definition(agent_id)
        assert resolved_published_agent is not None
        assert resolved_published_agent.name == "Pinned Agent"
        assert resolved_published_agent.config_json["system_prompt"] == "Published system prompt."
    finally:
        store.agent_definitions.pop(agent_id, None)
        store.agent_definition_revisions.pop(agent_id, None)
        store.guardrail_rulesets.pop(ruleset_id, None)
        store.guardrail_ruleset_revisions.pop(ruleset_id, None)
        for workflow_key, workflow in list(store.workflow_definitions.items()):
            if workflow.name == "Ruleset Consumer":
                store.workflow_definitions.pop(workflow_key, None)
                store.workflow_definition_revisions.pop(workflow_key, None)


def test_republish_requires_explicit_activation_before_runtime_moves_forward() -> None:
    workflow_id = str(uuid4())

    try:
        create_v1 = client.post(
            "/workflow-definitions",
            json={
                "id": workflow_id,
                "name": "Release Workflow v1",
                "description": "Initial active release.",
                "graph_json": _sample_graph(),
            },
        )
        assert create_v1.status_code == 200

        publish_v1 = client.post(f"/workflow-definitions/{workflow_id}/publish")
        assert publish_v1.status_code == 200

        first_release = store.workflow_definitions[workflow_id]
        first_published_revision_id = first_release.published_revision_id
        first_active_revision_id = first_release.active_revision_id
        assert first_published_revision_id
        assert first_active_revision_id == first_published_revision_id

        create_v2 = client.post(
            "/workflow-definitions",
            json={
                "id": workflow_id,
                "name": "Release Workflow v2",
                "description": "Second published release waiting on activation.",
                "graph_json": _sample_graph(),
            },
        )
        assert create_v2.status_code == 200

        publish_v2 = client.post(f"/workflow-definitions/{workflow_id}/publish")
        assert publish_v2.status_code == 200

        current = store.workflow_definitions[workflow_id]
        assert current.published_revision_id
        assert current.published_revision_id != first_published_revision_id
        assert current.active_revision_id == first_active_revision_id

        published_listing = client.get("/workflows/published")
        assert published_listing.status_code == 200
        published_workflow = next(item for item in published_listing.json() if item["id"] == workflow_id)
        assert published_workflow["name"] == "Release Workflow v2"
        assert published_workflow["description"] == "Second published release waiting on activation."

        active_listing = client.get("/workflows/active")
        assert active_listing.status_code == 200
        active_workflow = next(item for item in active_listing.json() if item["id"] == workflow_id)
        assert active_workflow["name"] == "Release Workflow v1"
        assert active_workflow["description"] == "Initial active release."

        activate = client.post(f"/workflow-definitions/{workflow_id}/activate")
        assert activate.status_code == 200
        assert activate.json()["active_revision"]["id"] == current.published_revision_id

        active_listing_after = client.get("/workflows/active")
        assert active_listing_after.status_code == 200
        active_workflow_after = next(item for item in active_listing_after.json() if item["id"] == workflow_id)
        assert active_workflow_after["name"] == "Release Workflow v2"
    finally:
        store.workflow_definitions.pop(workflow_id, None)
        store.workflow_definition_revisions.pop(workflow_id, None)


def test_agent_and_guardrail_activation_control_runtime_resolution() -> None:
    agent_id = str(uuid4())
    ruleset_id = str(uuid4())

    try:
        ruleset_v1 = client.post(
            "/guardrail-rulesets",
            json={
                "id": ruleset_id,
                "name": "Runtime Ruleset v1",
                "config_json": {"blocked_keywords": ["alpha"], "tripwire_action": "reject_content"},
            },
        )
        assert ruleset_v1.status_code == 200
        assert client.post(f"/guardrail-rulesets/{ruleset_id}/publish").status_code == 200

        ruleset_v2 = client.post(
            "/guardrail-rulesets",
            json={
                "id": ruleset_id,
                "name": "Runtime Ruleset v2",
                "config_json": {"blocked_keywords": ["beta"], "tripwire_action": "reject_content"},
            },
        )
        assert ruleset_v2.status_code == 200
        assert client.post(f"/guardrail-rulesets/{ruleset_id}/publish").status_code == 200

        guardrail_current = store.guardrail_rulesets[ruleset_id]
        assert guardrail_current.published_revision_id
        assert guardrail_current.active_revision_id
        assert guardrail_current.active_revision_id != guardrail_current.published_revision_id

        resolved_guardrail_before, _, _ = main_module._resolve_guardrail_config({"ruleset_id": ruleset_id})
        assert resolved_guardrail_before["blocked_keywords"] == ["alpha"]

        activate_ruleset = client.post(f"/guardrail-rulesets/{ruleset_id}/activate")
        assert activate_ruleset.status_code == 200

        resolved_guardrail_after, _, _ = main_module._resolve_guardrail_config({"ruleset_id": ruleset_id})
        assert resolved_guardrail_after["blocked_keywords"] == ["beta"]

        agent_v1 = client.post(
            "/agent-definitions",
            json={
                "id": agent_id,
                "name": "Runtime Agent v1",
                "config_json": {
                    "system_prompt": "Use the first runtime prompt.",
                    "graph_json": _sample_graph(),
                },
            },
        )
        assert agent_v1.status_code == 200
        assert client.post(f"/agent-definitions/{agent_id}/publish").status_code == 200

        agent_v2 = client.post(
            "/agent-definitions",
            json={
                "id": agent_id,
                "name": "Runtime Agent v2",
                "config_json": {
                    "system_prompt": "Use the second runtime prompt.",
                    "graph_json": _sample_graph(),
                },
            },
        )
        assert agent_v2.status_code == 200
        assert client.post(f"/agent-definitions/{agent_id}/publish").status_code == 200

        agent_current = store.agent_definitions[agent_id]
        assert agent_current.published_revision_id
        assert agent_current.active_revision_id
        assert agent_current.active_revision_id != agent_current.published_revision_id

        resolved_agent_before = main_module._resolve_published_agent_definition(agent_id)
        assert resolved_agent_before is not None
        assert resolved_agent_before.name == "Runtime Agent v1"
        assert resolved_agent_before.config_json["system_prompt"] == "Use the first runtime prompt."

        activate_agent = client.post(f"/agent-definitions/{agent_id}/activate")
        assert activate_agent.status_code == 200

        resolved_agent_after = main_module._resolve_published_agent_definition(agent_id)
        assert resolved_agent_after is not None
        assert resolved_agent_after.name == "Runtime Agent v2"
        assert resolved_agent_after.config_json["system_prompt"] == "Use the second runtime prompt."
    finally:
        store.agent_definitions.pop(agent_id, None)
        store.agent_definition_revisions.pop(agent_id, None)
        store.guardrail_rulesets.pop(ruleset_id, None)
        store.guardrail_ruleset_revisions.pop(ruleset_id, None)


def test_memory_endpoint_loads_long_term_entries_into_short_term() -> None:
    session_id = "session:tester"
    store.memory_by_session[session_id] = []
    main_module._POSTGRES_MEMORY.clear_entries(bucket_id=session_id, session_id=session_id, memory_scope="session")
    main_module._POSTGRES_MEMORY.append_entry(
        bucket_id=session_id,
        session_id=session_id,
        memory_scope="session",
        entry={"id": "lt-1", "content": "Remember that Acme wants a weekly update cadence."},
        source="test",
    )

    response = client.get(f"/memory/{session_id}", headers={"x-frontier-actor": "tester"})
    assert response.status_code == 200
    body = response.json()
    assert body["long_term_count"] == 1
    assert any("weekly update cadence" in entry["content"] for entry in body["entries"])
    assert any("weekly update cadence" in entry["content"] for entry in store.memory_by_session[session_id])


def test_memory_node_append_persists_short_and_long_term_memory() -> None:
    bucket_id = "agent:test-agent"
    store.memory_by_session[bucket_id] = []
    main_module._POSTGRES_MEMORY.clear_entries(bucket_id=bucket_id, memory_scope="agent")

    result, _meta = main_module._run_framework_memory(
        engine="native",
        action="append",
        scope="agent",
        bucket_id=bucket_id,
        node_id="memory-1",
        message="Remember customer preferences",
        source_payload={"message": "Customer prefers SOC 2 evidence with every proposal."},
    )

    assert result["memory_state"]["entries"] >= 1
    assert any("SOC 2 evidence" in entry["content"] for entry in store.memory_by_session[bucket_id])
    long_term_entries = main_module._POSTGRES_MEMORY.get_entries(bucket_id=bucket_id, memory_scope="agent", limit=10)
    assert any("SOC 2 evidence" in entry["content"] for entry in long_term_entries)
    consolidation_candidates = main_module._POSTGRES_MEMORY.list_consolidation_candidates(bucket_id=bucket_id, memory_scope="agent")
    assert any("SOC 2 evidence" in str(entry.get("content") or "") for entry in consolidation_candidates)


def test_task_learning_persists_agent_memory_entry() -> None:
    agent_id = "agent-learning"
    main_module._POSTGRES_MEMORY.clear_entries(bucket_id=f"agent:{agent_id}", memory_scope="agent")

    main_module._record_task_learning(
        run_id="run-learning-1",
        actor="tester",
        prompt_text="Remember that Acme prefers weekly status emails.",
        response_text="Captured and acknowledged the weekly status email preference.",
        selected_agent_id=agent_id,
        selected_agent_name="Learning Agent",
        requested_workflows=[],
        requested_tags=["memory", "learning"],
    )

    learned_entries = main_module._POSTGRES_MEMORY.get_entries(bucket_id=f"agent:{agent_id}", memory_scope="agent", limit=10)
    assert learned_entries
    assert any("Acme prefers weekly status emails" in entry["content"] for entry in learned_entries)
    consolidation_candidates = main_module._POSTGRES_MEMORY.list_consolidation_candidates(bucket_id=f"agent:{agent_id}", memory_scope="agent")
    assert any(entry.get("candidate_kind") == "task-learning" for entry in consolidation_candidates)


def test_memory_consolidation_processor_generates_summary_and_marks_candidates() -> None:
    bucket_id = "agent:consolidation-target"
    store.memory_by_session[bucket_id] = []
    main_module._POSTGRES_MEMORY.clear_entries(bucket_id=bucket_id, memory_scope="agent")
    main_module._NEO4J_GRAPH.memory_projections = []

    main_module._memory_append_entry(
        bucket_id,
        {"id": "mem-1", "content": "Acme prefers weekly status emails with compliance highlights."},
        memory_scope="agent",
        source="memory-node",
    )
    main_module._memory_append_entry(
        bucket_id,
        {"id": "mem-2", "content": "Acme also wants proposal packets to include recent SOC 2 evidence."},
        memory_scope="agent",
        source="memory-node",
    )

    result = main_module._run_memory_consolidation(actor="tester", bucket_id=bucket_id, memory_scope="agent", limit=10)

    assert result["ok"] is True
    assert result["status"] == "processed"
    assert result["consolidated_candidates"] >= 2
    assert result["generated_entries"]
    assert any("Consolidated memory summary" in entry["content"] for entry in result["generated_entries"])
    assert any(entry.get("world_graph_projection") for entry in result["generated_entries"])

    long_term_entries = main_module._POSTGRES_MEMORY.get_entries(bucket_id=bucket_id, memory_scope="agent", limit=20)
    assert any(entry.get("kind") == "memory-consolidation" for entry in long_term_entries)

    candidates = main_module._POSTGRES_MEMORY.list_consolidation_candidates(bucket_id=bucket_id, memory_scope="agent", status="consolidated")
    assert len(candidates) >= 2
    assert len(main_module._NEO4J_GRAPH.memory_projections) >= 1
    assert any(
        projection.get("owner", {}).get("id") == f"owner:{bucket_id}"
        for projection in main_module._NEO4J_GRAPH.memory_projections
    )


def test_internal_memory_consolidation_endpoint_runs_processor() -> None:
    bucket_id = "workflow:consolidation-endpoint"
    store.memory_by_session[bucket_id] = []
    main_module._POSTGRES_MEMORY.clear_entries(bucket_id=bucket_id, memory_scope="workflow")
    main_module._NEO4J_GRAPH.memory_projections = []

    main_module._memory_append_entry(
        bucket_id,
        {"id": "wf-mem-1", "content": "Ops workflow should escalate Sev-1 incidents to humans within five minutes."},
        memory_scope="workflow",
        source="memory-node",
    )
    main_module._memory_append_entry(
        bucket_id,
        {"id": "wf-mem-2", "content": "The same workflow should notify the incident commander immediately after the human escalation."},
        memory_scope="workflow",
        source="memory-node",
    )

    response = client.post(
        "/internal/memory/consolidation/run",
        json={"bucket_id": bucket_id, "scope": "workflow", "limit": 10, "actor": "tester"},
            headers={
                "x-frontier-actor": "tester",
                "x-frontier-subject": "backend",
                "x-frontier-signature": "signed",
            },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["processed_candidates"] >= 1
    assert any("summary" in str(entry.get("content") or "").lower() for entry in body["generated_entries"])
    assert len(main_module._NEO4J_GRAPH.memory_projections) >= 1


def test_memory_consolidation_defers_when_evidence_threshold_not_met() -> None:
    bucket_id = "agent:deferred-memory"
    store.memory_by_session[bucket_id] = []
    main_module._POSTGRES_MEMORY.clear_entries(bucket_id=bucket_id, memory_scope="agent")

    main_module._memory_append_entry(
        bucket_id,
        {"id": "defer-1", "content": "Capture that weekly executive reports should mention control drift."},
        memory_scope="agent",
        source="memory-node",
    )

    result = main_module._run_memory_consolidation(actor="tester", bucket_id=bucket_id, memory_scope="agent", limit=10)

    assert result["ok"] is True
    assert result["generated_entries"] == []
    deferred_candidates = main_module._POSTGRES_MEMORY.list_consolidation_candidates(bucket_id=bucket_id, memory_scope="agent", status="deferred")
    assert len(deferred_candidates) == 1
    assert deferred_candidates[0]["metadata"].get("reason") == "insufficient_evidence"


def test_memory_consolidation_skips_duplicate_summaries() -> None:
    bucket_id = "agent:duplicate-memory"
    store.memory_by_session[bucket_id] = []
    main_module._POSTGRES_MEMORY.clear_entries(bucket_id=bucket_id, memory_scope="agent")
    main_module._NEO4J_GRAPH.memory_projections = []

    original_overlap = os.environ.get("FRONTIER_MEMORY_CONSOLIDATION_DUPLICATE_MIN_OVERLAP")
    os.environ["FRONTIER_MEMORY_CONSOLIDATION_DUPLICATE_MIN_OVERLAP"] = "60"
    try:
        main_module._memory_append_entry(
            bucket_id,
            {"id": "dup-1", "content": "Acme requires weekly executive reports with control drift highlights."},
            memory_scope="agent",
            source="memory-node",
        )
        main_module._memory_append_entry(
            bucket_id,
            {"id": "dup-2", "content": "Acme wants weekly executive reports that call out control drift and risks."},
            memory_scope="agent",
            source="memory-node",
        )

        first_result = main_module._run_memory_consolidation(actor="tester", bucket_id=bucket_id, memory_scope="agent", limit=10)
        assert len(first_result["generated_entries"]) == 1

        main_module._memory_append_entry(
            bucket_id,
            {"id": "dup-3", "content": "Weekly executive reports should keep calling out control drift for Acme leadership."},
            memory_scope="agent",
            source="memory-node",
        )
        main_module._memory_append_entry(
            bucket_id,
            {"id": "dup-4", "content": "Leadership updates for Acme must continue to include control drift highlights each week."},
            memory_scope="agent",
            source="memory-node",
        )

        second_result = main_module._run_memory_consolidation(actor="tester", bucket_id=bucket_id, memory_scope="agent", limit=10)
        assert second_result["generated_entries"] == []

        duplicate_candidates = main_module._POSTGRES_MEMORY.list_consolidation_candidates(bucket_id=bucket_id, memory_scope="agent", status="duplicate")
        assert len(duplicate_candidates) >= 2
    finally:
        if original_overlap is None:
            os.environ.pop("FRONTIER_MEMORY_CONSOLIDATION_DUPLICATE_MIN_OVERLAP", None)
        else:
            os.environ["FRONTIER_MEMORY_CONSOLIDATION_DUPLICATE_MIN_OVERLAP"] = original_overlap


def test_internal_world_graph_projection_endpoint_replays_consolidated_memories() -> None:
    bucket_id = "agent:world-graph-replay"
    store.memory_by_session[bucket_id] = []
    main_module._POSTGRES_MEMORY.clear_entries(bucket_id=bucket_id, memory_scope="agent")
    main_module._NEO4J_GRAPH.memory_projections = []

    consolidated_entry = {
        "id": "memory-summary-1",
        "at": "2026-03-21T00:00:00Z",
        "content": "Consolidated memory summary for agent:world-graph-replay:\n- Acme wants executive reports to highlight control drift.",
        "kind": "memory-consolidation",
        "memory_scope": "agent",
        "candidate_kind": "promotion",
        "bucket_id": bucket_id,
        "session_id": bucket_id,
        "source_candidate_ids": ["mem-a", "mem-b"],
        "source_count": 2,
    }
    main_module._POSTGRES_MEMORY.append_entry(
        bucket_id=bucket_id,
        session_id=bucket_id,
        memory_scope="agent",
        entry=consolidated_entry,
        source="memory-consolidation",
    )

    response = client.post(
        "/internal/memory/world-graph/project",
        json={"bucket_id": bucket_id, "scope": "agent", "limit": 10, "actor": "tester"},
        headers={
            "x-frontier-actor": "tester",
            "x-frontier-subject": "backend",
            "x-frontier-signature": "signed",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["projected"] >= 1
    assert len(main_module._NEO4J_GRAPH.memory_projections) >= 1
    assert any(
        projection.get("memory", {}).get("id") == "memory-summary-1"
        for projection in main_module._NEO4J_GRAPH.memory_projections
    )


def test_hybrid_memory_context_includes_world_graph_results() -> None:
    bucket_id = "agent:hybrid-context"
    store.memory_by_session[bucket_id] = []
    main_module._POSTGRES_MEMORY.clear_entries(bucket_id=bucket_id, memory_scope="agent")
    main_module._NEO4J_GRAPH.memory_projections = []

    main_module._memory_append_entry(
        bucket_id,
        {"id": "hyb-1", "content": "Acme needs executive updates to highlight control drift and SOC 2 status."},
        memory_scope="agent",
        source="memory-node",
    )
    main_module._memory_append_entry(
        bucket_id,
        {"id": "hyb-2", "content": "Acme also expects proposal packets to include recent SOC 2 evidence."},
        memory_scope="agent",
        source="memory-node",
    )
    main_module._run_memory_consolidation(actor="tester", bucket_id=bucket_id, memory_scope="agent", limit=10)

    hybrid = main_module._memory_get_hybrid_context(bucket_id, limit=20, memory_scope="agent", query_text="SOC 2")
    assert hybrid["entries"]
    assert hybrid["world_graph_entries"]
    assert any("SOC 2" in str(entry.get("content") or "") for entry in hybrid["world_graph_entries"])
    assert hybrid["world_graph_topics"]


def test_memory_read_returns_world_graph_context() -> None:
    bucket_id = "workflow:hybrid-read"
    store.memory_by_session[bucket_id] = []
    main_module._POSTGRES_MEMORY.clear_entries(bucket_id=bucket_id, memory_scope="workflow")
    main_module._NEO4J_GRAPH.memory_projections = []

    main_module._memory_append_entry(
        bucket_id,
        {"id": "read-1", "content": "Incident workflows must notify the incident commander immediately."},
        memory_scope="workflow",
        source="memory-node",
    )
    main_module._memory_append_entry(
        bucket_id,
        {"id": "read-2", "content": "Incident workflows should escalate Sev-1 cases to humans within five minutes."},
        memory_scope="workflow",
        source="memory-node",
    )
    main_module._run_memory_consolidation(actor="tester", bucket_id=bucket_id, memory_scope="workflow", limit=10)

    result, _meta = main_module._run_framework_memory(
        engine="native",
        action="read",
        scope="workflow",
        bucket_id=bucket_id,
        node_id="memory-read-1",
        message="incident commander",
        source_payload={"message": "incident commander"},
    )

    assert result["memory_items"]
    assert result["world_graph"]["entries"]
    assert result["world_graph"]["topics"]


def test_node_definitions_hide_internal_memory_node_by_default() -> None:
    default_response = client.get("/node-definitions")
    assert default_response.status_code == 200
    default_types = {item["type_key"] for item in default_response.json()}
    assert "frontier/memory" not in default_types

    internal_response = client.get("/node-definitions?include_internal=true")
    assert internal_response.status_code == 200
    internal_types = {item["type_key"] for item in internal_response.json()}
    assert "frontier/memory" in internal_types


def test_memory_scope_policy_rejects_disallowed_scope() -> None:
    execution_state = {
        "effective_security_policy": {
            "effective": {
                "allowed_memory_scopes": ["session", "agent"],
            },
        }
    }

    try:
        main_module._enforce_memory_scope_policy("global", execution_state, node_id="memory-guard")
    except RuntimeError as exc:
        assert "memory-guard" in str(exc)
        assert "global" in str(exc)
    else:
        raise AssertionError("Expected disallowed memory scope to raise RuntimeError")

    main_module._enforce_memory_scope_policy("session", execution_state, node_id="memory-guard")


def test_definition_mutations_require_auth_when_enabled_and_emit_audit_events() -> None:
    original_require_auth = store.platform_settings.require_authenticated_requests
    workflow_id = str(uuid4())
    store.workflow_definitions.pop(workflow_id, None)
    original_audit_events = list(store.audit_events)
    original_artifacts = list(store.artifacts)
    store.audit_events = []

    try:
        store.platform_settings.require_authenticated_requests = True

        unauthorized_response = client.post(
            "/workflow-definitions",
            json={
                "id": workflow_id,
                "name": "Auth Required Workflow",
                "description": "Should require authenticated mutation requests.",
                "graph_json": _sample_graph(),
            },
        )
        assert unauthorized_response.status_code == 401
        assert any(event.action == "workflow.definition.save" and event.outcome == "blocked" for event in store.audit_events)

        authorized_response = client.post(
            "/workflow-definitions",
            json={
                "id": workflow_id,
                "name": "Auth Required Workflow",
                "description": "Should require authenticated mutation requests.",
                "graph_json": _sample_graph(),
            },
            headers={"x-frontier-actor": "tester"},
        )
        assert authorized_response.status_code == 200

        publish_response = client.post(
            f"/workflow-definitions/{workflow_id}/publish",
            headers={"x-frontier-actor": "tester"},
        )
        assert publish_response.status_code == 200

        save_events = [event for event in store.audit_events if event.action == "workflow.definition.save" and event.outcome == "allowed"]
        publish_events = [event for event in store.audit_events if event.action == "workflow.definition.publish" and event.outcome == "allowed"]
        assert save_events
        assert publish_events
        assert save_events[0].metadata.get("entity_type") == "workflow_definition"
        assert save_events[0].metadata.get("entity_id") == workflow_id
        assert publish_events[0].metadata.get("after", {}).get("generated_artifact_count") == 2
    finally:
        store.platform_settings.require_authenticated_requests = original_require_auth
        store.workflow_definitions.pop(workflow_id, None)
        store.artifacts = original_artifacts
        store.audit_events = original_audit_events


def test_legacy_security_policy_aliases_resolve_to_canonical_endpoints() -> None:
    workflow_id = str(uuid4())
    agent_id = str(uuid4())
    store.workflow_definitions[workflow_id] = main_module.WorkflowDefinition(
        id=workflow_id,
        name="Legacy Alias Workflow",
        description="Workflow for legacy security policy alias coverage.",
        version=1,
        status="draft",
        graph_json=_sample_graph(),
        security_config={"classification": "restricted"},
    )
    store.agent_definitions[agent_id] = main_module.AgentDefinition(
        id=agent_id,
        name="Legacy Alias Agent",
        version=1,
        status="draft",
        type="graph",
        config_json={"security": {"classification": "confidential"}},
    )

    try:
        workflow_alias = client.get(f"/workflows/{workflow_id}/security-policy")
        workflow_canonical = client.get(f"/workflow-definitions/{workflow_id}/security-policy")
        assert workflow_alias.status_code == 200
        assert workflow_alias.json() == workflow_canonical.json()

        agent_alias = client.get(f"/agents/{agent_id}/security-policy")
        agent_canonical = client.get(f"/agent-definitions/{agent_id}/security-policy")
        assert agent_alias.status_code == 200
        assert agent_alias.json() == agent_canonical.json()
    finally:
        store.workflow_definitions.pop(workflow_id, None)
        store.agent_definitions.pop(agent_id, None)


def test_integration_mutations_require_auth_and_emit_audit_events() -> None:
    original_require_auth = store.platform_settings.require_authenticated_requests
    integration_id = str(uuid4())
    store.integrations.pop(integration_id, None)
    original_audit_events = list(store.audit_events)
    store.audit_events = []

    try:
        store.platform_settings.require_authenticated_requests = True

        unauthorized_response = client.post(
            "/integrations",
            json={
                "id": integration_id,
                "name": "Secure Integration",
                "type": "http",
                "base_url": "http://localhost:9999/test",
            },
        )
        assert unauthorized_response.status_code == 401
        assert any(event.action == "integration.save" and event.outcome == "blocked" for event in store.audit_events)

        authorized_response = client.post(
            "/integrations",
            json={
                "id": integration_id,
                "name": "Secure Integration",
                "type": "http",
                "base_url": "http://localhost:9999/test",
            },
            headers={"x-frontier-actor": "tester"},
        )
        assert authorized_response.status_code == 200

        test_response = client.post(
            f"/integrations/{integration_id}/test",
            headers={"x-frontier-actor": "tester"},
        )
        assert test_response.status_code == 200

        delete_response = client.delete(
            f"/integrations/{integration_id}",
            headers={"x-frontier-actor": "tester"},
        )
        assert delete_response.status_code == 200

        assert any(event.action == "integration.save" and event.outcome == "allowed" for event in store.audit_events)
        assert any(event.action == "integration.test" and event.outcome == "allowed" for event in store.audit_events)
        assert any(event.action == "integration.delete" and event.outcome == "allowed" for event in store.audit_events)
    finally:
        store.platform_settings.require_authenticated_requests = original_require_auth
        store.integrations.pop(integration_id, None)
        store.audit_events = original_audit_events


def test_template_and_collaboration_mutations_require_auth_and_emit_audit_events() -> None:
    original_require_auth = store.platform_settings.require_authenticated_requests
    original_audit_events = list(store.audit_events)
    store.audit_events = []

    template_id = str(uuid4())
    store.agent_templates[template_id] = main_module.AgentTemplate(
        id=template_id,
        name="Secure Template",
        description="Template for auth coverage.",
        config_json={"graph_json": _sample_graph()},
    )

    try:
        store.platform_settings.require_authenticated_requests = True

        unauthorized_template = client.post(
            f"/templates/agents/{template_id}/instantiate",
            json={"name": "Template Instance"},
        )
        assert unauthorized_template.status_code == 401

        template_response = client.post(
            f"/templates/agents/{template_id}/instantiate",
            json={"name": "Template Instance"},
            headers={"x-frontier-actor": "tester"},
        )
        assert template_response.status_code == 200
        created_agent_id = template_response.json()["id"]

        unauthorized_join = client.post(
            "/collab/sessions/join",
            json={
                "entity_type": "agent",
                "entity_id": created_agent_id,
                "user_id": "tester",
                "display_name": "Tester",
            },
        )
        assert unauthorized_join.status_code == 401

        join_response = client.post(
            "/collab/sessions/join",
            json={
                "entity_type": "agent",
                "entity_id": created_agent_id,
                "user_id": "tester",
                "display_name": "Tester",
            },
            headers={"x-frontier-actor": "tester"},
        )
        assert join_response.status_code == 200
        session_id = join_response.json()["session"]["id"]

        sync_response = client.post(
            f"/collab/sessions/{session_id}/sync",
            json={"user_id": "tester", "graph_json": _sample_graph()},
            headers={"x-frontier-actor": "tester"},
        )
        assert sync_response.status_code == 200

        assert any(event.action == "template.agent.instantiate" and event.outcome == "allowed" for event in store.audit_events)
        assert any(event.action == "collab.session.join" and event.outcome == "allowed" for event in store.audit_events)
        assert any(event.action == "collab.session.sync" and event.outcome == "allowed" for event in store.audit_events)
    finally:
        store.platform_settings.require_authenticated_requests = original_require_auth
        store.agent_templates.pop(template_id, None)
        for agent_id in list(store.agent_definitions.keys()):
            if str(store.agent_definitions[agent_id].name).startswith("Template Instance"):
                store.agent_definitions.pop(agent_id, None)
        store.collaboration_sessions = {}
        store.audit_events = original_audit_events


def test_sensitive_read_routes_require_auth_when_enabled() -> None:
    original_require_auth = store.platform_settings.require_authenticated_requests
    original_audit_events = list(store.audit_events)
    store.audit_events = []
    session_id = "session:tester"
    store.memory_by_session[session_id] = [{"id": "mem-1", "content": "keep this safe"}]

    collab_session = main_module.CollaborationSession(
        id="agent:auth-read-agent",
        entity_type="agent",
        entity_id="auth-read-agent",
        graph_json=_sample_graph(),
        version=1,
        updated_at=main_module._now_iso(),
        participants=[],
    )
    store.collaboration_sessions[collab_session.id] = collab_session

    try:
        store.platform_settings.require_authenticated_requests = True

        assert client.get("/platform/settings").status_code == 401
        assert client.get(f"/memory/{session_id}").status_code == 401
        assert client.get("/audit/events").status_code == 401
        assert client.get(f"/collab/sessions/{collab_session.id}").status_code == 401
        assert client.delete(f"/memory/{session_id}").status_code == 401

        headers = {"x-frontier-actor": "tester"}
        assert client.get("/platform/settings", headers=headers).status_code == 200
        assert client.get(f"/memory/{session_id}", headers=headers).status_code == 200
        assert client.get("/audit/events", headers=headers).status_code == 200
        assert client.get(f"/collab/sessions/{collab_session.id}", headers=headers).status_code == 200
        assert client.delete(f"/memory/{session_id}", headers=headers).status_code == 200

        assert any(event.action == "platform.settings.read" and event.outcome == "allowed" for event in store.audit_events)
        assert any(event.action == "memory.read" and event.outcome == "allowed" for event in store.audit_events)
        assert any(event.action == "audit.events.read" and event.outcome == "allowed" for event in store.audit_events)
        assert any(event.action == "collab.session.read" and event.outcome == "allowed" for event in store.audit_events)
        assert any(event.action == "memory.clear" and event.outcome == "allowed" for event in store.audit_events)
    finally:
        store.platform_settings.require_authenticated_requests = original_require_auth
        store.audit_events = original_audit_events
        store.collaboration_sessions.pop(collab_session.id, None)
        store.memory_by_session.pop(session_id, None)


def test_secure_local_mode_fail_closes_sensitive_diagnostics(monkeypatch) -> None:
    original_require_auth = store.platform_settings.require_authenticated_requests
    original_audit_events = list(store.audit_events)
    store.audit_events = []

    try:
        store.platform_settings.require_authenticated_requests = False
        monkeypatch.setenv("FRONTIER_SECURE_LOCAL_MODE", "true")
        monkeypatch.delenv("FRONTIER_REQUIRE_AUTHENTICATED_REQUESTS", raising=False)

        assert client.get("/platform/security-policy").status_code == 401
        assert client.get("/runtime/providers").status_code == 401
        assert client.get("/runtime/local-integration-readiness").status_code == 401
        assert client.get("/runtime/l3-parity-report").status_code == 401

        headers = {"x-frontier-actor": "tester"}
        assert client.get("/platform/security-policy", headers=headers).status_code == 200
        assert client.get("/runtime/providers", headers=headers).status_code == 200
        assert client.get("/runtime/local-integration-readiness", headers=headers).status_code == 200
        assert client.get("/runtime/l3-parity-report", headers=headers).status_code == 200

        assert any(event.action == "platform.security_policy.read" and event.outcome == "blocked" for event in store.audit_events)
        assert any(event.action == "runtime.providers.read" and event.outcome == "allowed" for event in store.audit_events)
    finally:
        store.platform_settings.require_authenticated_requests = original_require_auth
        store.audit_events = original_audit_events


def test_secure_local_mode_keeps_public_health_minimal_and_gates_details(monkeypatch) -> None:
    original_require_auth = store.platform_settings.require_authenticated_requests
    original_audit_events = list(store.audit_events)
    store.audit_events = []

    try:
        store.platform_settings.require_authenticated_requests = False
        monkeypatch.setenv("FRONTIER_SECURE_LOCAL_MODE", "true")
        monkeypatch.delenv("FRONTIER_REQUIRE_AUTHENTICATED_REQUESTS", raising=False)

        public_health = client.get("/healthz")
        assert public_health.status_code == 200
        assert public_health.json()["status"] == "ok"
        assert "postgres" not in public_health.json()

        assert client.get("/healthz/details").status_code == 401

        detailed_health = client.get("/healthz/details", headers={"x-frontier-actor": "tester"})
        assert detailed_health.status_code == 200
        assert "postgres" in detailed_health.json()
        assert any(event.action == "health.details.read" and event.outcome == "allowed" for event in store.audit_events)
    finally:
        store.platform_settings.require_authenticated_requests = original_require_auth
        store.audit_events = original_audit_events


def test_secure_local_mode_fail_closes_mutation_routes_without_store_toggle(monkeypatch) -> None:
    original_require_auth = store.platform_settings.require_authenticated_requests
    workflow_id = str(uuid4())
    store.workflow_definitions.pop(workflow_id, None)

    try:
        store.platform_settings.require_authenticated_requests = False
        monkeypatch.setenv("FRONTIER_SECURE_LOCAL_MODE", "true")
        monkeypatch.delenv("FRONTIER_REQUIRE_AUTHENTICATED_REQUESTS", raising=False)

        unauthorized_response = client.post(
            "/workflow-definitions",
            json={
                "id": workflow_id,
                "name": "Secure Local Auth Workflow",
                "description": "Should require auth in secure local mode.",
                "graph_json": _sample_graph(),
            },
        )
        assert unauthorized_response.status_code == 401

        authorized_response = client.post(
            "/workflow-definitions",
            json={
                "id": workflow_id,
                "name": "Secure Local Auth Workflow",
                "description": "Should require auth in secure local mode.",
                "graph_json": _sample_graph(),
            },
            headers={"x-frontier-actor": "tester"},
        )
        assert authorized_response.status_code == 200
    finally:
        store.platform_settings.require_authenticated_requests = original_require_auth
        store.workflow_definitions.pop(workflow_id, None)


def test_secure_local_mode_uses_expiring_nonce_replay_cache(monkeypatch) -> None:
    original_require_auth = store.platform_settings.require_authenticated_requests
    original_seen_nonces = dict(store.a2a_seen_nonces)

    try:
        store.platform_settings.require_authenticated_requests = False
        store.a2a_seen_nonces = {}
        monkeypatch.setenv("FRONTIER_SECURE_LOCAL_MODE", "true")
        monkeypatch.setenv("FRONTIER_REQUIRE_A2A_RUNTIME_HEADERS", "true")
        monkeypatch.setenv("FRONTIER_A2A_NONCE_TTL_SECONDS", "60")

        headers = {
            "x-frontier-actor": "tester",
            "x-frontier-subject": "backend",
            "x-frontier-signature": "signed",
            "x-frontier-nonce": "nonce-1",
        }

        first = client.get("/platform/security-policy", headers=headers)
        assert first.status_code == 200

        replay = client.get("/platform/security-policy", headers=headers)
        assert replay.status_code == 409

        store.a2a_seen_nonces["nonce-1"] = (
            main_module.datetime.now(main_module.timezone.utc) - main_module.timedelta(seconds=1)
        ).isoformat()

        expired_reuse = client.get("/platform/security-policy", headers=headers)
        assert expired_reuse.status_code == 200
        assert "nonce-1" in store.a2a_seen_nonces
    finally:
        store.platform_settings.require_authenticated_requests = original_require_auth
        store.a2a_seen_nonces = original_seen_nonces


def test_runtime_profile_local_secure_matches_fail_closed_local_behavior(monkeypatch) -> None:
    original_require_auth = store.platform_settings.require_authenticated_requests
    original_audit_events = list(store.audit_events)
    store.audit_events = []

    try:
        store.platform_settings.require_authenticated_requests = False
        monkeypatch.setenv("FRONTIER_RUNTIME_PROFILE", "local-secure")
        monkeypatch.delenv("FRONTIER_SECURE_LOCAL_MODE", raising=False)
        monkeypatch.delenv("FRONTIER_REQUIRE_AUTHENTICATED_REQUESTS", raising=False)
        monkeypatch.delenv("FRONTIER_REQUIRE_A2A_RUNTIME_HEADERS", raising=False)

        public_health = client.get("/healthz")
        assert public_health.status_code == 200
        assert public_health.json()["mode"] == "local-secure"
        assert "postgres" not in public_health.json()

        assert client.get("/platform/security-policy").status_code == 401

        detailed = client.get("/platform/security-policy", headers={"x-frontier-actor": "tester"})
        assert detailed.status_code == 200
        body = detailed.json()
        assert body["runtime_profile"]["name"] == "local-secure"
        assert body["runtime_profile"]["controls"]["require_authenticated_requests"] is True
        assert body["runtime_profile"]["controls"]["require_a2a_runtime_headers"] is False
    finally:
        store.platform_settings.require_authenticated_requests = original_require_auth
        store.audit_events = original_audit_events


def test_runtime_profile_hosted_is_immutable_and_requires_a2a_headers(monkeypatch) -> None:
    original_require_auth = store.platform_settings.require_authenticated_requests
    original_seen_nonces = dict(store.a2a_seen_nonces)

    try:
        store.platform_settings.require_authenticated_requests = False
        store.a2a_seen_nonces = {}
        monkeypatch.setenv("FRONTIER_RUNTIME_PROFILE", "hosted")
        monkeypatch.setenv("FRONTIER_REQUIRE_AUTHENTICATED_REQUESTS", "false")
        monkeypatch.setenv("FRONTIER_REQUIRE_A2A_RUNTIME_HEADERS", "false")
        monkeypatch.delenv("FRONTIER_SECURE_LOCAL_MODE", raising=False)

        public_health = client.get("/healthz")
        assert public_health.status_code == 200
        assert public_health.json()["mode"] == "hosted"
        assert "postgres" not in public_health.json()

        assert client.get("/platform/security-policy").status_code == 401
        assert client.get("/platform/security-policy", headers={"x-frontier-actor": "tester"}).status_code == 401

        hosted_headers = {
            "x-frontier-actor": "tester",
            "x-frontier-subject": "backend",
            "x-frontier-signature": "signed",
            "x-frontier-nonce": "hosted-profile-nonce-1",
        }
        allowed = client.get("/platform/security-policy", headers=hosted_headers)
        assert allowed.status_code == 200
        body = allowed.json()
        assert body["runtime_profile"]["name"] == "hosted"
        assert body["runtime_profile"]["controls"]["require_authenticated_requests"] is True
        assert body["runtime_profile"]["controls"]["require_a2a_runtime_headers"] is True
    finally:
        store.platform_settings.require_authenticated_requests = original_require_auth
        store.a2a_seen_nonces = original_seen_nonces


def test_cors_preflight_uses_explicit_methods_and_headers() -> None:
    response = client.options(
        "/healthz",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "authorization,content-type,x-frontier-actor,x-frontier-signature,x-frontier-nonce",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"
    assert response.headers["access-control-allow-methods"] != "*"
    assert "POST" in response.headers["access-control-allow-methods"]
    assert response.headers["access-control-allow-headers"] != "*"
    allowed_headers = response.headers["access-control-allow-headers"].lower()
    assert "x-frontier-actor" in allowed_headers
    assert "x-frontier-signature" in allowed_headers
    assert "x-frontier-nonce" in allowed_headers


def test_security_headers_are_applied_from_shared_policy() -> None:
    response = client.get("/healthz")

    assert response.status_code == 200
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["content-security-policy"] == "default-src 'none'; frame-ancestors 'none'; base-uri 'none'"
    assert response.headers["referrer-policy"] == "no-referrer"
    assert response.headers["permissions-policy"] == "camera=(), microphone=(), geolocation=(), browsing-topics=()"


def test_hosted_runtime_profile_adds_hsts_header(monkeypatch) -> None:
    monkeypatch.setenv("FRONTIER_RUNTIME_PROFILE", "hosted")

    response = client.get("/healthz")

    assert response.status_code == 200
    assert response.headers["strict-transport-security"] == "max-age=63072000; includeSubDomains"


def test_route_inventory_covers_registered_backend_routes() -> None:
    validate_route_inventory(app)


def test_central_route_policy_protects_previously_unenforced_read_surfaces() -> None:
    original_require_auth = store.platform_settings.require_authenticated_requests

    try:
        store.platform_settings.require_authenticated_requests = True

        protected_paths = [
            "/workflow-runs",
            "/inbox",
            "/templates/agents",
            "/observability/dashboard",
            "/audit/atf-alignment-report",
            "/artifacts",
        ]

        for path in protected_paths:
            unauthorized = client.get(path)
            assert unauthorized.status_code == 401, path

            authorized = client.get(path, headers={"x-frontier-actor": "tester"})
            assert authorized.status_code == 200, path
    finally:
        store.platform_settings.require_authenticated_requests = original_require_auth


def test_memory_scope_authorization_denies_cross_actor_user_bucket_reads() -> None:
    bucket_id = "user:owner-user"
    store.memory_by_session[bucket_id] = [{"id": "mem-user-1", "content": "owner-only memory"}]

    try:
        denied = client.get(f"/memory/{bucket_id}?scope=user", headers={"x-frontier-actor": "other-user"})
        assert denied.status_code == 403

        allowed = client.get(f"/memory/{bucket_id}?scope=user", headers={"x-frontier-actor": "owner-user"})
        assert allowed.status_code == 200
        assert allowed.json()["session_id"] == bucket_id
    finally:
        store.memory_by_session.pop(bucket_id, None)


def test_memory_scope_authorization_requires_tenant_claim_for_tenant_bucket() -> None:
    bucket_id = "tenant:acme"
    store.memory_by_session[bucket_id] = [{"id": "mem-tenant-1", "content": "tenant-scoped memory"}]

    try:
        missing_claim = client.get(f"/memory/{bucket_id}?scope=tenant", headers={"x-frontier-actor": "tenant-user"})
        assert missing_claim.status_code == 403

        wrong_claim = client.get(
            f"/memory/{bucket_id}?scope=tenant",
            headers={"x-frontier-actor": "tenant-user", "x-frontier-tenant": "other"},
        )
        assert wrong_claim.status_code == 403

        allowed = client.get(
            f"/memory/{bucket_id}?scope=tenant",
            headers={"x-frontier-actor": "tenant-user", "x-frontier-tenant": "acme"},
        )
        assert allowed.status_code == 200
    finally:
        store.memory_by_session.pop(bucket_id, None)


def test_runtime_bearer_token_supplies_actor_and_tenant_claims() -> None:
    bucket_id = "tenant:acme"
    store.memory_by_session[bucket_id] = [{"id": "mem-tenant-jwt", "content": "tenant-scoped memory"}]

    token = mint_token(
        "tenant-user",
        ttl_seconds=60,
        additional_claims={
            "actor": "tenant-user",
            "tenant_id": "acme",
        },
    )

    try:
        settings_response = client.get(
            "/platform/settings",
            headers={"authorization": f"Bearer {token}"},
        )
        assert settings_response.status_code == 200

        memory_response = client.get(
            f"/memory/{bucket_id}?scope=tenant",
            headers={"authorization": f"Bearer {token}"},
        )
        assert memory_response.status_code == 200
        assert memory_response.json()["session_id"] == bucket_id
    finally:
        store.memory_by_session.pop(bucket_id, None)


def test_non_internal_runtime_bearer_token_cannot_access_internal_memory_endpoints() -> None:
    bucket_id = "agent:runtime-bearer-user"
    store.memory_by_session[bucket_id] = []
    main_module._POSTGRES_MEMORY.clear_entries(bucket_id=bucket_id, memory_scope="agent")
    main_module._memory_append_entry(
        bucket_id,
        {"id": "runtime-user-1", "content": "user bearer token should not gain internal access"},
        memory_scope="agent",
        source="memory-node",
    )

    token = mint_token(
        "member-user",
        ttl_seconds=60,
        additional_claims={
            "actor": "member-user",
        },
    )

    try:
        denied = client.post(
            "/internal/memory/consolidation/run",
            json={"bucket_id": bucket_id, "scope": "agent", "limit": 10},
            headers={"authorization": f"Bearer {token}"},
        )
        assert denied.status_code == 403
    finally:
        store.memory_by_session.pop(bucket_id, None)
        main_module._POSTGRES_MEMORY.clear_entries(bucket_id=bucket_id, memory_scope="agent")


def test_internal_runtime_bearer_token_can_access_internal_memory_endpoints() -> None:
    bucket_id = "agent:runtime-bearer-internal"
    store.memory_by_session[bucket_id] = []
    main_module._POSTGRES_MEMORY.clear_entries(bucket_id=bucket_id, memory_scope="agent")
    main_module._memory_append_entry(
        bucket_id,
        {"id": "runtime-internal-1", "content": "internal bearer token maintenance target"},
        memory_scope="agent",
        source="memory-node",
    )

    token = mint_token(
        "backend",
        ttl_seconds=60,
        additional_claims={
            "subject": "backend",
            "internal_service": True,
        },
    )

    try:
        allowed = client.post(
            "/internal/memory/consolidation/run",
            json={"bucket_id": bucket_id, "scope": "agent", "limit": 10},
            headers={"authorization": f"Bearer {token}"},
        )
        assert allowed.status_code == 200
    finally:
        store.memory_by_session.pop(bucket_id, None)
        main_module._POSTGRES_MEMORY.clear_entries(bucket_id=bucket_id, memory_scope="agent")


def test_memory_scope_authorization_requires_collaboration_membership_for_agent_bucket() -> None:
    bucket_id = "agent:secure-agent"
    store.memory_by_session[bucket_id] = [{"id": "mem-agent-1", "content": "agent memory"}]
    original_sessions = dict(store.collaboration_sessions)

    store.collaboration_sessions[bucket_id] = main_module.CollaborationSession(
        id=bucket_id,
        entity_type="agent",
        entity_id="secure-agent",
        graph_json=_sample_graph(),
        version=1,
        updated_at=main_module._now_iso(),
        participants=[
            main_module.CollaborationParticipant(
                user_id="member-user",
                display_name="Member",
                role="viewer",
                last_seen_at=main_module._now_iso(),
            )
        ],
    )

    try:
        denied = client.get(f"/memory/{bucket_id}?scope=agent", headers={"x-frontier-actor": "other-user"})
        assert denied.status_code == 403

        allowed = client.get(f"/memory/{bucket_id}?scope=agent", headers={"x-frontier-actor": "member-user"})
        assert allowed.status_code == 200
    finally:
        store.memory_by_session.pop(bucket_id, None)
        store.collaboration_sessions = original_sessions


def test_memory_scope_authorization_rejects_bucket_scope_mismatch() -> None:
    denied = client.get("/memory/agent:scope-mismatch?scope=session", headers={"x-frontier-actor": "tester"})
    assert denied.status_code == 403


def test_internal_memory_endpoints_require_internal_service_access() -> None:
    bucket_id = "agent:internal-maintenance"
    store.memory_by_session[bucket_id] = []
    main_module._POSTGRES_MEMORY.clear_entries(bucket_id=bucket_id, memory_scope="agent")
    main_module._memory_append_entry(
        bucket_id,
        {"id": "maint-1", "content": "internal maintenance target memory"},
        memory_scope="agent",
        source="memory-node",
    )

    try:
        denied = client.post(
            "/internal/memory/consolidation/run",
            json={"bucket_id": bucket_id, "scope": "agent", "limit": 10},
            headers={"x-frontier-actor": "tester"},
        )
        assert denied.status_code == 403

        allowed = client.post(
            "/internal/memory/consolidation/run",
            json={"bucket_id": bucket_id, "scope": "agent", "limit": 10},
            headers={
                "x-frontier-actor": "tester",
                "x-frontier-subject": "backend",
                "x-frontier-signature": "signed",
            },
        )
        assert allowed.status_code == 200

        projection = client.post(
            "/internal/memory/world-graph/project",
            json={"bucket_id": bucket_id, "scope": "agent", "limit": 10},
            headers={
                "x-frontier-actor": "tester",
                "x-frontier-subject": "backend",
                "x-frontier-signature": "signed",
            },
        )
        assert projection.status_code == 200
    finally:
        store.memory_by_session.pop(bucket_id, None)
        main_module._POSTGRES_MEMORY.clear_entries(bucket_id=bucket_id, memory_scope="agent")


def test_graph_runs_sanitize_runtime_failure_details(monkeypatch) -> None:
    def _explode(*_args: object, **_kwargs: object) -> dict[str, object]:
        raise RuntimeError("ToolInputGuardrailTripwireTriggered at node 'tool-1'")

    monkeypatch.setattr(main_module, "_execute_node", _explode)

    response = client.post(
        "/graph/runs",
        json={
            "schema_version": "frontier-graph/1.0",
            "nodes": _sample_graph()["nodes"],
            "links": _sample_graph()["links"],
            "input": {"message": "hello"},
        },
        headers={"x-frontier-actor": "tester"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "failed"
    failure_event = next(event for event in body["events"] if event["type"] == "node_failed")
    assert failure_event["summary"] == "Execution blocked by runtime policy."
    assert "ToolInputGuardrailTripwireTriggered" not in failure_event["summary"]


def test_source_allowlist_uses_canonical_path_containment(tmp_path: Path) -> None:
    allowed_root = tmp_path / "allowed"
    allowed_root.mkdir()
    inside = allowed_root / "nested" / "file.txt"
    inside.parent.mkdir()
    inside.write_text("ok", encoding="utf-8")

    sibling_prefix = tmp_path / "allowed-evil" / "file.txt"
    sibling_prefix.parent.mkdir()
    sibling_prefix.write_text("nope", encoding="utf-8")

    assert main_module._source_allowed(str(inside), [str(allowed_root)]) is True
    assert main_module._source_allowed(str(sibling_prefix), [str(allowed_root)]) is False


def test_prompt_loader_blocks_path_traversal_outside_approved_roots() -> None:
    assert main_module._load_prompt_from_relative_path("../README.md") == ""


def test_collaboration_routes_bind_payload_identity_to_authenticated_actor() -> None:
    original_require_auth = store.platform_settings.require_authenticated_requests
    original_audit_events = list(store.audit_events)
    original_sessions = dict(store.collaboration_sessions)
    store.audit_events = []

    session_id = _collab_session_key = None
    try:
        store.platform_settings.require_authenticated_requests = True

        join_mismatch = client.post(
            "/collab/sessions/join",
            json={
                "entity_type": "agent",
                "entity_id": "secure-agent",
                "user_id": "spoofed-user",
                "display_name": "Spoofed",
            },
            headers={"x-frontier-actor": "owner-user"},
        )
        assert join_mismatch.status_code == 403

        join_owner = client.post(
            "/collab/sessions/join",
            json={
                "entity_type": "agent",
                "entity_id": "secure-agent",
                "display_name": "Owner",
            },
            headers={"x-frontier-actor": "owner-user"},
        )
        assert join_owner.status_code == 200
        session_id = join_owner.json()["session"]["id"]
        assert join_owner.json()["participant"]["user_id"] == "owner-user"

        join_member = client.post(
            "/collab/sessions/join",
            json={
                "entity_type": "agent",
                "entity_id": "secure-agent",
                "display_name": "Member",
            },
            headers={"x-frontier-actor": "member-user"},
        )
        assert join_member.status_code == 200

        sync_mismatch = client.post(
            f"/collab/sessions/{session_id}/sync",
            json={"user_id": "spoofed-user", "graph_json": _sample_graph()},
            headers={"x-frontier-actor": "owner-user"},
        )
        assert sync_mismatch.status_code == 403

        sync_ok = client.post(
            f"/collab/sessions/{session_id}/sync",
            json={"graph_json": _sample_graph()},
            headers={"x-frontier-actor": "owner-user"},
        )
        assert sync_ok.status_code == 200

        permissions_mismatch = client.post(
            f"/collab/sessions/{session_id}/permissions",
            json={"actor_user_id": "spoofed-user", "target_user_id": "member-user", "role": "viewer"},
            headers={"x-frontier-actor": "owner-user"},
        )
        assert permissions_mismatch.status_code == 403

        permissions_ok = client.post(
            f"/collab/sessions/{session_id}/permissions",
            json={"target_user_id": "member-user", "role": "viewer"},
            headers={"x-frontier-actor": "owner-user"},
        )
        assert permissions_ok.status_code == 200

        updated_session = permissions_ok.json()["session"]
        member = next(item for item in updated_session["participants"] if item["user_id"] == "member-user")
        assert member["role"] == "viewer"
        assert any(event.action == "collab.session.join" and event.outcome == "blocked" for event in store.audit_events)
        assert any(event.action == "collab.session.sync" and event.outcome == "blocked" for event in store.audit_events)
        assert any(event.action == "collab.session.permissions.update" and event.outcome == "blocked" for event in store.audit_events)
    finally:
        store.platform_settings.require_authenticated_requests = original_require_auth
        store.audit_events = original_audit_events
        store.collaboration_sessions = original_sessions


def test_rank_hybrid_memory_entries_prefers_query_relevance() -> None:
    entries = [
        {"id": "general", "content": "General customer context without compliance specifics.", "tier": "short-term"},
        {"id": "relevant", "content": "Customer requires SOC 2 evidence in every proposal packet and review.", "tier": "long-term"},
    ]

    ranked = main_module._rank_hybrid_memory_entries(
        entries,
        query_text="SOC 2 evidence",
        runtime_role="",
    )

    assert ranked[0]["id"] == "relevant"
    assert ranked[0]["retrieval_score"] > ranked[1]["retrieval_score"]


def test_apply_memory_token_budget_truncates_context() -> None:
    entries = [
        {
            "id": "first",
            "content": " ".join(["evidence"] * 60),
            "tier": "long-term",
        },
        {
            "id": "second",
            "content": " ".join(["compliance"] * 60),
            "tier": "long-term",
        },
    ]
    ranked = main_module._rank_hybrid_memory_entries(
        entries,
        query_text="evidence compliance",
        runtime_role="",
    )

    kept = main_module._apply_memory_token_budget(ranked, max_tokens=100)

    assert len(kept) == 1
    assert kept[0]["id"] == ranked[0]["id"]
    assert kept[0]["retrieval_tokens"] <= 100


def test_rank_hybrid_memory_entries_applies_runtime_role_bonus() -> None:
    entries = [
        {
            "id": "short-term",
            "content": "Control drift and evidence requirements for customer updates.",
            "tier": "short-term",
        },
        {
            "id": "world-graph",
            "content": "Control drift and evidence requirements for customer updates.",
            "tier": "world-graph",
        },
    ]

    ranked_default = main_module._rank_hybrid_memory_entries(
        entries,
        query_text="control drift evidence",
        runtime_role="",
    )
    ranked_retrieval = main_module._rank_hybrid_memory_entries(
        entries,
        query_text="control drift evidence",
        runtime_role="retrieval",
    )

    assert ranked_default[0]["id"] == "short-term"
    assert ranked_retrieval[0]["id"] == "world-graph"
    assert ranked_retrieval[0]["retrieval_score"] > ranked_default[0]["retrieval_score"]
