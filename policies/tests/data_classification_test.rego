package lattix.data_classification_test

import rego.v1

import data.lattix.data_classification

test_restricted_text if {
  data_classification.classification == "restricted" with input as {"text": "contains SSN data"}
}

test_confidential_text if {
  data_classification.classification == "confidential" with input as {"text": "customer escalation"}
}
