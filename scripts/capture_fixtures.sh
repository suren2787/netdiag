#!/usr/bin/env bash
# Capture raw AWS and Kubernetes JSON for one app into tests/fixtures/.
#
# Read-only: only describe/list/get calls and kubectl get.
# Strips env, envFrom, args, command and the last-applied-configuration
# annotation from all Kubernetes objects before writing them.
#
# Usage: scripts/capture_fixtures.sh <cluster> <namespace> <deployment>
# Needs: aws CLI v2, kubectl (context pointing at the cluster), jq 1.6+
set -euo pipefail

if [[ $# -ne 3 ]]; then
  echo "Usage: $0 <cluster> <namespace> <deployment>" >&2
  exit 1
fi
CLUSTER=$1
NS=$2
DEPLOY=$3

for tool in aws kubectl jq; do
  command -v "$tool" >/dev/null || { echo "Missing tool: $tool" >&2; exit 1; }
done

ROOT=$(cd "$(dirname "$0")/.." && pwd)
AWS_DIR="$ROOT/tests/fixtures/aws"
K8S_DIR="$ROOT/tests/fixtures/k8s"
mkdir -p "$AWS_DIR" "$K8S_DIR"

# Container objects are the ones with an "image" key. Labels named "env" are kept.
STRIP='walk(
  if type == "object" then
    (if has("image") then del(.env, .envFrom, .args, .command) else . end)
    | (if (.annotations | type) == "object"
       then .annotations |= del(.["kubectl.kubernetes.io/last-applied-configuration"])
       else . end)
  else . end)'
LEAK_CHECK='[.. | objects | select(has("image") and (has("env") or has("envFrom")))] | length'

safe_name() { echo "$1" | tr -c 'A-Za-z0-9._-\n' '_'; }

echo "== Identity"
aws sts get-caller-identity --output json > "$AWS_DIR/sts_get_caller_identity.json"
jq -r '"Account: \(.Account)  Caller: \(.Arn)"' "$AWS_DIR/sts_get_caller_identity.json"
echo "kubectl context: $(kubectl config current-context)"

echo "== Cluster"
aws eks describe-cluster --name "$CLUSTER" --output json > "$AWS_DIR/eks_describe_cluster.json"
REGION=$(jq -r '.cluster.arn | split(":")[3]' "$AWS_DIR/eks_describe_cluster.json")
VPC_ID=$(jq -r '.cluster.resourcesVpcConfig.vpcId' "$AWS_DIR/eks_describe_cluster.json")
AWS=(aws --region "$REGION" --output json)

echo "== VPC $VPC_ID"
"${AWS[@]}" ec2 describe-vpcs --vpc-ids "$VPC_ID" > "$AWS_DIR/ec2_describe_vpcs.json"
"${AWS[@]}" ec2 describe-subnets --filters "Name=vpc-id,Values=$VPC_ID" > "$AWS_DIR/ec2_describe_subnets.json"
"${AWS[@]}" ec2 describe-route-tables --filters "Name=vpc-id,Values=$VPC_ID" > "$AWS_DIR/ec2_describe_route_tables.json"
"${AWS[@]}" ec2 describe-nat-gateways --filter "Name=vpc-id,Values=$VPC_ID" > "$AWS_DIR/ec2_describe_nat_gateways.json"
"${AWS[@]}" ec2 describe-vpc-endpoints --filters "Name=vpc-id,Values=$VPC_ID" > "$AWS_DIR/ec2_describe_vpc_endpoints.json"
"${AWS[@]}" ec2 describe-transit-gateway-vpc-attachments --filters "Name=vpc-id,Values=$VPC_ID" \
  > "$AWS_DIR/ec2_describe_transit_gateway_vpc_attachments.json"

echo "== Kubernetes $NS/$DEPLOY"
kubectl get deployment "$DEPLOY" -n "$NS" -o json | jq "$STRIP" > "$K8S_DIR/deployment.json"
SA=$(jq -r '.spec.template.spec.serviceAccountName // "default"' "$K8S_DIR/deployment.json")
kubectl get serviceaccount "$SA" -n "$NS" -o json | jq "$STRIP" > "$K8S_DIR/serviceaccount.json"
kubectl get services -n "$NS" -o json | jq "$STRIP" > "$K8S_DIR/services.json"
kubectl get ingresses -n "$NS" -o json | jq "$STRIP" > "$K8S_DIR/ingresses.json"

HOSTS_JSON=$(jq -s '[.[].items[].status.loadBalancer.ingress[]?.hostname // empty | ascii_downcase] | unique' \
  "$K8S_DIR/ingresses.json" "$K8S_DIR/services.json")
echo "Load balancer hostnames in namespace: $(jq -r 'join(", ")' <<<"$HOSTS_JSON")"

echo "== Load balancers"
"${AWS[@]}" elbv2 describe-load-balancers \
  | jq --argjson hosts "$HOSTS_JSON" \
      '{LoadBalancers: [.LoadBalancers[] | select((.DNSName | ascii_downcase) as $d | $hosts | index($d))]}' \
  > "$AWS_DIR/elbv2_describe_load_balancers.json"

jq -r '.LoadBalancers[] | [.LoadBalancerArn, .LoadBalancerName, .Type] | @tsv' \
  "$AWS_DIR/elbv2_describe_load_balancers.json" |
while IFS=$'\t' read -r LB_ARN LB_NAME LB_TYPE; do
  name=$(safe_name "$LB_NAME")
  "${AWS[@]}" elbv2 describe-listeners --load-balancer-arn "$LB_ARN" > "$AWS_DIR/elbv2_describe_listeners_$name.json"
  if [[ "$LB_TYPE" == "application" ]]; then
    "${AWS[@]}" wafv2 get-web-acl-for-resource --resource-arn "$LB_ARN" > "$AWS_DIR/wafv2_get_web_acl_for_resource_$name.json"
  fi
done

echo "== CloudFront"
aws cloudfront list-distributions --output json \
  | jq --argjson hosts "$HOSTS_JSON" \
      '{DistributionList: {Items: [(.DistributionList.Items // [])[]
         | select([.Origins.Items[].DomainName | ascii_downcase] | any(. as $o | $hosts | index($o)))]}}' \
  > "$AWS_DIR/cloudfront_list_distributions.json"

