---
name: build-renderer
description: Sessions 3-4. Render network.yaml to D2, SVG and a markdown flow table.
disable-model-invocation: true
---
Build the renderer in `src/netdiag/render/`.

Read first:
- `templates/network.template.yaml` (the input)
- `.claude/rules/render.md` (layout rules)
- `docs/design.md`

Do one step at a time. Run `pytest` after each step and stop for my review.

1. `render/table.py`: implement `render_flow_table(network: dict) -> str`. Add `tests/test_table.py`.
2. `render/d2.py`: implement `render_d2(network: dict) -> str`. Follow the layout rules exactly. Add `tests/test_d2.py`, including the check that edge count equals flow table row count.
3. In `cli.py`, implement the `render` command: read a `network.yaml`, write `<out>/network.d2` and `<out>/flows.md`, then run `d2 <out>/network.d2 <out>/network.svg`.
4. Run `netdiag render templates/network.template.yaml --out out/template` and show me the result.

Use `templates/network.template.yaml` as the test input. Do not touch the extractors.

Gate: if the diagram is still cluttered after two rounds of layout changes, stop and tell me. We will switch to a fixed SVG template instead of D2.
