# Fixtures

Raw API responses for one staging app, captured with:

```
scripts/capture_fixtures.sh <cluster> <namespace> <deployment>
```

or `/capture-fixtures` in Claude Code.

- `aws/` — AWS CLI JSON output, one file per call.
- `k8s/` — kubectl JSON output. Deployments and Services have `env`, `envFrom`, `args`, `command` and the `last-applied-configuration` annotation removed.

Rules:
- Never edit these files by hand to make a test pass.
- Never add Secrets or ConfigMaps here.
- They contain real staging account IDs, ARNs and hostnames. Keep this repo internal.
