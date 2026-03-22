from __future__ import annotations

import os
import sys
import types
from collections import defaultdict
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient

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


def test_memory_endpoint_loads_long_term_entries_into_short_term() -> None:
    session_id = "session:test-memory"
    store.memory_by_session[session_id] = []
    main_module._POSTGRES_MEMORY.clear_entries(bucket_id=session_id, session_id=session_id, memory_scope="session")
    main_module._POSTGRES_MEMORY.append_entry(
        bucket_id=session_id,
        session_id=session_id,
        memory_scope="session",
        entry={"id": "lt-1", "content": "Remember that Acme wants a weekly update cadence."},
        source="test",
    )

    response = client.get(f"/memory/{session_id}")
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
        headers={"x-frontier-actor": "tester"},
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
        headers={"x-frontier-actor": "tester"},
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
