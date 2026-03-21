package lattix.filesystem_access_test

import rego.v1

import data.lattix.filesystem_access

test_allow_read_under_allowed_root if {
  filesystem_access.allow with input as {
    "action": "read",
    "path": "/workspace/project/file.txt",
    "allowed_paths": ["/workspace/project"]
  }
}

test_deny_read_outside_allowed_root if not filesystem_access.allow with input as {
  "action": "read",
  "path": "/etc/passwd",
  "allowed_paths": ["/workspace/project"]
}
