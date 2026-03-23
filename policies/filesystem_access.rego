package lattix.filesystem_access

import rego.v1

default allow = false

allow if {
  input.action == "read"
  some allowed_path in input.allowed_paths
  input.path == allowed_path
}

allow if {
  input.action == "read"
  some allowed_path in input.allowed_paths
  startswith(input.path, sprintf("%s/", [trim_suffix(allowed_path, "/")]))
}
