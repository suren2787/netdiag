---
name: build-k8s-extractor
description: Session 6. Kubernetes extractor, from deployment to load balancer hostname.
disable-model-invocation: true
---
Implement the functions in `src/netdiag/extract/k8s.py`.

Read first:
- `.claude/rules/extract.md` (lookup chain steps 1-3, stripping rules)
- `tests/fixtures/k8s/*.json`
- The `ingress` and `workload` sections of `templates/network.template.yaml`

Do one function at a time, in the order they appear in the file. Each gets tests in `tests/test_k8s.py` that use the fixtures. Run `pytest` and stop for my review after each function.

Strip the Deployment as the rules say before returning it. Never read Secrets or ConfigMaps.
