package lattix.network_egress

import rego.v1

default allow = false

allow if {
  input.action == "network_egress"
  input.target in input.allowed_targets
}
