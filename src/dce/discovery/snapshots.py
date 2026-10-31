from typing import Any

from dce.common.errors import DceError, ErrorCode


def compare_services(current: list[dict[str, Any]], saved: list[dict[str, Any]]) -> dict[str, Any]:
    def indexed(items: list[dict[str, Any]]) -> dict[str, Any]:
        result = {str(item["name"]): item.get("image") for item in items}
        if len(result) != len(items):
            raise DceError(ErrorCode.SNAPSHOT_CONFLICT, "Duplicate service names in snapshot.")
        return result

    left, right = indexed(current), indexed(saved)
    added, removed = sorted(left.keys() - right.keys()), sorted(right.keys() - left.keys())
    changed = sorted(name for name in left.keys() & right.keys() if left[name] != right[name])
    return {
        "status": "config_drift_candidate" if added or removed or changed else "declarations_equal",
        "added": added,
        "removed": removed,
        "changed_images": changed,
        "version_match": "not_verified",
    }


def stack_runtime(
    stack: dict[str, Any], endpoint: dict[str, Any], services: list[dict[str, Any]]
) -> dict[str, Any]:
    stack_swarm = stack.get("swarm_id", stack.get("SwarmId"))
    current_swarm = endpoint.get("current_swarm_id")
    if not current_swarm:
        current_swarm = endpoint.get("Swarm", {}).get("Cluster", {}).get("ID")
    endpoint_id = str(endpoint.get("id", endpoint.get("Id", "")))
    stack_endpoint = str(stack.get("endpoint_id", stack.get("EndpointId", "")))
    if (
        stack.get("Type", 1) != 1
        or not current_swarm
        or stack_swarm != current_swarm
        or not stack_endpoint
        or stack_endpoint != endpoint_id
    ):
        return {
            "status": "stale_candidate",
            "services": [],
            "environment": "unresolved",
            "health": "unknown",
            "reason": "Endpoint or Swarm identity mismatch/unverified",
        }
    namespace = stack.get("namespace", stack.get("Namespace")) or stack.get(
        "name", stack.get("Name")
    )
    selected = []
    for service in services:
        labels = service.get("Spec", {}).get("Labels", {})
        observed_namespace = service.get("namespace", labels.get("com.docker.stack.namespace"))
        if namespace and observed_namespace == namespace:
            selected.append(service)
    return {
        "status": "observed_verified",
        "services": selected,
        "namespace": namespace,
        "namespace_evidence": "service_labels",
        "environment": "unresolved",
        "health": "unknown",
    }
