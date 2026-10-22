# netdiag — design (phase 1)

## Goal
One command produces the network diagram and flow table for one app running on EKS in staging:

```
netdiag run --cluster <name> --namespace <ns> --deployment <name> --declared declared.yaml --out out/<app>
```

Outputs in `--out`:

| File | What it is |
|---|---|
| `extracted.yaml` | Everything read from AWS and Kubernetes |
| `network.yaml` | Extracted + declared, merged. Same shape as `templates/network.template.yaml` |
| `network.d2`, `network.svg` | The diagram |
| `flows.md` | The flow table, warnings and prod differences |

## Scope
Phase 1: outside the cluster only. Phase 2 (inside the cluster) is a separate piece of work.

## Sources

| Source | What it gives |
|---|---|
| Kubernetes API | Deployment → service account, pod labels → Services → Ingresses → load balancer hostname |
| AWS APIs | Cluster networking, load balancer, WAF, CloudFront, IAM role and its permissions |
| `declared.yaml` (tech lead) | Data stores reached with a password, external FQDNs, on-prem systems, purpose of each dependency, prod differences |

The API call and response field for every extracted value is written next to the field in `templates/network.template.yaml`.

## Derivation rules
Implemented in `src/netdiag/derive.py`.

| Field | Rule |
|---|---|
| `subnet.default_route` | Target of the `0.0.0.0/0` route in the subnet's route table. A subnet with no explicit association uses the VPC main route table. |
| `subnet.tier` | `igw-*` → public. `nat-*` or `tgw-*` → private. No default route → isolated. Anything else → private, plus a warning. |
| `subnet.cluster_subnet` | True if the subnet ID is in the cluster's `resourcesVpcConfig.subnetIds`. |
| `workload.identity` | Pod Identity association found → `pod-identity`. Else IRSA annotation found → `irsa`. Else `node-role`, plus a warning. |
| `dependency` (aws-service) | `port: 443`, `protocol: https`, `tls: true`, `auth: iam`. |
| `dependency.path` | aws-service: `vpc-endpoint` if a VPC endpoint exists for the service, else the egress route. data-store: `in-vpc`. on-prem: `tgw`. external and internal-app: the egress route. |
| Egress route | Default route of the cluster subnets: `nat-*` → `nat`, `tgw-*` → `tgw`, none → `none`. If cluster subnets disagree, use `mixed` and add a warning. |
| IDs | Ingress entries `I1..In`, dependencies `D1..Dn`, numbered after sorting by name. |

### Warnings
Add a warning (do not fail) when:
- An IAM policy statement has `Resource: "*"`.
- An HTTP listener does not redirect to HTTPS.
- An internet-facing load balancer has no WAF and no CloudFront with WAF.
- The EKS API endpoint is public with `0.0.0.0/0` in `publicAccessCidrs`.
- A value could not be determined.

## Merge rules
Implemented in `src/netdiag/merge.py`.

1. Start from `extracted.yaml`.
2. Copy `owner_team`, `tech_lead` and `prod_differences` from `declared.yaml`.
3. For each declared dependency, match on `name`:
   - Entry has only `name` and `purpose`: set `purpose` on the extracted dependency with that name. If no extracted dependency has that name, add a warning.
   - Full entry with a name that is not extracted: add it as a dependency with `source: declared`.
   - Full entry with a name that is already extracted: keep the extracted values, take `purpose` from the declared entry, add a warning that the declared values were ignored.
4. Any extracted dependency left without a `purpose`: add a warning.
5. Apply the derivation rules for `path` and IDs after merging.
6. Sort all lists. Set `generated_at`.

## Access
- One read-only IAM role in the staging account.
- That role has an EKS access entry with `AmazonEKSViewPolicy`. This policy excludes Secrets.
- The tool uses the default credential chain (`AWS_PROFILE`) and the current kubeconfig context.

## Known gaps (phase 1)
- Data stores reached with a password are not linked to the app in any API. The tech lead declares them.
- IAM policies with `Resource: "*"` show the service but not the resource.
- Who calls the EKS API (CI runners, admins) is not shown.
- The diagram shows staging. Prod differences are declared, not verified.