echo "== Workload identity (service account $SA)"
"${AWS[@]}" eks list-pod-identity-associations --cluster-name "$CLUSTER" --namespace "$NS" --service-account "$SA" \
  > "$AWS_DIR/eks_list_pod_identity_associations.json"
ASSOC_ID=$(jq -r '.associations[0].associationId // empty' "$AWS_DIR/eks_list_pod_identity_associations.json")
ROLE_ARN=""
if [[ -n "$ASSOC_ID" ]]; then
  "${AWS[@]}" eks describe-pod-identity-association --cluster-name "$CLUSTER" --association-id "$ASSOC_ID" \
    > "$AWS_DIR/eks_describe_pod_identity_association.json"
  ROLE_ARN=$(jq -r '.association.roleArn' "$AWS_DIR/eks_describe_pod_identity_association.json")
else
  ROLE_ARN=$(jq -r '.metadata.annotations["eks.amazonaws.com/role-arn"] // empty' "$K8S_DIR/serviceaccount.json")
fi

if [[ -n "$ROLE_ARN" ]]; then
  ROLE_NAME=${ROLE_ARN##*/}
  echo "== IAM role $ROLE_NAME"
  aws iam list-attached-role-policies --role-name "$ROLE_NAME" --output json > "$AWS_DIR/iam_list_attached_role_policies.json"
  jq -r '.AttachedPolicies[] | [.PolicyArn, .PolicyName] | @tsv' "$AWS_DIR/iam_list_attached_role_policies.json" |
  while IFS=$'\t' read -r POLICY_ARN POLICY_NAME; do
    name=$(safe_name "$POLICY_NAME")
    aws iam get-policy --policy-arn "$POLICY_ARN" --output json > "$AWS_DIR/iam_get_policy_$name.json"
    VERSION=$(jq -r '.Policy.DefaultVersionId' "$AWS_DIR/iam_get_policy_$name.json")
    aws iam get-policy-version --policy-arn "$POLICY_ARN" --version-id "$VERSION" --output json \
      > "$AWS_DIR/iam_get_policy_version_$name.json"
  done
  aws iam list-role-policies --role-name "$ROLE_NAME" --output json > "$AWS_DIR/iam_list_role_policies.json"
  jq -r '.PolicyNames[]' "$AWS_DIR/iam_list_role_policies.json" |
  while read -r POLICY_NAME; do
    aws iam get-role-policy --role-name "$ROLE_NAME" --policy-name "$POLICY_NAME" --output json \
      > "$AWS_DIR/iam_get_role_policy_$(safe_name "$POLICY_NAME").json"
  done
else
  echo "No Pod Identity or IRSA role found for $SA"
fi

echo "== Secret check"
for f in "$K8S_DIR"/*.json; do
  if [[ "$(jq "$LEAK_CHECK" "$f")" != "0" ]] || grep -q 'last-applied-configuration' "$f"; then
    rm -f "$f"
    echo "Deleted $f: it still contained env vars or last-applied-configuration. Check the jq filter." >&2
    exit 1
  fi
done
echo "OK. Files written:"
ls -1 "$AWS_DIR" "$K8S_DIR"
