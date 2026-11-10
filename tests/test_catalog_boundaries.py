from pathlib import Path

import pytest
from test_catalog import sample

from dce.catalog.db import Catalog
from dce.common.errors import DceError
from dce.graph.model import DiscoveryResult


def test_edge_disappears_without_entity_deletion_and_reappears(tmp_path: Path) -> None:
    result = sample()
    key = result.edges[0].id
    with Catalog(tmp_path / "db.sqlite3") as catalog:
        catalog.import_scan(result, scope="one")
        catalog.import_scan(result, scope="two")
        catalog.review(key, action="accept", actor="owner", reason="verified")
        without_edge = result.model_copy(update={"edges": []})
        catalog.import_scan(without_edge, scope="one")
        assert not catalog.edge(key)["stale"]
        catalog.import_scan(without_edge, scope="two")
        stale = catalog.edge(key)
        assert stale["stale"] and stale["conflict"]
        assert stale["valid_until"] and stale["status"] == "confirmed"
        assert not catalog.get_entity(result.entities[0].id)["deleted"]
        assert len(catalog.edge_versions(key)) == 3
        catalog.import_scan(without_edge, scope="two")
        assert len(catalog.edge_versions(key)) == 3
        catalog.import_scan(result, scope="two")
        assert catalog.edge(key)["status"] == "confirmed"
        assert catalog.edge(key)["conflict"] and not catalog.edge(key)["stale"]
        assert len(catalog.edge_versions(key)) == 4


@pytest.mark.parametrize(
    "corruption", ["snapshot", "evidence", "missing_evidence", "duplicate_evidence"]
)
def test_invalid_observations_roll_back(tmp_path: Path, corruption: str) -> None:
    result = sample()
    with Catalog(tmp_path / "db.sqlite3") as catalog:
        catalog.import_scan(result, scope="demo")
        before = catalog.counts()
        if corruption == "snapshot":
            result.snapshots[0].metadata["changed"] = "unexpected"
        elif corruption == "evidence":
            result.evidence[0].summary = "contradicts immutable evidence"
        elif corruption == "missing_evidence":
            result.edges[0].evidence_ids = ["unknown"]
        else:
            result.edges[0].evidence_ids *= 2
        result.entities[0].attributes["changed"] = "must-roll-back"
        with pytest.raises(DceError):
            catalog.import_scan(result, scope="demo")
        assert "changed" not in catalog.get_entity(result.entities[0].id)["attributes"]
        assert catalog.counts() == before


def test_local_permissions_and_reopen(tmp_path: Path) -> None:
    path = tmp_path / "private" / "db.sqlite3"
    result = sample()
    with Catalog(path) as catalog:
        catalog.import_scan(result, scope="demo")
    assert path.stat().st_mode & 0o777 == 0o600
    assert path.parent.stat().st_mode & 0o777 == 0o700
    with Catalog(path) as catalog:
        assert catalog.get_entity(result.entities[0].id)["external_id"] == "1"
        assert len(catalog.history(result.entities[0].id)) == 1
    link = tmp_path / "symlink.sqlite3"
    link.symlink_to(path)
    with pytest.raises(DceError):
        Catalog(link)


def test_catalog_query_contracts(tmp_path: Path) -> None:
    result = sample()
    with Catalog(tmp_path / "db.sqlite3") as catalog:
        with pytest.raises(DceError):
            catalog.import_scan(DiscoveryResult(), scope=" ")
        catalog.import_scan(result, scope="demo")
        assert catalog.snapshot(result.snapshots[0].id)["version"] == "v1"
        assert len(catalog.get_evidence(result.edges[0].evidence_ids)) == 1
        assert len(catalog.list_edges(status="candidate")["items"]) == 1
        assert catalog.list_edges(status="confirmed")["items"] == []
        assert catalog.trace(result.entities[0].id, max_depth=0)["edges"] == []
        assert catalog.trace(result.entities[0].id, direction="in")["edges"] == []
        assert len(catalog.trace(result.entities[0].id, direction="both")["edges"]) == 1
        for operation in (
            lambda: catalog.snapshot("absent"),
            lambda: catalog.get_evidence(["ref"] * 101),
            lambda: catalog.review("absent", action="accept", actor="owner", reason="proof"),
        ):
            with pytest.raises(DceError):
                operation()
        catalog.review(
            result.edges[0].id, action="override", actor="owner", reason="manual override"
        )
        assert catalog.edge(result.edges[0].id)["status"] == "confirmed"


def test_import_cannot_escalate_candidate_to_human_confirmed(tmp_path: Path) -> None:
    result = sample()
    result.edges[0] = result.edges[0].model_copy(update={"status": "confirmed"})
    with Catalog(tmp_path / "db.sqlite3") as catalog:
        with pytest.raises(DceError):
            catalog.import_scan(result, scope="hostile-provider")
        assert catalog.counts()["edges"] == 0


def test_catalog_storage_redacts_accidentally_supplied_secrets(tmp_path: Path) -> None:
    result = sample()
    result.entities[0].attributes.update(
        {"Token": "synthetic-private", "name": "password=synthetic-private"}
    )
    result.snapshots[0].metadata["Cookie"] = "synthetic-private"
    result.evidence[0].summary = "Token=synthetic-private"
    path = tmp_path / "db.sqlite3"
    with Catalog(path) as catalog:
        catalog.import_scan(result, scope="demo")
        assert "synthetic-private" not in str(catalog.get_entity(result.entities[0].id))
        assert "synthetic-private" not in str(catalog.snapshot(result.snapshots[0].id))
        catalog.review(
            result.edges[0].id, action="reject", actor="owner", reason="Token=synthetic-private"
        )
        assert "synthetic-private" not in str(catalog.reviews(result.edges[0].id))
    assert b"synthetic-private" not in path.read_bytes()
