package lattix.agent_policy

import rego.v1

default allow = false

agent_config := {
  "orchestrator": {"id": "orchestrator", "allowed_tools": ["execute_step", "a2a.execute"]},
  "backend": {"id": "backend", "allowed_tools": ["execute_step", "a2a.execute"]},
  "research": {"id": "research", "allowed_tools": ["execute_step", "search"]},
  "code": {"id": "code", "allowed_tools": ["execute_step", "generate_code"]},
  "review": {"id": "review", "allowed_tools": ["execute_step", "review_output"]}
}

network_allowlist := {target | some target in input.allowed_targets}

tool_calls_used := object.get(input, "tool_calls_used", object.get(input, "tool_calls", 0))

allowed_tool(tool) if {
  provided_allowed_tools := object.get(input, "allowed_tools", null)
  is_array(provided_allowed_tools)
  tool in provided_allowed_tools
}

allowed_tool(tool) if {
  provided_allowed_tools := object.get(input, "allowed_tools", null)
  not is_array(provided_allowed_tools)
  config := object.get(agent_config, input.agent_id, null)
  config != null
  tool in config.allowed_tools
}

allow if {
  allowed_tool(input.tool)
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
  object.get(input, "max_tool_calls", 0) > 0
  tool_calls_used > input.max_tool_calls
}

deny if {
  input.action == "llm_call"
  input.classification == "restricted"
  input.provider != "local"
}
