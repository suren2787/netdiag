---
paths:
  - "src/netdiag/render/**"
  - "tests/test_d2.py"
  - "tests/test_table.py"
---
# Renderer rules

Input is always a `network.yaml` dict. Renderers never call APIs and never read `extracted.yaml` or `declared.yaml` directly.

## Diagram layout (D2)
Fixed placement. Do not let the layout engine decide where the main zones go.

- Top row, left to right: `Internet`, `CloudFront + WAF` (only if present), `On-prem` (only if an on-prem dependency exists).
- Middle: the VPC container. Inside it, a `subnets` container with `grid-columns` = number of AZs used by cluster or load balancer subnets, and rows in this order: `public`, `private`, `isolated`. In D2 every child of a grid container becomes a cell, so put only subnet boxes inside `subnets`.
- One box per tier per AZ. Merge subnets of the same tier in the same AZ into one box, listing their CIDRs in the label. Do not draw one box per subnet.
- Mark cluster subnets with the label `EKS nodes`.
- Load balancers sit in the subnet tier they are deployed in.
- Egress (NAT, Transit Gateway attachment) and VPC endpoints sit at the VPC edge, outside the `subnets` container.
- Dependencies sit outside the VPC, grouped by type: `aws-service`, `external`, `on-prem`, `internal-app`. Dependencies with path `in-vpc` (data stores) go inside the VPC container, next to `subnets`, in one `Data stores` box.

## Edges
- Label each edge only with its ID (`I1`, `D2`). Ports, protocols and auth go in the flow table, not on the diagram.
- One edge per ingress and per dependency. No other edges.

## Style
- One D2 theme. Two fill colours: one for AWS-managed network controls (WAF, CloudFront, NAT, Transit Gateway, endpoints), one neutral for everything else.
- Short labels: name on line 1, one detail on line 2.

## Flow table (markdown)
- One row per ingress and per dependency, in ID order.
- Columns: ID, From, To, Port, Protocol, TLS, Auth, Path, Purpose, Source.
- After the table, list `warnings` and `prod_differences`.

## Check
The number of edges in the D2 output must equal the number of rows in the flow table. Write a test for this.
