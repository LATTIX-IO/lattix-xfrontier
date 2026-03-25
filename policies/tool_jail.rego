package lattix.tool_jail

import rego.v1

default allow = false

valid_uid(uid) if {
  regex.match("^[0-9]+$", uid)
}

non_root_user if {
  run_as_user := trim(object.get(input, "run_as_user", ""), " ")
  run_as_user != ""
  uid := split(run_as_user, ":")[0]
  valid_uid(uid)
  to_number(uid) > 0
}

network_safe if {
  input.allow_network != true
}

network_safe if {
  input.require_egress_mediation == true
}

allow if {
  input.readonly_rootfs == true
  non_root_user
  network_safe
}
