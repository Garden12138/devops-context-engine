import asyncio
from pathlib import Path

import pytest
from test_catalog import sample

from dce.ai.provider import FakeProvider
from dce.app.mapping import MappingService
from dce.catalog.db import Catalog
from dce.common.errors import DceError
from dce.discovery.fixture import discover_fixture
from dce.graph.model import Entity


def test_offline_rules_and_ambiguous_business_candidates(tmp_path: Path) -> None:
    result = discover_fixture(Path("fixtures/synthetic-discovery.json"))
    with Catalog(tmp_path / "catalog.sqlite3") as catalog:
        catalog.import_scan(result, scope="fixture")
        service = MappingService(catalog)
        report = asyncio.run(service.suggest())
        assert report["ai_status"] == "disabled"
        semantic = [
            e for e in catalog.list_edges(limit=100)["items"] if e["relation"] == "implements"
        ]
        # Query by status to avoid dependence on mixed technical graph pagination.
        candidates = catalog.list_edges(status="unresolved", limit=100)["items"]
        candidates += catalog.list_edges(status="candidate", limit=100)["items"]
        semantic += [e for e in candidates if e["relation"] == "implements"]
        assert {e["status"] for e in semantic} <= {"candidate", "unresolved"}
        assert len({e["target_id"] for e in semantic}) == 3
        count = catalog.counts()
        asyncio.run(service.suggest())
        assert catalog.counts() == count
        assert len([e for e in catalog.read_graph().edges if e.relation == "declares_image"]) == 78


def test_ai_candidate_schema_and_minimal_input(tmp_path: Path) -> None:
    result = sample()
    result.entities[0].attributes["name"] = "https://private.example.invalid Token=synthetic-secret"
    source, target = result.entities
    payload = {
        "candidates": [
            {
                "source_id": source.id,
                "target_id": target.id,
                "relation": "related_to",
                "evidence_ids": [result.evidence[0].id],
                "confidence": 0.95,
                "rationale": "Metadata is ambiguous.",
            }
        ]
    }
    provider = FakeProvider(payload)
    with Catalog(tmp_path / "catalog.sqlite3") as catalog:
        catalog.import_scan(result, scope="demo")
        report = asyncio.run(MappingService(catalog, provider=provider).suggest())
        assert report["ai_status"] == "ok"
        text = str(provider.received)
        assert all(
            word not in text for word in ("private.example", "synthetic-secret", "Token", "https")
        )
        ai = next(
            e
            for e in catalog.list_edges(status="candidate")["items"]
            if e["relation"] == "related_to"
        )
        assert ai["confidence"] <= 0.79
        assert ai["status"] == "candidate"


@pytest.mark.parametrize(
    "mode", ["timeout", "invalid", "confirmed", "unknown_reference", "failure"]
)
def test_ai_failure_preserves_rules(tmp_path: Path, mode: str) -> None:
    result = sample()
    payload = {
        "candidates": [
            {
                "source_id": result.entities[0].id,
                "target_id": result.entities[1].id,
                "relation": "related_to",
                "evidence_ids": [result.evidence[0].id],
                "confidence": 0.9,
                "rationale": "candidate",
                "status": "candidate",
            }
        ]
    }
    if mode == "confirmed":
        payload["candidates"][0]["status"] = "confirmed"
    if mode == "unknown_reference":
        payload["candidates"][0]["evidence_ids"] = ["unknown"]
    provider = FakeProvider(
        "invalid-json" if mode == "invalid" else payload,
        delay=0.1 if mode == "timeout" else 0,
        fail=mode == "failure",
    )
    with Catalog(tmp_path / "catalog.sqlite3") as catalog:
        catalog.import_scan(result, scope="demo")
        report = asyncio.run(MappingService(catalog, provider=provider, timeout=0.01).suggest())
        assert report["ai_status"] in {"timeout", "invalid_response", "failed"}
        assert not catalog.list_edges(status="confirmed")["items"]
        assert catalog.edge(result.edges[0].id)["status"] == "candidate"


def test_review_versions_evidence_and_environment_ack(tmp_path: Path) -> None:
    result = sample()
    environment = Entity(source_instance="local", kind="environment", external_id="demo-env")
    result.entities.append(environment)
    result.edges[0].target_id = environment.id
    result.edges[0].relation = "deployed_in"
    edge_id = result.edges[0].id
    with Catalog(tmp_path / "catalog.sqlite3") as catalog:
        catalog.import_scan(result, scope="demo")
        service = MappingService(catalog)
        preview = service.preview(edge_id)
        assert preview["environment_confirmation_required"]
        assert preview["evidence"]
        assert preview["impact"]["source_id"] == result.entities[0].id
        with pytest.raises(DceError):
            service.review(
                edge_id, action="accept", actor="owner", reason="proof", expected_version=1
            )
        service.review(
            edge_id,
            action="accept",
            actor="owner",
            reason="proof",
            expected_version=1,
            confirm_environment=True,
        )
        assert catalog.edge(edge_id)["status"] == "confirmed"
        with pytest.raises(DceError):
            service.review(
                edge_id, action="reject", actor="owner", reason="stale preview", expected_version=1
            )
        service.review(
            edge_id, action="revoke", actor="owner", reason="withdraw", expected_version=2
        )
        assert catalog.edge(edge_id)["status"] == "candidate"
