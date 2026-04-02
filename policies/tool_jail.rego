package lattix.tool_jail

import rego.v1

default allow = false

command_executable := value if {
  command := object.get(input, "command", [])
  is_array(command)
  count(command) > 0
  raw := command[0]
  value := trim(sprintf("%v", [raw]), " ")
  value != ""
}

command_executable := value if {
  command := object.get(input, "command", [])
  not is_array(command)
  value := trim(object.get(input, "tool", object.get(input, "action", "")), " ")
  value != ""
}

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

executable_safe if {
  allowed_executables := object.get(input, "allowed_executables", [])
  is_array(allowed_executables)
  count(allowed_executables) > 0
  executable := command_executable
  executable in allowed_executables
}

network_targets_safe if {
  input.allow_network != true
  requested_hosts := object.get(input, "requested_hosts", [])
  count(requested_hosts) == 0
}

network_targets_safe if {
  input.allow_network == true
  allowed_hosts := object.get(input, "allowed_hosts", [])
  requested_hosts := object.get(input, "requested_hosts", [])
  count(allowed_hosts) > 0
  count(requested_hosts) > 0
  every host in requested_hosts {
    host in allowed_hosts
  }
}

allow if {
  input.readonly_rootfs == true
  non_root_user
  network_safe
  executable_safe
  network_targets_safe
}
