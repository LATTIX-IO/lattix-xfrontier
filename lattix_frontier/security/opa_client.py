"""OPA client with local fallback decisions."""

from __future__ import annotations

from dataclasses import dataclass
import os

import httpx

from lattix_frontier.config import get_settings
from lattix_frontier.sandbox.network import is_host_allowed


@dataclass
class PolicyDecision:
    """Policy decision object."""

    allowed: bool
    reason: str = "allowed"


class OPAClient:
    """Evaluate policies through OPA or local fallback rules."""

    def __init__(self, base_url: str | None = None) -> None:
        self.base_url = (base_url or get_settings().opa_addr).rstrip("/")

    async def evaluate(self, policy: str, payload: dict[str, object]) -> PolicyDecision:
        url = f"{self.base_url}/v1/data/lattix/{policy}/allow"
        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
                response = await client.post(url, json={"input": payload})
                if response.is_success:
                    result = bool(response.json().get("result", False))
                    return PolicyDecision(allowed=result, reason="opa decision")
        except httpx.HTTPError:
            pass
        return self._evaluate_locally(policy, payload)

    def _evaluate_locally(self, policy: str, payload: dict[str, object]) -> PolicyDecision:
        action = payload.get("action")
        budget = payload.get("budget", {})
        if policy == "filesystem_access":
            path = str(payload.get("path", ""))
            allowed_paths = [str(item) for item in payload.get("allowed_paths", [])]
            if any(path.startswith(allowed) for allowed in allowed_paths):
                return PolicyDecision(allowed=True, reason="filesystem path allowlisted")
            return PolicyDecision(allowed=False, reason="filesystem path not allowlisted")
        if policy == "agent_policy":
            agent_id = str(payload.get("agent_id", "")).strip()
            tool = str(payload.get("tool", "")).strip()
            agent_config = {
                "orchestrator": {"execute_step"},
                "research": {"search", "execute_step"},
                "code": {"generate_code", "execute_step"},
                "review": {"review_output", "execute_step"},
            }
            if agent_id in agent_config and tool in agent_config[agent_id]:
                if tool == "read_file" and str(payload.get("resource", "")).endswith((".env", ".json", ".key", ".pem", ".ssh")):
                    return PolicyDecision(allowed=False, reason="credential file access denied")
                if isinstance(budget, dict) and int(budget.get("tokens_used", 0)) > int(budget.get("max_tokens", 0)):
                    return PolicyDecision(allowed=False, reason="budget exceeded")
                if payload.get("classification") == "restricted" and payload.get("provider") != "local":
                    return PolicyDecision(allowed=False, reason="restricted data requires local provider")
                return PolicyDecision(allowed=True, reason="local embedded policy decision")
            return PolicyDecision(allowed=False, reason="agent tool is not allowlisted")
        if isinstance(budget, dict) and int(budget.get("tokens_used", 0)) > int(budget.get("max_tokens", 0)):
            return PolicyDecision(allowed=False, reason="budget exceeded")
        if payload.get("classification") == "restricted" and payload.get("provider") != "local":
            return PolicyDecision(allowed=False, reason="restricted data requires local provider")
        if action == "network_egress":
            target = str(payload.get("target", ""))
            allowed_targets = payload.get("allowed_targets", [])
            if not isinstance(allowed_targets, list) or not is_host_allowed(target, [str(item) for item in allowed_targets]):
                return PolicyDecision(allowed=False, reason="target not allowlisted")
            return PolicyDecision(allowed=True, reason="network egress allowlisted")
        if action == "read":
            allowed_paths = payload.get("allowed_paths", [])
            path = os.path.abspath(str(payload.get("path", "")))
            if isinstance(allowed_paths, list) and allowed_paths:
                if not any(os.path.commonpath([path, os.path.abspath(str(root))]) == os.path.abspath(str(root)) for root in allowed_paths):
                    return PolicyDecision(allowed=False, reason="path not allowlisted")
        if "readonly_rootfs" in payload:
            if not bool(payload.get("readonly_rootfs", False)):
                return PolicyDecision(allowed=False, reason="readonly root filesystem is required")
            if bool(payload.get("allow_network", False)) and not bool(payload.get("require_egress_mediation", False)):
                return PolicyDecision(allowed=False, reason="egress mediation is required when network is enabled")
            if str(payload.get("run_as_user", "")).startswith("0"):
                return PolicyDecision(allowed=False, reason="sandbox tools must not run as root")
            return PolicyDecision(allowed=True, reason="local embedded policy decision")
        if action == "read":
            return PolicyDecision(allowed=False, reason="filesystem access denied")
        if action == "network_egress":
            return PolicyDecision(allowed=False, reason="network egress denied")
        return PolicyDecision(allowed=False, reason="OPA unavailable; fail-closed deny")
