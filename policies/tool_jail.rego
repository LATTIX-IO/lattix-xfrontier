package lattix.tool_jail

import rego.v1

default allow = false

network_safe if {
  input.allow_network != true
}

network_safe if {
  input.require_egress_mediation == true
}

allow if {
  input.readonly_rootfs == true
  not startswith(input.run_as_user, "0")
  network_safe
}
