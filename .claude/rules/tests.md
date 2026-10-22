---
paths:
  - "tests/**"
---
# Test rules

- Tests never call AWS or a live cluster. Use the JSON files in `tests/fixtures/aws/` and `tests/fixtures/k8s/`.
- For boto3, use `botocore.stub.Stubber` loaded with fixture responses, or pass plain dicts into the logic functions.
- For Kubernetes, pass plain dicts. Do not mock the kubernetes client internals.
- One test file per module: `test_<module>.py`.
- Each test checks one rule. Name it after the rule, for example `test_subnet_with_igw_route_is_public`.
- The end-to-end test compares generated output with `templates/network.template.yaml` field by field, ignoring `generated_at`.
- Do not edit fixture files to make a test pass. If a fixture looks wrong, stop and tell me.
