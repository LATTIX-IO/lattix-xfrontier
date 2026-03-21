package lattix.network_policy

import rego.v1

default allow = false

allow if {
  input.source == "orchestrator"
  input.target in {"agent-research", "agent-code", "agent-review", "vault", "opa", "nats", "postgres"}
}

allow if {
  startswith(input.source, "agent-")
  input.target in {"opa", "nats", "vault", "envoy"}
}

allow if {
  input.source == "envoy"
  input.target in {"https://example.internal", "https://api.openai.com"}
}
