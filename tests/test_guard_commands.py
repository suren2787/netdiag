"""Tests for the Claude Code PreToolUse hook in .claude/hooks/guard_commands.py."""
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

HOOK = Path(__file__).resolve().parents[1] / ".claude" / "hooks" / "guard_commands.py"
spec = importlib.util.spec_from_file_location("guard_commands", HOOK)
guard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guard)

ALLOWED = [
    "pytest -q",
    "aws sts get-caller-identity",
    "aws --profile stg --region ap-east-1 eks describe-cluster --name platform-stg",
    "aws ec2 describe-subnets --filters Name=vpc-id,Values=vpc-1 --output json > out.json",
    "aws elbv2 describe-load-balancers --query 'LoadBalancers[].DNSName'",
    "aws iam list-attached-role-policies --role-name app",
    "aws iam get-policy-version --policy-arn arn:aws:iam::1:policy/p --version-id v1",
    "aws s3 ls",
    "kubectl get ingress -n payments",
    "kubectl get deploy -n payments",
    "kubectl get deploy payments-api -n payments -o wide",
    "kubectl get svc -n payments -o json",
    "kubectl describe ingress payments-api -n payments",
    "kubectl auth can-i list services -n payments",
    "kubectl config current-context",
    "aws ec2 describe-vpcs | jq '.Vpcs[]'",
    "scripts/capture_fixtures.sh platform-stg payments payments-api",
]

BLOCKED = [
    "aws ec2 delete-vpc --vpc-id vpc-1",
    "aws --region ap-east-1 ec2 create-tags --resources x --tags Key=a,Value=b",
    "aws iam put-role-policy --role-name x --policy-name y --policy-document file://p.json",
    "aws secretsmanager get-secret-value --secret-id x",
    "aws ssm get-parameter --name x --with-decryption",
    "aws eks get-token --cluster-name x",
    "aws ecr get-login-password",
    "aws eks update-kubeconfig --name x",
    "aws configure set region x",
    "aws s3 cp s3://bucket/key .",
    "aws ec2 describe-vpcs && aws ec2 delete-vpc --vpc-id vpc-1",
    "bash -c 'aws ec2 terminate-instances --instance-ids i-1'",
    "echo x; $(aws iam delete-role --role-name x)",
    "kubectl delete deploy payments-api",
    "kubectl apply -f x.yaml",
    "kubectl exec -it pod -- sh",
    "kubectl logs pod-1",
    "kubectl get secrets -n payments",
    "kubectl get secret/db -n payments -o yaml",
    "kubectl describe configmap app",
    "kubectl get cm,svc -n payments",
    "kubectl get deploy payments-api -n payments -o yaml",
    "kubectl get deployment/payments-api -ojson",
    "kubectl get pods -n payments --output=jsonpath='{..env}'",
    "kubectl describe deploy payments-api",
    "kubectl describe pod pod-1",
    "kubectl get all -n payments -o yaml",
    "kubectl get --raw /api/v1/namespaces/payments/secrets",
    "kubectl config use-context prod",
    "cat ~/.aws/credentials",
    "/usr/local/bin/aws ec2 delete-subnet --subnet-id s",
]


@pytest.mark.parametrize("command", ALLOWED)
def test_allowed(command):
    assert guard.check(command) is None


@pytest.mark.parametrize("command", BLOCKED)
def test_blocked(command):
    assert guard.check(command) is not None


def run_hook(payload: dict) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(HOOK)], input=json.dumps(payload),
                          capture_output=True, text=True)


def test_hook_exits_2_with_reason_on_stderr():
    result = run_hook({"tool_name": "Bash", "tool_input": {"command": "kubectl get secrets"}})
    assert result.returncode == 2
    assert "Blocked by netdiag guard" in result.stderr


def test_hook_exits_0_for_allowed_command():
    result = run_hook({"tool_name": "Bash", "tool_input": {"command": "aws ec2 describe-vpcs"}})
    assert result.returncode == 0
