package lattix.tool_jail_test

import rego.v1

import data.lattix.tool_jail

test_allow_safe_tool_jail if {
  tool_jail.allow with input as {
    "readonly_rootfs": true,
    "require_egress_mediation": true,
    "allow_network": true,
    "run_as_user": "1000:1000"
  }
}

test_deny_root_user if not tool_jail.allow with input as {
  "readonly_rootfs": true,
  "require_egress_mediation": true,
  "allow_network": false,
  "run_as_user": "0:0"
}
