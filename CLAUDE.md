# netdiag

## What this project is
`netdiag` produces the network diagram and flow table for one application running on EKS in staging, for architecture reviews.

Phase 1 covers only what is **outside the cluster**: VPC, subnets, load balancers, WAF, CloudFront, egress, VPC endpoints, and the AWS services and systems the app depends on.

Pipeline:
1. Extract from Kubernetes and AWS → `extracted.yaml`
2. Merge with the tech lead's `declared.yaml` → `network.yaml`
3. Render `network.yaml` → D2 → SVG, and → markdown flow table

The build plan is in `docs/plan.md`. Each build session has a skill: `/build-renderer`, `/capture-fixtures`, `/build-k8s-extractor`, `/build-aws-extractor`, `/build-merge-cli`.

## The contract
- `templates/network.template.yaml` is the output contract. Every field the code produces must exist in it, with the same name and shape.
- `templates/declared.template.yaml` and `schema/declared.schema.json` define the tech lead's input.
- `docs/design.md` holds the derivation and merge rules. Follow them exactly. Do not invent new rules.
- Do not add, rename or remove fields unless I ask. If a change is needed, propose it first, then update the template, the schema and `docs/design.md` in the same change.

## Hard rules (never break these)
1. **Read-only.** AWS calls must be `describe_*`, `list_*` or `get_*` only. Kubernetes calls must be `read_*` or `list_*` only. Never create, update, patch, delete, tag, put, attach or exec. This applies to code and to commands you run.
2. **No secrets.** Never read Kubernetes Secrets or ConfigMaps. Never read or store container `env`, `envFrom`, or the `kubectl.kubernetes.io/last-applied-configuration` annotation. Never call `secretsmanager:GetSecretValue` or `ssm:GetParameter`.
3. **Do not inspect workloads directly.** Do not run `kubectl describe` or `kubectl get -o yaml/json` on deployments or pods; their output can contain secrets in env vars. Use `scripts/capture_fixtures.sh`, which strips them.
4. **No AI at run time.** No LLM or AI service calls in `src/`. The tool is deterministic code.
5. **No other network calls.** Only AWS APIs (boto3) and the Kubernetes API. No HTTP requests, telemetry or downloads in `src/`.
6. **No credentials in code.** Use the default boto3 credential chain (`AWS_PROFILE`) and the default kubeconfig. Never hardcode account IDs, ARNs, hostnames or regions.
7. **No new dependencies** beyond `pyproject.toml` unless I ask.

A PreToolUse hook (`.claude/hooks/guard_commands.py`) blocks AWS and kubectl commands that break rules 1–3. If it blocks something you think is needed, stop and tell me. Do not try another way around it.

## How to write the code
- Python 3.11+, type hints on every function, standard library first.
- Keep API calls and logic apart:
  - `src/netdiag/extract/` — API calls only. Returns plain dicts.
  - `src/netdiag/derive.py` — pure functions for derived fields (tier, path, identity, IDs, warnings). No I/O.
  - `src/netdiag/merge.py` — pure merge of extracted and declared data.
  - `src/netdiag/render/` — pure rendering from `network.yaml`.
- Pass boto3 clients and Kubernetes API objects in as arguments. Never create clients inside extractor functions.
- Use boto3 paginators wherever the operation supports pagination.
- Output must be deterministic: sort every list by `id`, then `name`. Same input gives byte-identical output.
- Fail loudly. On `AccessDenied` or a missing resource, raise an error that names the API call and the resource. Do not return empty data silently.
- When a value cannot be determined, set it to `null` and add a line to `warnings`. Do not guess.
- `derive.py` is already implemented with tests. Follow its style for the other modules.

## Accuracy
- Use only boto3 operation names and response fields that exist in the AWS documentation. If you are not sure, say so instead of guessing.
- The template comments name the API call and response field for every extracted value. Use those.

## Tests
- Every function in `extract/`, `derive.py`, `merge.py` and `render/` gets a pytest test.
- Tests use saved JSON from `tests/fixtures/`. Tests never call AWS or a live cluster.
- Run `pytest` after every change. Do not report a step as done while tests fail.

## Working style
- Do one step at a time and stop for my review after each.
- Keep changes small. Do not refactor code outside the current step.

## Commands
- Install: `pip install -e ".[dev]"`
- Test: `pytest`
- Lint: `ruff check src tests`
- Validate a tech lead file: `netdiag validate <declared.yaml>`

## Out of scope for phase 1
Do not build these, even if they seem useful: inside-the-cluster diagram, flow logs, drift reports, CI pipelines, a UI, a database, caching, multi-cluster or multi-app runs.
