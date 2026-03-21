package lattix.network_policy_test

import rego.v1

import data.lattix.network_policy

test_orchestrator_can_call_agents if {
  network_policy.allow with input as {"source": "orchestrator", "target": "agent-research"}
}

test_agent_cannot_access_arbitrary_service if not network_policy.allow with input as {"source": "agent-research", "target": "postgres"}
