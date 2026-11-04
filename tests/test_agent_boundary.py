from pathlib import Path
from unittest.mock import patch

from dce.app.services import AppServices
from dce.common.config import Settings


def test_default_core_does_not_invoke_mapping_or_fixture_fallback(tmp_path: Path) -> None:
    with AppServices(Settings(catalog_path=tmp_path / "cache.sqlite3")) as service:
        with patch("dce.app.mapping.MappingService.suggest", side_effect=AssertionError):
            result = service.initialize()
            assert result["mapping"]["status"] == "host_agent_required"
            assert service.bug_context("DEMO-1001", include_assets=False)["modules"] == []
        assert service.catalog.list_edges(status="candidate")["items"] == []
