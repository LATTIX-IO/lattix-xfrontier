package lattix.data_classification

import rego.v1

default classification = "internal"

classification := "restricted" if {
  contains(lower(input.text), "ssn")
}

classification := "confidential" if {
  contains(lower(input.text), "customer")
}
