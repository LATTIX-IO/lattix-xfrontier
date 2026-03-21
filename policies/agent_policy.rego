package lattix.agent_policy

import rego.v1

default allow = false

agent_config := {
  "orchestrator": {"id": "orchestrator", "allowed_tools": ["execute_step", "a2a.execute"]},
  "research": {"id": "research", "allowed_tools": ["execute_step", "search"]},
  "code": {"id": "code", "allowed_tools": ["execute_step", "generate_code"]},
  "review": {"id": "review", "allowed_tools": ["execute_step", "review_output"]}
}

network_allowlist := {target | some target in input.allowed_targets}

allow if {
  input.agent_id == agent_config[input.agent_id].id
  input.tool in agent_config[input.agent_id].allowed_tools
  not deny
}

deny if {
  input.tool == "read_file"
  regex.match("\\.(env|json|key|pem|ssh)$", input.resource)
}

deny if {
  input.action == "network_egress"
  count(network_allowlist) == 0
}

deny if {
  input.action == "network_egress"
  not input.target in network_allowlist
}

deny if {
  input.budget.tokens_used > input.budget.max_tokens
}

deny if {
  input.action == "llm_call"
  input.classification == "restricted"
  input.provider != "local"
}
