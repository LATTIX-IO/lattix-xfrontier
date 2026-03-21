package lattix.budget_policy

import rego.v1

default allow = true

allow := false if {
  input.tokens_used > input.max_tokens
}

allow := false if {
  input.duration_used_seconds > input.max_duration_seconds
}

allow := false if {
  input.cost_used_usd > input.max_cost_usd
}
