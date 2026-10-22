# Network diagram — guide for tech leads

The architecture review needs a network diagram for your app once it is running in staging. Most of it is generated from AWS and Kubernetes. You only fill in what those cannot show.

## What to do
1. Copy `templates/declared.template.yaml` to `declared.yaml`.
2. Fill in the header: deployment, namespace, cluster, owner team, your email.
3. Under `dependencies`, list:
   - Databases and caches your app connects to with a password (RDS, ElastiCache, etc.).
   - External services it calls, by hostname (vendor APIs, SaaS).
   - On-prem systems it calls.
   - Other internal apps it calls outside the cluster.
4. For AWS services your app calls with its IAM role (S3, Secrets Manager, SQS, etc.), add only `name` and `purpose`. Everything else is extracted. Use the same name as in the generated flow table.
5. Under `prod_differences`, write anything that will differ in prod: account, WAF mode, egress, extra dependencies. Write "None" if nothing differs.
6. Check the file: `netdiag validate declared.yaml`.

## Allowed values
| Field | Values |
|---|---|
| `type` | `data-store`, `external`, `on-prem`, `internal-app` |
| `protocol` | `https`, `http`, `grpc`, `postgres`, `mysql`, `redis`, `kafka`, `tcp` |
| `auth` | `password`, `iam`, `mtls`, `api-key`, `oauth`, `none` |

`service` is required for `data-store` (for example `rds-postgres`, `elasticache-redis`).

## Rules
- Give every dependency a `purpose` in one short sentence.
- Use hostnames, not IP addresses.
- Do not put passwords, keys or tokens in this file.
