import asyncio
from pathlib import Path

from dce.ai.provider import FakeProvider
from dce.app.mapping import MappingService
from dce.catalog.db import Catalog
from dce.graph.model import DiscoveryResult, Edge, Entity, Evidence, Snapshot
from dce.graph.rules import suggestions


def graph() -> DiscoveryResult:
    business = Entity(
        source_instance="zen", kind="business_project", external_id="1", attributes={"name": "api"}
    )
    repo = Entity(source_instance="git", kind="repository", external_id="1")
    snapshot = Snapshot(
        source_instance="git", resource_key=repo.id, kind="repository", version="v1"
    )
    evidence = Evidence(
        source_instance="git",
        snapshot_id=snapshot.id,
        locator="pom.xml",
        version="v1",
        summary="modules",
    )
    result = DiscoveryResult(entities=[business, repo], snapshots=[snapshot], evidence=[evidence])
    for n in range(51):
        module = Entity(
            source_instance="git", kind="module", external_id=str(n), attributes={"path": f"api{n}"}
        )
        result.entities.append(module)
        result.edges.append(
            Edge(
                source_id=repo.id,
                target_id=module.id,
                relation="contains_module",
                status="observed_verified",
                evidence_ids=[evidence.id],
            )
        )
    return result


def test_rule_candidate_limit_and_missing_evidence() -> None:
    result = graph()
    assert len(suggestions(result).edges) == 50
    assert "CANDIDATE_LIMIT_REACHED" in suggestions(result).warnings
    result.evidence = []
    assert suggestions(result).edges == []


def test_ai_and_rule_same_edge_remain_idempotent(tmp_path: Path) -> None:
    result = graph()
    candidate = suggestions(result).edges[0]
    provider = FakeProvider(
        {
            "candidates": [
                {
                    "source_id": candidate.source_id,
                    "target_id": candidate.target_id,
                    "relation": candidate.relation,
                    "evidence_ids": [result.evidence[0].id],
                    "confidence": 0.75,
                    "rationale": "Ambiguous metadata association",
                }
            ]
        }
    )
    with Catalog(tmp_path / "catalog.sqlite3") as catalog:
        catalog.import_scan(result, scope="demo")
        service = MappingService(catalog, provider=provider)
        asyncio.run(service.suggest())
        version = catalog.edge(candidate.id)["version"]
        asyncio.run(service.suggest())
        assert catalog.edge(candidate.id)["version"] == version
        assert catalog.edge(candidate.id)["status"] == "candidate"
