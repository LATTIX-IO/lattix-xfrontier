package lattix.tool_jail_test

import rego.v1

import data.lattix.tool_jail

test_allow_safe_tool_jail if {
  tool_jail.allow with input as {
    "readonly_rootfs": true,
    "require_egress_mediation": true,
    "allow_network": true,
    "run_as_user": "1000:1000",
    "command": ["python", "-c", "1+1"],
    "allowed_executables": ["python"],
    "allowed_hosts": ["api.example.com"],
    "requested_hosts": ["api.example.com"]
  }
}

test_deny_root_user if not tool_jail.allow with input as {
  "readonly_rootfs": true,
  "require_egress_mediation": true,
  "allow_network": false,
  "run_as_user": "0:0",
  "command": ["python", "-c", "1+1"],
  "allowed_executables": ["python"]
}

test_deny_invalid_run_as_user if not tool_jail.allow with input as {
  "readonly_rootfs": true,
  "require_egress_mediation": true,
  "allow_network": false,
  "run_as_user": "nobody:1000",
  "command": ["python", "-c", "1+1"],
  "allowed_executables": ["python"]
}

test_deny_missing_allowed_executables if not tool_jail.allow with input as {
  "readonly_rootfs": true,
  "require_egress_mediation": true,
  "allow_network": false,
  "run_as_user": "1000:1000",
  "command": ["python", "-c", "1+1"]
}

test_deny_requested_hosts_when_network_disabled if not tool_jail.allow with input as {
  "readonly_rootfs": true,
  "require_egress_mediation": true,
  "allow_network": false,
  "run_as_user": "1000:1000",
  "command": ["python", "-c", "1+1"],
  "allowed_executables": ["python"],
  "requested_hosts": ["api.example.com"]
}

test_deny_unallowlisted_requested_hosts if not tool_jail.allow with input as {
  "readonly_rootfs": true,
  "require_egress_mediation": true,
  "allow_network": true,
  "run_as_user": "1000:1000",
  "command": ["python", "-c", "1+1"],
  "allowed_executables": ["python"],
  "allowed_hosts": ["api.example.com"],
  "requested_hosts": ["evil.example.com"]
}
