from pathlib import Path

import pytest
from sqlalchemy import select

from dce.catalog.db import Catalog
from dce.catalog.schema import entity_history, scans
from dce.common.errors import DceError
from dce.discovery.fixture import discover_fixture
from dce.graph.model import DiscoveryResult, Edge, Entity, Evidence, Snapshot


def sample() -> DiscoveryResult:
    a = Entity(
        source_instance="zen", kind="business_project", external_id="1", attributes={"name": "demo"}
    )
    b = Entity(source_instance="git", kind="module", external_id="1", attributes={"path": "api"})
    snapshot = Snapshot(source_instance="zen", resource_key=a.id, kind="business", version="v1")
    evidence = Evidence(
        source_instance="zen",
        snapshot_id=snapshot.id,
        locator="project/1",
        version="v1",
        summary="synthetic candidate",
    )
    edge = Edge(
        source_id=a.id,
        target_id=b.id,
        relation="implements",
        status="candidate",
        confidence=0.5,
        evidence_ids=[evidence.id],
    )
    return DiscoveryResult(entities=[a, b], snapshots=[snapshot], evidence=[evidence], edges=[edge])


def test_catalog_fixture_idempotency_and_trace(tmp_path: Path) -> None:
    result = discover_fixture(Path("fixtures/synthetic-discovery.json"))
    with Catalog(tmp_path / "catalog.sqlite3") as catalog:
        catalog.import_scan(result, scope="fixture-demo")
        counts = catalog.counts()
        catalog.import_scan(result, scope="fixture-demo")
        assert catalog.counts() == counts
        assert len(catalog.list_entities(kind="service", limit=100)["items"]) == 78
        assert catalog.list_entities(kind="service", limit=20)["more_available"]
        assert len(catalog.list_entities(kind="service", limit=20, offset=60)["items"]) == 18
        service = next(e for e in result.entities if e.kind == "service")
        forward = catalog.trace(service.id, direction="out", max_depth=2)
        reverse = catalog.trace(service.id, direction="in", max_depth=2)
        assert any(e["relation"] == "observes_image_reference" for e in forward["edges"])
        assert any(e["relation"] == "runs_service" for e in reverse["edges"])
        assert catalog.trace(service.id, direction="both", limit=1)["more_available"]
        assert len(catalog.history(service.id)) == 1
        assert len(catalog.scan_status()["items"]) == 2


def test_versions_review_protection_and_revoke(tmp_path: Path) -> None:
    result = sample()
    edge = result.edges[0]
    with Catalog(tmp_path / "catalog.sqlite3") as catalog:
        catalog.import_scan(result, scope="demo")
        catalog.review(edge.id, action="accept", actor="human:test", reason="verified by owner")
        assert catalog.edge(edge.id)["status"] == "confirmed"
        result.entities[0].attributes["name"] = "updated"
        result.edges[0].confidence = 0.2
        catalog.import_scan(result, scope="demo")
        assert len(catalog.history(result.entities[0].id)) == 2
        assert catalog.edge(edge.id)["status"] == "confirmed"
        assert catalog.edge(edge.id)["conflict"]
        assert len(catalog.reviews(edge.id)) == 1
        catalog.review(
            edge.id, action="revoke", actor="human:test", reason="evidence no longer valid"
        )
        assert catalog.edge(edge.id)["status"] == "candidate"
        assert len(catalog.reviews(edge.id)) == 2
        assert catalog.audit(edge.id)[-1]["event"] == "review_revoke"


def test_scope_disappearance_retains_audit(tmp_path: Path) -> None:
    result = sample()
    with Catalog(tmp_path / "catalog.sqlite3") as catalog:
        catalog.import_scan(result, scope="one")
        catalog.import_scan(result, scope="two")
        catalog.review(result.edges[0].id, action="accept", actor="human:test", reason="verified")
        catalog.import_scan(DiscoveryResult(), scope="one")
        assert not catalog.get_entity(result.entities[0].id)["deleted"]
        catalog.import_scan(DiscoveryResult(), scope="two", complete=False)
        assert not catalog.get_entity(result.entities[0].id)["deleted"]
        catalog.import_scan(DiscoveryResult(), scope="two")
        assert catalog.get_entity(result.entities[0].id)["deleted"]
        stored = catalog.edge(result.edges[0].id)
        assert stored["status"] == "confirmed" and stored["stale"]
        assert catalog.reviews(result.edges[0].id)
        assert catalog.list_entities()["items"] == []
        catalog.import_scan(result, scope="two")
        assert not catalog.get_entity(result.entities[0].id)["deleted"]


def test_invalid_batch_rolls_back_and_records_failed_scan(tmp_path: Path) -> None:
    result = sample()
    result.edges[0].target_id = "nonexistent"
    with Catalog(tmp_path / "catalog.sqlite3") as catalog:
        with pytest.raises(DceError):
            catalog.import_scan(result, scope="invalid")
        assert catalog.counts()["entities"] == 0
        assert catalog.counts()["snapshots"] == 0
        with catalog.engine.connect() as connection:
            assert connection.execute(select(scans.c.status)).scalar() == "failed"


def test_queries_and_review_validation(tmp_path: Path) -> None:
    with Catalog(tmp_path / "catalog.sqlite3") as catalog:
        result = sample()
        catalog.import_scan(result, scope="demo")
        for operation in (
            lambda: catalog.list_entities(limit=101),
            lambda: catalog.trace(result.entities[0].id, direction="bad"),
            lambda: catalog.trace(result.entities[0].id, max_depth=20),
            lambda: catalog.get_entity("absent"),
            lambda: catalog.edge("absent"),
            lambda: catalog.review(result.edges[0].id, action="accept", actor="", reason=""),
        ):
            with pytest.raises(DceError):
                operation()
        catalog.review(
            result.edges[0].id, action="reject", actor="human:test", reason="wrong module"
        )
        assert catalog.edge(result.edges[0].id)["status"] == "rejected"
        catalog.import_scan(result, scope="demo")
        assert catalog.edge(result.edges[0].id)["status"] == "rejected"


def test_alembic_upgrade_backfills_history(tmp_path: Path) -> None:
    path = tmp_path / "catalog.sqlite3"
    with Catalog(path, revision="0001") as catalog:
        from dce.catalog.schema import edges, entities

        with catalog.engine.begin() as connection:
            connection.execute(
                entities.insert().values(
                    id="legacy",
                    source_instance="git",
                    kind="repo",
                    external_id="1",
                    attributes={"name": "legacy"},
                    version=1,
                    deleted=False,
                    first_seen="synthetic-time",
                    last_verified="synthetic-time",
                )
            )
            connection.execute(
                edges.insert().values(
                    id="legacy-edge",
                    source_id="legacy",
                    target_id="legacy",
                    relation="legacy_relation",
                    observed_status="candidate",
                    status="candidate",
                    evidence_ids=[],
                    confidence=0.1,
                    version=1,
                    conflict=False,
                    stale=False,
                    deleted=False,
                    valid_from="synthetic-time",
                    last_verified="synthetic-time",
                )
            )
        catalog.migrate()
        assert len(catalog.history("legacy")) == 1
        assert len(catalog.edge_versions("legacy-edge")) == 1
        catalog.migrate()
        with catalog.engine.connect() as connection:
            assert len(connection.execute(select(entity_history)).all()) == 1
