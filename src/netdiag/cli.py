"""netdiag command line.

  netdiag validate <declared.yaml>
  netdiag render <network.yaml> --out <dir>
  netdiag run --cluster <name> --namespace <ns> --deployment <name> --declared <file> --out <dir>
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator

SCHEMA_PATH = Path(__file__).resolve().parents[2] / "schema" / "declared.schema.json"


def validate_declared(path: Path) -> list[str]:
    """Validate a tech lead's declared.yaml. Returns a list of errors (empty if valid)."""
    try:
        data = yaml.safe_load(path.read_text())
    except (OSError, yaml.YAMLError) as exc:
        return [f"Cannot read {path}: {exc}"]
    schema = json.loads(SCHEMA_PATH.read_text())
    validator = Draft202012Validator(schema)
    errors = []
    for error in sorted(validator.iter_errors(data), key=lambda e: list(e.absolute_path)):
        location = "/".join(str(p) for p in error.absolute_path) or "(root)"
        errors.append(f"{location}: {error.message}")
    return errors


def cmd_validate(args: argparse.Namespace) -> int:
    errors = validate_declared(Path(args.declared))
    if errors:
        print(f"{args.declared}: {len(errors)} error(s)")
        for error in errors:
            print(f"  - {error}")
        return 1
    print(f"{args.declared}: valid")
    return 0


def cmd_render(args: argparse.Namespace) -> int:
    raise NotImplementedError("Sessions 3-4: run /build-renderer")


def cmd_run(args: argparse.Namespace) -> int:
    raise NotImplementedError("Session 9: run /build-merge-cli")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="netdiag", description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    p_validate = sub.add_parser("validate", help="Validate a tech lead's declared.yaml")
    p_validate.add_argument("declared")
    p_validate.set_defaults(func=cmd_validate)

    p_render = sub.add_parser("render", help="Render network.yaml to D2, SVG and a flow table")
    p_render.add_argument("network")
    p_render.add_argument("--out", required=True)
    p_render.set_defaults(func=cmd_render)

    p_run = sub.add_parser("run", help="Extract, merge and render for one app")
    p_run.add_argument("--cluster", required=True)
    p_run.add_argument("--namespace", required=True)
    p_run.add_argument("--deployment", required=True)
    p_run.add_argument("--declared", required=True)
    p_run.add_argument("--environment", default="stg")
    p_run.add_argument("--out", required=True)
    p_run.set_defaults(func=cmd_run)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except NotImplementedError as exc:
        print(f"netdiag {args.command}: not built yet ({exc})", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
