import asyncio
from pathlib import Path

import pytest
from test_catalog import sample

from dce.ai.provider import FakeProvider, NoopProvider
from dce.app.mapping import MappingService
from dce.catalog.db import Catalog
from dce.common.errors import DceError
from dce.discovery.fixture import discover_fixture
from dce.graph.model import Edge, Entity


def test_explicit_modules_to_shared_build_image(tmp_path: Path) -> None:
    result = discover_fixture(Path("fixtures/synthetic-discovery.json"))
    repo = next(
        e for e in result.entities if e.kind == "repository" and e.attributes["role"] == "source"
    )
    job = Entity(
        source_instance=repo.source_instance,
        kind="build_job",
        external_id="1001:build",
        attributes={"name": "build", "module_paths": ["ui-template", "common-lib"]},
    )
    result.entities.append(job)
    basis = next(e for e in result.edges if e.relation == "contains_module")
    result.edges.append(
        Edge(
            source_id=repo.id,
            target_id=job.id,
            relation="declares_build_job",
            status="observed_verified",
            evidence_ids=basis.evidence_ids,
        )
    )
    with Catalog(tmp_path / "catalog.sqlite3") as catalog:
        catalog.import_scan(result, scope="fixture")
        asyncio.run(MappingService(catalog, provider=NoopProvider()).suggest())
        inputs = [e for e in catalog.read_graph().edges if e.relation == "declares_module_input"]
        assert len(inputs) == 2
        assert all(e.target_id == job.id and e.status == "observed_verified" for e in inputs)
        assert all(catalog.get_evidence(e.evidence_ids) for e in inputs)


def test_similar_names_remain_candidates_and_no_ai_flag(tmp_path: Path) -> None:
    result = discover_fixture(Path("fixtures/synthetic-discovery.json"))
    business = next(e for e in result.entities if e.kind == "business_project")
    business.attributes["name"] = "api common-lib service"
    provider = FakeProvider("invalid")
    with Catalog(tmp_path / "catalog.sqlite3") as catalog:
        catalog.import_scan(result, scope="fixture")
        service = MappingService(catalog, provider=provider)
        assert asyncio.run(service.suggest(no_ai=True))["ai_status"] == "disabled"
        assert provider.received == []
        candidates = catalog.list_edges(status="candidate")["items"]
        unresolved = catalog.list_edges(status="unresolved")["items"]
        assert len(candidates) + len(unresolved) == 3
        assert candidates and all(edge["confidence"] < 0.8 for edge in candidates)
        assert catalog.list_edges(status="confirmed")["items"] == []


def test_stale_relationship_cannot_be_accepted(tmp_path: Path) -> None:
    result = sample()
    with Catalog(tmp_path / "catalog.sqlite3") as catalog:
        catalog.import_scan(result, scope="demo")
        catalog.import_scan(result.model_copy(update={"edges": []}), scope="demo")
        service = MappingService(catalog)
        with pytest.raises(DceError):
            service.review(
                result.edges[0].id,
                action="accept",
                actor="owner",
                reason="proof",
                expected_version=2,
            )


def test_ai_failure_is_durable_and_retryable(tmp_path: Path) -> None:
    with Catalog(tmp_path / "catalog.sqlite3") as catalog:
        catalog.import_scan(sample(), scope="demo")
        service = MappingService(catalog, provider=FakeProvider("invalid"))
        report = asyncio.run(service.suggest())
        run = catalog.scan_status()["items"][0]
        assert run["id"] == report["run_id"]
        assert run["status"] == "failed" and run["summary"]["ai_status"] == "invalid_response"
        service.provider = NoopProvider()
        report = asyncio.run(service.suggest())
        assert catalog.scan_status()["items"][0]["status"] == "complete"
        assert report["ai_status"] == "ok"
