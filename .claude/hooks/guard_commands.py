#!/usr/bin/env python3
"""PreToolUse hook for Bash.

Blocks AWS CLI and kubectl commands that change state or can expose secrets.
Exit 2 blocks the command; the message on stderr goes back to Claude.
Exit 0 lets the normal permission flow decide.

Test it with: pytest tests/test_guard_commands.py
"""
from __future__ import annotations

import json
import os
import shlex
import sys

# ---------- AWS CLI ----------
AWS_ALLOWED_PREFIXES = ("describe-", "list-", "get-")
AWS_BLOCKED_OPERATIONS = {
    "get-secret-value",
    "batch-get-secret-value",
    "get-parameter",
    "get-parameters",
    "get-parameters-by-path",
    "get-login-password",
    "get-authorization-token",
    "get-token",
    "get-session-token",
    "get-federation-token",
    "get-credentials-for-identity",
    "get-role-credentials",
}
AWS_GLOBAL_OPTIONS_WITH_VALUE = {
    "--profile", "--region", "--output", "--query", "--endpoint-url",
    "--cli-read-timeout", "--cli-connect-timeout", "--color", "--ca-bundle",
    "--cli-binary-format",
}

# ---------- kubectl ----------
KUBECTL_ALLOWED_VERBS = {
    "get", "describe", "api-resources", "api-versions", "version", "explain", "cluster-info",
}
KUBECTL_ALLOWED_SUBCOMMANDS = {
    "auth": {"can-i"},
    "config": {"view", "get-contexts", "current-context", "get-clusters"},
}
KUBECTL_OPTIONS_WITH_VALUE = {
    "-n", "--namespace", "--context", "--kubeconfig", "--cluster", "--user",
    "-o", "--output", "-l", "--selector", "--field-selector", "-f", "--filename",
    "--request-timeout", "-s", "--server", "--token", "--as", "--as-group",
}
SECRET_KINDS = {"secret", "secrets", "configmap", "configmaps", "cm"}
WORKLOAD_KINDS = {
    "all",
    "deployment", "deployments", "deploy",
    "pod", "pods", "po",
    "replicaset", "replicasets", "rs",
    "statefulset", "statefulsets", "sts",
    "daemonset", "daemonsets", "ds",
    "job", "jobs",
    "cronjob", "cronjobs", "cj",
}
SAFE_OUTPUT_FORMATS = {"wide", "name"}

# ---------- files ----------
CREDENTIAL_PATHS = (".aws/credentials", ".aws/sso/cache", ".aws/cli/cache")

SEPARATORS = {"&&", "||", ";", "|", "|&", "&", "(", ")", ">", ">>", "<", "<<", ">&", "&>"}


def tokenize(command: str) -> list[str]:
    lexer = shlex.shlex(command.replace("\n", " ; "), posix=True, punctuation_chars=True)
    lexer.whitespace_split = True
    return list(lexer)


def segments(tokens: list[str]) -> list[list[str]]:
    result: list[list[str]] = [[]]
    for token in tokens:
        if token in SEPARATORS or (token and set(token) <= set("&|;()<>")):
            result.append([])
        else:
            result[-1].append(token)
    return [s for s in result if s]


def positionals(args: list[str], options_with_value: set[str]) -> list[str]:
    found: list[str] = []
    skip_next = False
    for arg in args:
        if skip_next:
            skip_next = False
            continue
        if arg.startswith("-"):
            if "=" not in arg and arg in options_with_value:
                skip_next = True
            continue
        found.append(arg)
    return found


def option_value(args: list[str], short: str, long: str) -> str | None:
    for i, arg in enumerate(args):
        if arg in (short, long) and i + 1 < len(args):
            return args[i + 1]
        if arg.startswith(long + "=") or arg.startswith(short + "="):
            return arg.split("=", 1)[1]
        if arg.startswith(short) and len(arg) > len(short) and not arg.startswith("--"):
            return arg[len(short):]
    return None


def check_aws(args: list[str]) -> str | None:
    pos = positionals(args, AWS_GLOBAL_OPTIONS_WITH_VALUE)
    if len(pos) < 2:
        return None  # e.g. "aws --version"
    service, operation = pos[0], pos[1]
    if service == "s3":
        return None if operation == "ls" else f"'aws s3 {operation}' is not allowed. Only 'aws s3 ls' is read-only."
    if service == "configure":
        return "'aws configure' changes local AWS config. Ask the user to run it."
    if service == "eks" and operation == "update-kubeconfig":
        return "'aws eks update-kubeconfig' changes the local kubeconfig. Ask the user to run it."
    if operation in AWS_BLOCKED_OPERATIONS:
        return f"'aws {service} {operation}' returns secrets or credentials and is not allowed."
    if not operation.startswith(AWS_ALLOWED_PREFIXES):
        return f"'aws {service} {operation}' is not read-only. Only describe-*, list-* and get-* are allowed."
    return None


def check_kubectl(args: list[str]) -> str | None:
    if "--raw" in args or any(a.startswith("--raw=") for a in args):
        return "'kubectl --raw' is not allowed."
    pos = positionals(args, KUBECTL_OPTIONS_WITH_VALUE)
    if not pos:
        return None
    verb = pos[0]
    if verb in KUBECTL_ALLOWED_SUBCOMMANDS:
        sub = pos[1] if len(pos) > 1 else ""
        if sub in KUBECTL_ALLOWED_SUBCOMMANDS[verb]:
            return None
        return f"'kubectl {verb} {sub}' is not allowed."
    if verb not in KUBECTL_ALLOWED_VERBS:
        return f"'kubectl {verb}' is not read-only. Only get, describe and read-only info commands are allowed."
    if verb in ("get", "describe"):
        kinds = set()
        for resource in pos[1:]:
            for part in resource.split(","):
                kinds.add(part.split("/", 1)[0].split(".", 1)[0].lower())
        if kinds & SECRET_KINDS:
            return "Reading Secrets or ConfigMaps is not allowed."
        if kinds & WORKLOAD_KINDS:
            if verb == "describe":
                return ("'kubectl describe' on workloads shows env vars, which can contain secrets. "
                        "Use scripts/capture_fixtures.sh instead.")
            output = option_value(args, "-o", "--output")
            if output is not None and output.split("=", 1)[0] not in SAFE_OUTPUT_FORMATS:
                return ("Full workload output (-o json/yaml/jsonpath) can contain secrets in env vars. "
                        "Use scripts/capture_fixtures.sh instead.")
    return None


def check(command: str) -> str | None:
    """Return a reason to block, or None to allow."""
    if any(path in command for path in CREDENTIAL_PATHS):
        return "Reading local AWS credential files is not allowed."
    try:
        tokens = tokenize(command)
    except ValueError:
        if "aws" in command or "kubectl" in command:
            return "Command could not be parsed. Simplify it so it can be checked."
        return None

    for segment in segments(tokens):
        for i, token in enumerate(segment):
            # Quoted strings passed to bash -c, sh -c, xargs, etc.
            if " " in token and ("aws " in token or "kubectl " in token):
                reason = check(token)
                if reason:
                    return reason
            name = os.path.basename(token)
            if name == "aws":
                reason = check_aws(segment[i + 1:])
                if reason:
                    return reason
                break
            if name == "kubectl":
                reason = check_kubectl(segment[i + 1:])
                if reason:
                    return reason
                break
    return None


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError:
        return 0
    if payload.get("tool_name") != "Bash":
        return 0
    command = (payload.get("tool_input") or {}).get("command", "")
    reason = check(command)
    if reason:
        print(f"Blocked by netdiag guard: {reason}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
