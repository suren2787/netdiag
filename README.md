# netdiag

Generates the network diagram and flow table for an app running on EKS in staging, for architecture reviews.
Phase 1 covers what is outside the cluster.

- Design and rules: [docs/design.md](docs/design.md)
- Build plan: [docs/plan.md](docs/plan.md)
- Guide for tech leads: [docs/tech-lead-guide.md](docs/tech-lead-guide.md)

## Prerequisites
- Python 3.11+
- AWS CLI v2, kubectl, jq 1.6+
- D2 CLI: https://d2lang.com (`brew install d2` on macOS)
- Claude Code (VS Code extension or CLI)

## Setup
```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest
```
`pytest` should pass from day 1: it covers the derivation rules, the tech lead schema and the command guard.

Run `aws eks update-kubeconfig --name <cluster>` yourself before using Claude Code. The guard blocks Claude from running it.

## Usage
```bash
netdiag validate declared.yaml                       # works now
netdiag render network.yaml --out out/<app>          # after sessions 3-4
netdiag run --cluster <c> --namespace <ns> --deployment <d> \
            --declared declared.yaml --out out/<app>  # after session 9
```

## Layout
```
CLAUDE.md                      Project rules Claude Code loads every session
.claude/
  settings.json                Permissions (allow / ask / deny) and the PreToolUse hook
  hooks/guard_commands.py      Blocks AWS and kubectl commands that change state or expose secrets
  rules/                       Path-scoped rules (extractors, renderers, tests)
  skills/                      One slash command per build session
docs/                          Design, plan, tech lead guide
templates/                     network.template.yaml (output contract), declared.template.yaml
schema/declared.schema.json    Validation for the tech lead file (also used by VS Code YAML autocomplete)
scripts/capture_fixtures.sh    Captures raw AWS and Kubernetes JSON for tests
src/netdiag/
  cli.py                       Commands (validate implemented)
  derive.py                    Derivation rules (implemented, tested)
  merge.py                     Merge rules (session 9)
  extract/k8s.py, aws.py       Extractors (sessions 6-8)
  render/d2.py, table.py       Renderers (sessions 3-4)
tests/                         pytest; fixtures/ holds captured JSON
```

## Guardrails
Three layers, from soft to hard:

1. `CLAUDE.md` and `.claude/rules/` — instructions Claude follows.
2. `.claude/settings.json` — permissions. Read-only AWS and kubectl commands run without asking. Edits to the contract (`templates/`, `schema/`, `docs/design.md`), the guardrail files and fixtures always ask. Secrets, `curl`, `wget` and credential files are denied.
3. `.claude/hooks/guard_commands.py` — runs before every Bash command and blocks it (exit code 2) if it:
   - calls an AWS operation that is not `describe-*`, `list-*` or `get-*`, or returns credentials (`get-secret-value`, `get-parameter`, `get-token`, ...)
   - runs a kubectl verb other than `get`, `describe` or read-only info commands
   - reads Secrets or ConfigMaps
   - dumps a workload as JSON/YAML or runs `describe` on it (env vars can hold secrets)
   - reads local AWS credential files

Tests for the hook: `tests/test_guard_commands.py`. Check it is active with `/hooks` in Claude Code.
