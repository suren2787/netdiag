"""Kubernetes extractor (session 6, /build-k8s-extractor).

Lookup chain steps 1-3 in .claude/rules/extract.md:
  Deployment -> service account and pod labels -> Services -> Ingresses -> load balancer hostname

API objects are passed in (kubernetes.client.AppsV1Api, CoreV1Api, NetworkingV1Api).
Never read Secrets or ConfigMaps.
"""
from __future__ import annotations

from typing import Any


def get_deployment(apps_api: Any, namespace: str, name: str) -> dict[str, Any]:
    """Read the Deployment and return it stripped.

    Keep only: name, namespace, selector matchLabels, pod template labels,
    serviceAccountName (default "default"), container names and ports.
    Drop env, envFrom, args, command, volumes and all annotations.
    """
    raise NotImplementedError("Session 6: /build-k8s-extractor")


def get_service_account(core_api: Any, namespace: str, name: str) -> dict[str, Any]:
    """Return {"name": ..., "irsa_role_arn": <eks.amazonaws.com/role-arn annotation or None>}."""
    raise NotImplementedError("Session 6: /build-k8s-extractor")


def find_services(core_api: Any, namespace: str, pod_labels: dict[str, str]) -> list[dict[str, Any]]:
    """Services in the namespace whose spec.selector is a non-empty subset of pod_labels.

    Return name, type, ports, and status.loadBalancer.ingress[].hostname for type LoadBalancer.
    """
    raise NotImplementedError("Session 6: /build-k8s-extractor")


def find_ingresses(networking_api: Any, namespace: str, service_names: set[str]) -> list[dict[str, Any]]:
    """Ingresses in the namespace with a backend pointing at one of service_names.

    Return for each: name, hosts (spec.rules[].host), backend service and port,
    and load balancer hostnames (status.loadBalancer.ingress[].hostname).
    """
    raise NotImplementedError("Session 6: /build-k8s-extractor")
