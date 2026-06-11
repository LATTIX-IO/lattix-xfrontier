"""Focused tests for the Symphony-derived skills registry and integration catalog."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

if not str(os.environ.get("A2A_JWT_SECRET") or "").strip():
    os.environ["A2A_JWT_SECRET"] = "unit-test-super-secret-value-32bytes"
if not str(os.environ.get("FRONTIER_API_BEARER_TOKEN") or "").strip():
    os.environ["FRONTIER_API_BEARER_TOKEN"] = "unit-test-bearer"

import app.main as main_module
from app.main import app, store

client = TestClient(app)

READ_HEADERS = {"x-frontier-actor": "tester"}
ADMIN_HEADERS = {"Authorization": "Bearer unit-test-bearer", "x-frontier-actor": "frontier-admin"}


def test_local_catalog_includes_gpt_oss_models() -> None:
    response = client.get("/models/overview", headers=READ_HEADERS)
    assert response.status_code == 200
    ids = {item["id"] for item in response.json()["catalog"]}
    assert {"gpt-oss:20b", "gpt-oss:120b"} <= ids


def test_bundled_skills_are_seeded_and_listed() -> None:
    response = client.get("/skills", headers=READ_HEADERS)
    assert response.status_code == 200
    skills = response.json()
    names = {item["name"] for item in skills}
    assert {"commit", "push", "pull", "land", "issue-tracker", "debug"} <= names
    assert all(item["source"] == "bundled" for item in skills if item["name"] == "commit")


def test_custom_skill_lifecycle_create_update_disable_delete() -> None:
    created = client.post(
        "/skills",
        json={
            "name": "release-notes",
            "description": "Draft release notes from merged PRs.",
            "content": "## Goal\nSummarize merged changes.",
            "tags": ["delivery"],
        },
        headers=ADMIN_HEADERS,
    )
    assert created.status_code == 200
    skill = created.json()
    skill_id = skill["id"]
    try:
        assert skill["source"] == "custom"
        assert skill["version"] == 1
        assert skill["status"] == "enabled"

        updated = client.post(
            "/skills",
            json={"id": skill_id, "status": "disabled", "content": "## Goal\nUpdated."},
            headers=ADMIN_HEADERS,
        )
        assert updated.status_code == 200
        assert updated.json()["version"] == 2
        assert updated.json()["status"] == "disabled"
        assert updated.json()["name"] == "release-notes"  # preserved without resending

        deleted = client.delete(f"/skills/{skill_id}", headers=ADMIN_HEADERS)
        assert deleted.status_code == 200
    finally:
        store.skills.pop(skill_id, None)


def test_bundled_skills_cannot_be_deleted() -> None:
    response = client.delete("/skills/skill-commit", headers=ADMIN_HEADERS)
    assert response.status_code == 400
    assert "disable" in response.json()["detail"].lower()
    assert "skill-commit" in store.skills


def test_enabled_skills_inject_into_system_prompt_within_budget() -> None:
    augmented = main_module._augment_system_prompt_with_skills("BASE PROMPT")
    assert augmented.startswith("BASE PROMPT")
    assert "## Platform skills" in augmented
    assert "### Skill: commit" in augmented
    assert len(augmented) <= len("BASE PROMPT") + main_module._SKILLS_PROMPT_CHAR_BUDGET + 200

    original = store.skills["skill-commit"].status
    try:
        store.skills["skill-commit"].status = "disabled"
        without = main_module._augment_system_prompt_with_skills("BASE PROMPT")
        assert "### Skill: commit" not in without
    finally:
        store.skills["skill-commit"].status = original


def test_skill_injection_increments_usage_metrics() -> None:
    commit = store.skills["skill-commit"]
    before_count = commit.usage_count
    main_module._augment_system_prompt_with_skills("BASE PROMPT")
    assert commit.usage_count == before_count + 1
    assert commit.last_used_at != ""


def test_skill_test_endpoint_dry_runs_a_skill() -> None:
    response = client.post(
        "/skills/skill-commit/test",
        json={"prompt": "Commit the current changes."},
        headers=ADMIN_HEADERS,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["skill_id"] == "skill-commit"
    assert body["mode"] in {"live", "simulated"}
    assert isinstance(body["output"], str) and body["output"]


def test_skill_test_endpoint_validates_input() -> None:
    missing = client.post("/skills/skill-commit/test", json={"prompt": "  "}, headers=ADMIN_HEADERS)
    assert missing.status_code == 400

    unknown = client.post("/skills/not-a-skill/test", json={"prompt": "x"}, headers=ADMIN_HEADERS)
    assert unknown.status_code == 404


def test_observability_dashboard_includes_skill_metrics() -> None:
    response = client.get("/observability/dashboard", headers=ADMIN_HEADERS)
    assert response.status_code == 200
    body = response.json()
    assert "skills" in body
    names = {item["name"] for item in body["skills"]}
    assert "commit" in names
    assert "skills_enabled" in body["summary"]
    assert "skill_injections_total" in body["summary"]
    sample = body["skills"][0]
    assert {"usage_count", "last_used_at", "status", "version"} <= set(sample.keys())


def test_integration_catalog_lists_and_installs_entries() -> None:
    catalog = client.get("/integrations/catalog", headers=ADMIN_HEADERS)
    assert catalog.status_code == 200
    entries = catalog.json()
    ids = {entry["catalog_id"] for entry in entries}
    assert {"mcp-github", "mcp-linear", "api-nvidia-nim", "mcp-filesystem"} <= ids

    installed_id = None
    try:
        install = client.post("/integrations/catalog/mcp-github/install", headers=ADMIN_HEADERS)
        assert install.status_code == 200
        body = install.json()
        installed_id = body["id"]
        assert body["already_installed"] is False

        integration = store.integrations[installed_id]
        assert integration.status == "draft"
        assert integration.metadata_json["catalog_id"] == "mcp-github"
        assert integration.secret_ref == ""  # credentials are never preloaded

        again = client.post("/integrations/catalog/mcp-github/install", headers=ADMIN_HEADERS)
        assert again.json()["already_installed"] is True

        refreshed = client.get("/integrations/catalog", headers=ADMIN_HEADERS)
        github_entry = next(
            entry for entry in refreshed.json() if entry["catalog_id"] == "mcp-github"
        )
        assert github_entry["installed"] is True
    finally:
        if installed_id:
            store.integrations.pop(installed_id, None)


def test_install_unknown_catalog_entry_is_404() -> None:
    response = client.post("/integrations/catalog/not-a-real-entry/install", headers=ADMIN_HEADERS)
    assert response.status_code == 404
