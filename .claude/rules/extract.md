---
paths:
  - "src/netdiag/extract/**"
  - "scripts/**"
  - "tests/test_k8s.py"
  - "tests/test_aws.py"
---
# Extractor rules

## Allowed AWS operations (boto3)
Only these. Ask before adding another.

| Client | Operations |
|---|---|
| eks | `describe_cluster`, `list_pod_identity_associations`, `describe_pod_identity_association` |
| ec2 | `describe_vpcs`, `describe_subnets`, `describe_route_tables`, `describe_nat_gateways`, `describe_vpc_endpoints`, `describe_transit_gateway_vpc_attachments` |
| elbv2 | `describe_load_balancers`, `describe_listeners` |
| wafv2 | `get_web_acl_for_resource` |
| cloudfront | `list_distributions` |
| iam | `list_attached_role_policies`, `get_policy`, `get_policy_version`, `list_role_policies`, `get_role_policy` |
| sts | `get_caller_identity` |

## Allowed Kubernetes reads (kubernetes Python client)
- `AppsV1Api.read_namespaced_deployment`
- `CoreV1Api.list_namespaced_service`, `CoreV1Api.read_namespaced_service_account`
- `NetworkingV1Api.list_namespaced_ingress`

Never call anything on Secrets or ConfigMaps. Never call `connect_*` or exec.

## Stripping before returning
From the Deployment, keep only: name, namespace, `spec.selector.matchLabels`, `spec.template.metadata.labels`, `spec.template.spec.serviceAccountName`, container names and ports.
Drop everything else, especially `env`, `envFrom`, `args`, `command`, volumes and all annotations.

## Lookup chain (follow this order)
1. Deployment → service account name and pod labels.
2. Services in the namespace whose `spec.selector` is a subset of the pod labels.
3. Ingresses in the namespace whose backends point at those Services. Services of type `LoadBalancer` count as ingress too.
4. `status.loadBalancer.ingress[].hostname` → match `DNSName` in `elbv2.describe_load_balancers` (case-insensitive).
5. Load balancer ARN → listeners, WAF (ALB only), CloudFront distributions whose origin `DomainName` equals the load balancer `DNSName`.
6. Cluster → VPC, subnets, route tables, NAT gateways, Transit Gateway attachments, VPC endpoints.
7. Service account → Pod Identity association, else IRSA annotation `eks.amazonaws.com/role-arn` → IAM role → policies.

## Notes
- `ec2.describe_nat_gateways` takes `Filter` (singular). The other ec2 calls take `Filters`.
- `describe_route_tables`: a subnet with no explicit association uses the route table where `Associations[].Main` is true.
- `wafv2.get_web_acl_for_resource` only works for ALBs, not NLBs.
- `cloudfront` is a global service. Create its client with `region_name="us-east-1"`.
- IAM policy documents from `get_role_policy` and `get_policy_version` may arrive as decoded dicts or URL-encoded strings. Handle both.
