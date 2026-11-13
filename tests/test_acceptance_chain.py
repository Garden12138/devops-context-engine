from pathlib import Path

from dce.app.services import AppServices
from dce.common.config import Settings


def test_many_modules_jobs_images_services_end_to_end(tmp_path: Path) -> None:
    with AppServices(Settings(catalog_path=tmp_path / "catalog.sqlite3")) as service:
        service.initialize()
        graph = service.catalog.read_graph()
        common = next(
            e for e in graph.entities if e.kind == "module" and e.attributes["path"] == "common-lib"
        )
        jobs = {
            edge.target_id
            for edge in graph.edges
            if edge.source_id == common.id and edge.relation == "declares_module_input"
        }
        assert len(jobs) == 2
        images = {
            edge.target_id
            for edge in graph.edges
            if edge.source_id in jobs and edge.relation == "declares_build_image"
        }
        assert len(images) == 3
        for image in images:
            runtime = [
                edge.source_id
                for edge in graph.edges
                if edge.target_id == image and edge.relation == "observes_image_reference"
            ]
            assert len(runtime) == 2
        assert all(
            service.catalog.get_evidence(edge.evidence_ids)
            for edge in graph.edges
            if edge.relation == "declares_module_input"
        )
