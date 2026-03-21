package lattix.filesystem_access

import rego.v1

default allow = false

allow if {
  input.action == "read"
  some allowed_path in input.allowed_paths
  startswith(input.path, allowed_path)
}
