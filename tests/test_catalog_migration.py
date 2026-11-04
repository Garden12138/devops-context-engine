import sqlite3
from pathlib import Path
from unittest.mock import patch

import pytest

from dce.catalog.backup import backup, version
from dce.catalog.db import Catalog
from dce.common.errors import DceError, ErrorCode
from dce.discovery.fixture import discover_fixture


def test_migration_backs_up_before_role_change_and_preserves_rows(tmp_path: Path):
    path = tmp_path / "catalog.sqlite3"
    with Catalog(path, revision="0002") as catalog:
        catalog.import_scan(
            discover_fixture(Path("fixtures/synthetic-discovery.json")), scope="demo"
        )
        before = catalog.counts()
        edge = catalog.list_edges()["items"][0]
        catalog.review(
            edge["id"],
            action="accept",
            actor="owner",
            reason="historical test",
            expected_version=edge["version"],
        )
        reviews = catalog.reviews(edge["id"])
        history = catalog.edge_versions(edge["id"])
    with Catalog(path) as catalog:
        assert catalog.counts() == before
        assert catalog.reviews(edge["id"]) == reviews
        assert catalog.edge_versions(edge["id"]) == history
        assert catalog.edge(edge["id"])["status"] == "confirmed"
        assert catalog.role()["role"] == "resource_cache_and_history"
        saved = catalog.last_backup
        assert saved is not None and version(saved) == "0002"
        assert saved.stat().st_mode & 0o777 == 0o600
        with sqlite3.connect(saved) as db:
            assert db.execute("SELECT COUNT(*) FROM entities").fetchone()[0] == before["entities"]
            assert db.execute("PRAGMA quick_check").fetchone()[0] == "ok"
    with Catalog(path) as catalog:
        assert catalog.last_backup is None
    # Backup is a usable pre-migration database and remains untouched.
    assert version(saved) == "0002"


def test_backup_failure_blocks_migration_and_preserves_source(tmp_path):
    path = tmp_path / "catalog.sqlite3"
    with Catalog(path, revision="0002"):
        pass
    with patch("dce.catalog.db.backup", side_effect=DceError(ErrorCode.INVALID_PAYLOAD, "safe")):
        with pytest.raises(DceError):
            Catalog(path)
    assert version(path) == "0002"
    with Catalog(path):
        pass
    bad = tmp_path / "bad.sqlite3"
    bad.symlink_to(path)
    with pytest.raises(DceError):
        backup(bad)
    (tmp_path / "backups").rename(tmp_path / "old-backups")
    (tmp_path / "backups").symlink_to(tmp_path / "old-backups")
    with pytest.raises(DceError):
        backup(path)


def test_corrupt_backup_and_deadline_cleanup(tmp_path):
    path = tmp_path / "corrupt.sqlite3"
    path.write_bytes(b"not a database")
    with pytest.raises(DceError):
        backup(path)
    assert list((tmp_path / "backups").iterdir()) == []
    with pytest.raises(DceError):
        version(path)
    path.unlink()
    with Catalog(path):
        pass
    with patch("dce.catalog.backup.time.monotonic", side_effect=[0, 100]):
        with pytest.raises(DceError):
            backup(path)
    assert list((tmp_path / "backups").iterdir()) == []
