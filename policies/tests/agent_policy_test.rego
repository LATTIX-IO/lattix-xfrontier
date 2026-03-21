package lattix.agent_policy_test

import rego.v1

import data.lattix.agent_policy

test_allow_registered_tool if {
  agent_policy.allow with input as {
    "agent_id": "orchestrator",
    "tool": "execute_step",
    "resource": "workflow",
    "budget": {"tokens_used": 0, "max_tokens": 10},
    "action": "execute_step",
    "classification": "internal",
    "provider": "local"
  }
}

test_deny_credential_file if {
  agent_policy.deny with input as {
    "agent_id": "research",
    "tool": "read_file",
    "resource": ".env",
    "budget": {"tokens_used": 0, "max_tokens": 10},
    "action": "read_file",
    "classification": "internal",
    "provider": "local"
  }
}

test_deny_restricted_external_llm if {
  agent_policy.deny with input as {
    "agent_id": "orchestrator",
    "tool": "llm_call",
    "resource": "workflow",
    "budget": {"tokens_used": 0, "max_tokens": 10},
    "action": "llm_call",
    "classification": "restricted",
    "provider": "openai"
  }
}
