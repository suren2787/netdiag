from netdiag import derive

ROUTE_TABLES = [
    {
        "RouteTableId": "rtb-main",
        "Associations": [{"Main": True}],
        "Routes": [{"DestinationCidrBlock": "10.40.0.0/20", "GatewayId": "local"}],
    },
    {
        "RouteTableId": "rtb-public",
        "Associations": [{"SubnetId": "subnet-pub", "Main": False}],
        "Routes": [{"DestinationCidrBlock": "0.0.0.0/0", "GatewayId": "igw-1"}],
    },
    {
        "RouteTableId": "rtb-private",
        "Associations": [{"SubnetId": "subnet-priv", "Main": False}],
        "Routes": [{"DestinationCidrBlock": "0.0.0.0/0", "TransitGatewayId": "tgw-1"}],
    },
    {
        "RouteTableId": "rtb-broken",
        "Associations": [{"SubnetId": "subnet-blackhole", "Main": False}],
        "Routes": [{"DestinationCidrBlock": "0.0.0.0/0", "NatGatewayId": "nat-1", "State": "blackhole"}],
    },
]


def test_subnet_with_explicit_association_uses_its_route_table():
    assert derive.default_route_for_subnet("subnet-priv", ROUTE_TABLES) == "tgw-1"


def test_subnet_without_association_uses_main_route_table():
    assert derive.default_route_for_subnet("subnet-unassociated", ROUTE_TABLES) is None


def test_blackhole_default_route_counts_as_none():
    assert derive.default_route_for_subnet("subnet-blackhole", ROUTE_TABLES) is None


def test_subnet_with_igw_route_is_public():
    assert derive.subnet_tier("igw-1") == "public"


def test_subnet_with_nat_or_tgw_route_is_private():
    assert derive.subnet_tier("nat-1") == "private"
    assert derive.subnet_tier("tgw-1") == "private"


def test_subnet_without_default_route_is_isolated():
    assert derive.subnet_tier(None) == "isolated"


def test_unrecognised_route_target_is_private_with_warning():
    assert derive.subnet_tier("pcx-1") == "private"
    assert "pcx-1" in derive.route_target_warning("subnet-x", "pcx-1")
    assert derive.route_target_warning("subnet-x", "tgw-1") is None


def test_egress_from_matching_cluster_subnets():
    assert derive.egress_route(["tgw-1", "tgw-1"]) == ("tgw", None)


def test_egress_is_mixed_when_cluster_subnets_disagree():
    egress, warning = derive.egress_route(["tgw-1", "nat-1"])
    assert egress == "mixed"
    assert warning is not None


def test_endpoint_short_name_strips_region_prefix():
    assert derive.endpoint_short_name("com.amazonaws.ap-east-1.ecr.api", "ap-east-1") == "ecr.api"


def test_pod_identity_takes_precedence_over_irsa():
    assert derive.workload_identity("arn:role/a", "arn:role/b") == ("pod-identity", "arn:role/a", None)


def test_irsa_used_when_no_pod_identity():
    assert derive.workload_identity(None, "arn:role/b") == ("irsa", "arn:role/b", None)


def test_node_role_used_when_no_workload_role_with_warning():
    identity, role, warning = derive.workload_identity(None, None)
    assert (identity, role) == ("node-role", None)
    assert warning is not None


def test_aws_service_with_endpoint_uses_vpc_endpoint():
    assert derive.dependency_path("aws-service", "secretsmanager", {"secretsmanager"}, "tgw") == "vpc-endpoint"


def test_aws_service_without_endpoint_uses_egress():
    assert derive.dependency_path("aws-service", "sqs", {"secretsmanager"}, "nat") == "nat"


def test_paths_by_dependency_type():
    assert derive.dependency_path("data-store", "rds-postgres", set(), "tgw") == "in-vpc"
    assert derive.dependency_path("on-prem", None, set(), "nat") == "tgw"
    assert derive.dependency_path("external", None, set(), "nat") == "nat"


def test_ids_assigned_after_sorting_by_name():
    items = derive.assign_ids([{"name": "b"}, {"name": "a"}], "D")
    assert items == [{"id": "D1", "name": "a"}, {"id": "D2", "name": "b"}]


def test_wildcard_resource_warns():
    assert derive.wildcard_resource_warning("s3:GetObject", "*") is not None
    assert derive.wildcard_resource_warning("s3:GetObject", "arn:aws:s3:::bucket/*") is None


def test_http_listener_without_redirect_warns():
    assert derive.http_listener_warning("I1", {"port": 80, "protocol": "HTTP"}) is not None
    assert derive.http_listener_warning("I1", {"port": 80, "protocol": "HTTP", "default_action": "redirect"}) is None


def test_internet_facing_without_waf_warns():
    ingress = {"id": "I1", "load_balancer": {"scheme": "internet-facing", "waf_acl": None}, "cloudfront": None}
    assert derive.unprotected_ingress_warning(ingress) is not None
    ingress["load_balancer"]["waf_acl"] = "acl"
    assert derive.unprotected_ingress_warning(ingress) is None


def test_public_api_endpoint_open_to_world_warns():
    assert derive.public_api_endpoint_warning({"public": True, "public_cidrs": ["0.0.0.0/0"]}) is not None
    assert derive.public_api_endpoint_warning({"private": True, "public": False, "public_cidrs": []}) is None
