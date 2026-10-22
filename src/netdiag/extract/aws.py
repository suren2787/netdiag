"""AWS extractor (sessions 7-8, /build-aws-extractor).

Lookup chain steps 4-7 and the allowed operations are in .claude/rules/extract.md.
Each extracted field, with its API call and response field, is in templates/network.template.yaml.

boto3 clients are passed in. Use paginators. Derived values come from netdiag.derive.
"""
from __future__ import annotations

from typing import Any


def get_cluster(eks: Any, cluster_name: str) -> dict[str, Any]:
    """eks.describe_cluster -> the `cluster` section plus vpc_id and cluster subnet IDs."""
    raise NotImplementedError("Session 7: /build-aws-extractor")


def get_vpc_network(ec2: Any, vpc_id: str, cluster_subnet_ids: list[str], region: str) -> dict[str, Any]:
    """The `vpc` section: CIDRs, subnets (with default_route, tier, cluster_subnet),
    NAT gateways, Transit Gateway attachments, VPC endpoints.
    """
    raise NotImplementedError("Session 7: /build-aws-extractor")


def get_load_balancer(elbv2: Any, wafv2: Any, cloudfront: Any, lb_hostname: str) -> dict[str, Any]:
    """Match lb_hostname to DNSName, then listeners, WAF ACL and CloudFront distribution.

    Returns {"load_balancer": {...}, "cloudfront": {...} or None}.
    """
    raise NotImplementedError("Session 8: /build-aws-extractor")


def get_workload_identity(
    eks: Any, cluster_name: str, namespace: str, service_account: str, irsa_role_arn: str | None
) -> dict[str, Any]:
    """The `workload` section: service_account, identity, iam_role. Uses derive.workload_identity."""
    raise NotImplementedError("Session 8: /build-aws-extractor")


def get_role_dependencies(iam: Any, role_arn: str) -> list[dict[str, Any]]:
    """aws-service dependencies from the role's attached and inline policies.

    One dependency per service + resource. Statements with Effect Deny are ignored.
    Resource "*" produces a warning via derive.wildcard_resource_warning.
    """
    raise NotImplementedError("Session 8: /build-aws-extractor")
