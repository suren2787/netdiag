"""Merge extracted and declared data (session 9, /build-merge-cli).

Rules: "Merge rules" in docs/design.md. Pure function, no I/O.
"""
from __future__ import annotations

from typing import Any


def merge(extracted: dict[str, Any], declared: dict[str, Any]) -> dict[str, Any]:
    """Return network.yaml content in the shape of templates/network.template.yaml."""
    raise NotImplementedError("Session 9: /build-merge-cli")
