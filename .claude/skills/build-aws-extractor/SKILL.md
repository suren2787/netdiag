---
name: build-aws-extractor
description: Sessions 7-8. AWS extractor for cluster networking, load balancer and IAM role.
disable-model-invocation: true
---
Implement the functions in `src/netdiag/extract/aws.py`.

Read first:
- `.claude/rules/extract.md` (lookup chain steps 4-7, allowed operations)
- `tests/fixtures/aws/*.json`
- `templates/network.template.yaml` (each extracted field names its API call and response field)
- `src/netdiag/derive.py` (use these functions for derived fields)

Order:
1. `get_cluster` and `get_vpc_network`
2. `get_load_balancer`
3. `get_workload_identity` and `get_role_dependencies`

Each function takes boto3 clients as arguments and gets tests in `tests/test_aws.py` using `botocore.stub.Stubber` with fixture responses. Use paginators.

If a derivation rule is missing from `derive.py`, add a pure function there with a test. Do not put derivation logic in `aws.py`.

Run `pytest` and stop for my review after each numbered step.
