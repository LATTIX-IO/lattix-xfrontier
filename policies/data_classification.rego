package lattix.data_classification

import rego.v1

default classification = "internal"

classification := "restricted" if {
  contains(lower(input.text), "ssn")
}

classification := "restricted" if {
  regex.match("(social security|api[_-]?key|bearer|private key)", lower(input.text))
}

classification := "confidential" if {
  contains(lower(input.text), "customer")
}

classification := "confidential" if {
  regex.match("(password|phone|email)", lower(input.text))
}
