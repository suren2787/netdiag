---
name: build-merge-cli
description: Session 9. Merge extracted and declared data and wire up the run command.
disable-model-invocation: true
---
Do one step at a time. Run `pytest` and stop for my review after each.

1. Implement `merge()` in `src/netdiag/merge.py` following the merge rules in `docs/design.md`. Add `tests/test_merge.py`.
2. Implement the `run` command in `src/netdiag/cli.py`:
   - validate `declared.yaml` with `validate_declared` (already implemented)
   - create boto3 clients and the Kubernetes API objects from the default profile and kubeconfig
   - call the extractors and write `<out>/extracted.yaml`
   - merge and write `<out>/network.yaml`
   - render and write `<out>/network.d2`, `<out>/network.svg`, `<out>/flows.md`
3. Add an end-to-end test that runs extract and merge on the fixtures and compares the result with `templates/network.template.yaml`, ignoring `generated_at`.

Do not run `netdiag run` against a live account. I will do that myself in session 10.
