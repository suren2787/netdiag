# netdiag — build plan (phase 1)

About 10 sessions of 2 hours each, working alone with Claude Code.
Each build session has a skill. Run it by typing the skill name in Claude Code, for example `/build-renderer`.

## Before you start
- [ ] Request a read-only IAM role in the staging account, with an EKS access entry using `AmazonEKSViewPolicy`. This depends on another team, so ask on day 1.

## Session 1 — Setup
- [ ] Open this folder in VS Code.
- [ ] Install prerequisites (see README).
- [ ] `python -m venv .venv && source .venv/bin/activate && pip install -e ".[dev]"`
- [ ] `pytest` passes (derive rules, schema, command guard).
- [ ] In Claude Code, run `/hooks` and check the PreToolUse Bash hook is listed.

## Session 2 — Contract (by hand, no Claude)
- [ ] Pick one app already in staging.
- [ ] Copy `templates/network.template.yaml` to `out/<app>/expected.yaml` and fill it in by hand from the AWS console and kubectl.
- [ ] Copy `templates/declared.template.yaml` to `out/<app>/declared.yaml` and fill it in. Run `netdiag validate out/<app>/declared.yaml`.
- [ ] Fix anything in the template or `docs/design.md` that turned out wrong. Do this before any code is written.

## Sessions 3–4 — Renderer
- [ ] `/build-renderer`
- [ ] Gate: if the D2 diagram is still cluttered after these two sessions, switch to a fixed SVG template before going further.

## Session 5 — Fixtures
- [ ] `/capture-fixtures <cluster> <namespace> <deployment>`
- [ ] Check the script's secret check printed OK (no container `env`/`envFrom`, no `last-applied-configuration`).
- [ ] Commit the fixtures only if this repo stays internal. They contain real staging IDs and hostnames.

## Session 6 — Kubernetes extractor
- [ ] `/build-k8s-extractor`

## Sessions 7–8 — AWS extractor
- [ ] `/build-aws-extractor`

## Session 9 — Merge and CLI
- [ ] `/build-merge-cli`

## Session 10 — Pilot
- [ ] Run `netdiag run` on the app from session 2. Diff `network.yaml` against `out/<app>/expected.yaml`. That diff is the test.
- [ ] Run it on a second app with its tech lead.
- [ ] Add it to the architecture review checklist.

## Not in phase 1
No LLM at run time, no flow logs, no drift report, no CI automation, no UI, no database.
