import json
from pathlib import Path

import pytest

from dce.common.errors import DceError
from dce.discovery.fixture import discover_fixture
from dce.discovery.snapshots import compare_services, stack_runtime
from dce.graph.model import identity

FIXTURE = Path("fixtures/synthetic-discovery.json")


def test_synthetic_discovery_acceptance() -> None:
    result = discover_fixture(FIXTURE)
    services = [e for e in result.entities if e.kind == "service"]
    images = [e for e in result.entities if e.kind == "image"]
    stacks = [e for e in result.entities if e.kind == "stack"]
    assert len(services) == 78
    assert len(images) == 73
    assert len(stacks) == 3
    assert len([e for e in result.entities if e.kind == "swarm"]) == 1
    assert len([e for e in stacks if e.attributes["state"] == "stale_candidate"]) == 2
    assert all(e.attributes["environment"] == "unresolved" for e in stacks)
    assert len([e for e in result.entities if e.kind == "module"]) == 3
    assert {e.attributes["role"] for e in result.entities if e.kind == "repository"} == {
        "source",
        "deployment",
    }
    drift = next(a for a in result.anomalies if a["status"] == "config_drift_candidate")
    assert drift["added"] == [f"demo-svc-{n:03}" for n in range(72, 79)]
    assert drift["removed"] == drift["changed_images"] == []
    assert {s.kind for s in result.snapshots} >= {"git_current", "portainer_saved", "swarm_runtime"}
    counts = {}
    for edge in result.edges:
        if edge.relation == "observes_image_reference":
            counts[edge.target_id] = counts.get(edge.target_id, 0) + 1
    assert len([n for n in counts.values() if n == 2]) == 5
    assert all(e.attributes["mutable_tag"] for e in images)
    evidence = {e.id for e in result.evidence}
    assert all(set(edge.evidence_ids) <= evidence for edge in result.edges)
    assert not any(edge.status == "confirmed" for edge in result.edges)
    assert {e.id for e in discover_fixture(FIXTURE).entities} == {e.id for e in result.entities}
    assert {s.id for s in discover_fixture(FIXTURE).snapshots} == {s.id for s in result.snapshots}


def test_composite_identity_isolation() -> None:
    keys = {
        identity("zen", "project", "1"),
        identity("git", "project", "1"),
        identity("port", "stack", "1"),
        identity("git2", "project", "1"),
    }
    assert len(keys) == 4
    assert identity("a:b", "c", "d") != identity("a", "b:c", "d")


def test_stack_empty_namespace_and_mismatch() -> None:
    endpoint = {"Id": 1, "Swarm": {"Cluster": {"ID": "current"}}}
    stack = {"Id": 3, "Name": "demo", "Namespace": "", "EndpointId": 1, "SwarmId": "current"}
    services = [
        {"Spec": {"Labels": {"com.docker.stack.namespace": "demo"}}},
        {"Spec": {"Labels": {"com.docker.stack.namespace": "infra"}}},
    ]
    assert len(stack_runtime(stack, endpoint, services)["services"]) == 1
    assert (
        stack_runtime({**stack, "SwarmId": "old"}, endpoint, services)["status"]
        == "stale_candidate"
    )
    assert (
        stack_runtime({**stack, "EndpointId": 2}, endpoint, services)["status"] == "stale_candidate"
    )
    assert (
        stack_runtime({**stack, "EndpointId": ""}, endpoint, services)["status"]
        == "stale_candidate"
    )
    assert stack_runtime(stack, {}, services)["status"] == "stale_candidate"
    assert stack_runtime({**stack, "Type": 2}, endpoint, services)["status"] == "stale_candidate"
    assert stack_runtime(stack, endpoint, [])["status"] == "stale_candidate"


def test_snapshot_diff() -> None:
    diff = compare_services(
        [{"name": "a", "image": "one"}, {"name": "b", "image": "two"}],
        [{"name": "b", "image": "old"}, {"name": "c", "image": "three"}],
    )
    assert diff["added"] == ["a"]
    assert diff["removed"] == ["c"]
    assert diff["changed_images"] == ["b"]
    assert compare_services([], [])["version_match"] == "not_verified"
    with pytest.raises(DceError):
        compare_services([{"name": "same"}, {"name": "same"}], [])


def test_bad_fixture_rejected(tmp_path: Path) -> None:
    path = tmp_path / "fixture.json"
    for value in ({"synthetic": False}, {"synthetic": True}, []):
        path.write_text(json.dumps(value))
        with pytest.raises(DceError):
            discover_fixture(path)
    with pytest.raises(DceError):
        discover_fixture(tmp_path / "missing.json")
