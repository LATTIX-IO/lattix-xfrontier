package lattix.network_egress_test

import rego.v1

import data.lattix.network_egress

test_allow_allowlisted_target if {
  network_egress.allow with input as {
    "action": "network_egress",
    "target": "api.example.com",
    "allowed_targets": ["api.example.com"]
  }
}

test_deny_non_allowlisted_target if not network_egress.allow with input as {
  "action": "network_egress",
  "target": "evil.example.com",
  "allowed_targets": ["api.example.com"]
}
