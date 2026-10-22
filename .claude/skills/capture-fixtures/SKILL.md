---
name: capture-fixtures
description: Session 5. Capture raw AWS and Kubernetes JSON for one staging app into tests/fixtures.
disable-model-invocation: true
argument-hint: <cluster> <namespace> <deployment>
---
Capture fixtures for cluster `$0`, namespace `$1`, deployment `$2`.

1. Check access first: run `aws sts get-caller-identity` and `kubectl config current-context`. Show me both and wait for me to confirm they point at staging.
2. Run `scripts/capture_fixtures.sh $0 $1 $2`.
3. Confirm the script's "Secret check" step printed OK. It fails and deletes the file if any container still has `env` or `envFrom`, or if `last-applied-configuration` is present. A label named `env` is expected and is not a leak. If the check failed, stop and tell me.
4. List the files written and their sizes.

Do not edit the files. Do not run any other AWS or kubectl commands.
