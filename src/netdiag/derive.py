"""Derivation rules. Pure functions, no I/O.

Each function implements one row of the "Derivation rules" table in docs/design.md.
"""
from __future__ import annotations

from typing import Any

ROUTE_TARGET_KEYS = (
    "GatewayId",
    "NatGatewayId",
    "TransitGatewayId",
    "NetworkInterfaceId",
    "VpcPeeringConnectionId",
    "InstanceId",
    "LocalGatewayId",
    "CarrierGatewayId",
    "CoreNetworkArn",
)

AWS_SERVICE_DEFAULTS = {"port": 443, "protocol": "https", "tls": True, "auth": "iam"}


def default_route_for_subnet(subnet_id: str, route_tables: list[dict[str, Any]]) -> str | None:
    """Target of the 0.0.0.0/0 route for a subnet.

    route_tables: RouteTables[] from ec2 describe_route_tables for the VPC.
    A subnet with no explicit association uses the main route table.
    Returns None if there is no active default route.
    """
    explicit = None
    main = None
    for table in route_tables:
        for assoc in table.get("Associations", []):
            if assoc.get("SubnetId") == subnet_id:
                explicit = table
            if assoc.get("Main"):
                main = table
    table = explicit or main
    if table is None:
        return None
    for route in table.get("Routes", []):
        if route.get("DestinationCidrBlock") != "0.0.0.0/0":
            continue
        if route.get("State") == "blackhole":
            return None
        for key in ROUTE_TARGET_KEYS:
            if route.get(key):
                return route[key]
    return None


def subnet_tier(default_route: str | None) -> str:
    """igw-* is public, nat-* or tgw-* is private, no default route is isolated.

    Any other target is treated as private; use route_target_warning to flag it.
    """
    if default_route is None:
        return "isolated"
    if default_route.startswith("igw-"):
        return "public"
    return "private"


def route_target_warning(subnet_id: str, default_route: str | None) -> str | None:
    if default_route is None or default_route.startswith(("igw-", "nat-", "tgw-")):
        return None
    return f"Subnet {subnet_id} default route goes to {default_route}; tier set to private"


def egress_route(cluster_subnet_routes: list[str | None]) -> tuple[str, str | None]:
    """Egress path from the cluster subnets' default routes.

    Returns (egress, warning). egress is nat, tgw, igw, none or mixed.
    """
    def kind(route: str | None) -> str:
        if route is None:
            return "none"
        for prefix, name in (("nat-", "nat"), ("tgw-", "tgw"), ("igw-", "igw")):
            if route.startswith(prefix):
                return name
        return "other"

    kinds = sorted({kind(r) for r in cluster_subnet_routes})
    if not kinds:
        return "none", "No cluster subnets found"
    if len(kinds) > 1:
        return "mixed", f"Cluster subnets use different egress routes: {', '.join(kinds)}"
    if kinds[0] == "other":
        return "other", "Cluster subnets use an unrecognised egress route"
    return kinds[0], None


def endpoint_short_name(service_name: str, region: str) -> str:
    """com.amazonaws.ap-east-1.ecr.api -> ecr.api"""
    prefix = f"com.amazonaws.{region}."
    if service_name.startswith(prefix):
        return service_name[len(prefix):]
    return service_name


def workload_identity(
    pod_identity_role: str | None, irsa_role: str | None
) -> tuple[str, str | None, str | None]:
    """Returns (identity, iam_role, warning)."""
    if pod_identity_role:
        return "pod-identity", pod_identity_role, None
    if irsa_role:
        return "irsa", irsa_role, None
    return "node-role", None, "No Pod Identity or IRSA role found; the app uses the node role"


def dependency_path(dep_type: str, service: str | None, vpc_endpoints: set[str], egress: str) -> str:
    """Network path a dependency is reached through. See docs/design.md."""
    if dep_type == "aws-service":
        return "vpc-endpoint" if service in vpc_endpoints else egress
    if dep_type == "data-store":
        return "in-vpc"
    if dep_type == "on-prem":
        return "tgw"
    return egress


def assign_ids(items: list[dict[str, Any]], prefix: str) -> list[dict[str, Any]]:
    """Sort by name and set id = <prefix>1..n. Returns new dicts with id first."""
    ordered = sorted(items, key=lambda item: item.get("name") or item.get("hostname") or "")
    return [{"id": f"{prefix}{i}", **{k: v for k, v in item.items() if k != "id"}}
            for i, item in enumerate(ordered, start=1)]


# ---------- warnings ----------

def wildcard_resource_warning(action: str | list[str], resource: str | list[str]) -> str | None:
    resources = [resource] if isinstance(resource, str) else resource
    if "*" not in resources:
        return None
    actions = [action] if isinstance(action, str) else action
    return f"IAM role grants {', '.join(sorted(actions))} on Resource '*' - resource not identifiable"


def http_listener_warning(ingress_id: str, listener: dict[str, Any]) -> str | None:
    if listener.get("protocol") != "HTTP":
        return None
    if listener.get("default_action") == "redirect":
        return None
    return f"Listener {listener.get('port')}/HTTP on {ingress_id} does not redirect to HTTPS"


def unprotected_ingress_warning(ingress: dict[str, Any]) -> str | None:
    lb = ingress.get("load_balancer") or {}
    if lb.get("scheme") != "internet-facing":
        return None
    if lb.get("waf_acl"):
        return None
    cloudfront = ingress.get("cloudfront") or {}
    if cloudfront.get("waf_acl"):
        return None
    return f"Internet-facing load balancer on {ingress.get('id')} has no WAF"


def public_api_endpoint_warning(api_endpoint: dict[str, Any]) -> str | None:
    if api_endpoint.get("public") and "0.0.0.0/0" in (api_endpoint.get("public_cidrs") or []):
        return "EKS API endpoint is public and open to 0.0.0.0/0"
    return None
