import asyncio
import base64
import re
from contextlib import ExitStack
from pathlib import Path
from typing import Any

import httpx
from pydantic import SecretStr

from dce.app.mapping import MappingService
from dce.catalog.db import Catalog
from dce.common.config import PlatformConfig, Settings
from dce.common.errors import DceError, ErrorCode
from dce.connectors.gitlab import GitLab
from dce.connectors.http import Reader
from dce.connectors.portainer import Portainer
from dce.connectors.zentao import ZenTao
from dce.discovery.checkpoint import Checkpoint
from dce.discovery.crawler import Crawler, ScanScope
from dce.discovery.fixture import discover_fixture, load_fixture
from dce.graph.model import fingerprint
from dce.graph.rules import suggestions
from dce.security.redact import redact

DEFAULT_FIXTURE = Path("fixtures/synthetic-discovery.json")
SYNTHETIC_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
)


def resource_key(value: str) -> str:
    if not re.fullmatch(r"[\w./:-]{1,250}", value) or ".." in value or "://" in value:
        raise DceError(ErrorCode.INVALID_PAYLOAD, "Expected a controlled resource ID.")
    return value


def external_id(value: Any) -> str | int | None:
    if isinstance(value, dict):
        value = value.get("id")
    return value if isinstance(value, (str, int)) and not isinstance(value, bool) else None


class AppServices:
    def __init__(
        self,
        settings: Settings,
        *,
        fixture: Path = DEFAULT_FIXTURE,
        transports: dict[str, httpx.BaseTransport] | None = None,
    ) -> None:
        self.settings = settings
        self.fixture = fixture
        self.transports = transports or {}
        self.catalog = Catalog(settings.catalog_path)

    def __enter__(self) -> "AppServices":
        return self

    def __exit__(self, *_: object) -> None:
        self.catalog.engine.dispose()

    def reader(self, kind: str) -> Reader:
        return Reader(
            self.settings.platform(kind), self.settings, transport=self.transports.get(kind)
        )

    @staticmethod
    def require_live(live: bool, read_only: bool) -> None:
        if live and not read_only:
            raise DceError(ErrorCode.PERMISSION_DENIED, "Live mode requires --read-only.")

    def initialize(self, *, fixture: Path | None = None, no_ai: bool = True) -> dict[str, Any]:
        path = fixture or self.fixture
        result = discover_fixture(path)
        scan_id = self.catalog.import_scan(
            result, scope="fixture:" + fingerprint(str(path.resolve()))
        )
        mapping = asyncio.run(MappingService(self.catalog).suggest(no_ai=no_ai))
        return {
            "scan_id": scan_id,
            "counts": self.catalog.counts(),
            "mapping": mapping,
            "verification": "synthetic",
            "external_status": "not_verified",
        }

    def discover(self, scope: ScanScope, *, live: bool, read_only: bool) -> dict[str, Any]:
        self.require_live(live, read_only)
        if not live:
            return self.initialize()
        with ExitStack() as contexts:
            adapters: dict[str, Any] = {}
            for name, adapter in (("gitlab", GitLab), ("zentao", ZenTao), ("portainer", Portainer)):
                if any(
                    values for key, values in scope.model_dump().items() if key.startswith(name)
                ):
                    adapters[name] = adapter(contexts.enter_context(self.reader(name)))
            scope_id = fingerprint(
                {
                    "scope": scope.model_dump(),
                    "sources": {
                        name: reader.reader.config.instance_id for name, reader in adapters.items()
                    },
                }
            )
            checkpoint = Checkpoint(
                self.settings.catalog_path.parent / "checkpoints" / f"{scope_id}.json", scope_id
            )
            result = Crawler(scope, checkpoint, **adapters).run()
            scan_id = self.catalog.import_scan(result, scope=scope_id)
            mapping = asyncio.run(MappingService(self.catalog).suggest(no_ai=True))
            return {
                "scan_id": scan_id,
                "counts": self.catalog.counts(),
                "mapping": mapping,
                "warnings": result.warnings,
                "verification": "live_read_only",
                "scope": scope.model_dump(),
            }

    def bug_context(
        self,
        bug_id: str,
        *,
        include_assets: bool = True,
        live: bool = False,
        read_only: bool = False,
    ) -> dict[str, Any]:
        resource_key(bug_id)
        self.require_live(live, read_only)
        if live:
            reader = self.reader("zentao")
            ephemeral = None
        else:
            fixture = load_fixture(self.fixture)
            config_data = next(
                item for item in fixture["source_instances"] if item["kind"] == "zentao"
            )
            config = PlatformConfig(
                instance_id=config_data["id"],
                base_url=config_data["base_url"],
                token=SecretStr("synthetic-only"),
            )

            def handle(request: httpx.Request) -> httpx.Response:
                if request.url.path.startswith("/api.php/v1/bugs/"):
                    match = next(
                        (bug for bug in fixture["zentao"]["bugs"] if str(bug["id"]) == bug_id), None
                    )
                    return (
                        httpx.Response(200, json={**match, "steps": match["steps_html"]})
                        if match
                        else httpx.Response(404)
                    )
                return httpx.Response(
                    200, content=SYNTHETIC_PNG, headers={"Content-Type": "image/png"}
                )

            reader = Reader(config, self.settings, transport=httpx.MockTransport(handle))
            ephemeral = discover_fixture(self.fixture)
        with reader:
            adapter = ZenTao(reader)
            bug = adapter.bug(bug_id)
            text, urls = adapter.parse_steps(bug)
            assets, warnings = [], []
            if include_assets:
                for url in urls[:10]:
                    try:
                        assets.append(
                            adapter.download_image(
                                url, self.settings.catalog_path.parent / "assets"
                            )
                        )
                    except DceError as exc:
                        warnings.append(f"ASSET_{exc.code.value}")
            modules = self._bug_modules(bug, reader.config.instance_id, ephemeral)
            if not any(module["status"] == "confirmed" for module in modules):
                warnings.append("BUSINESS_MAPPING_UNCONFIRMED")
            secrets = (reader.config.token.get_secret_value(),)
            return {
                "bug_id": bug_id,
                "source_instance": reader.config.instance_id,
                "title": redact(str(bug.get("title", ""))[:300], secrets),
                "steps": redact(text[:1800], secrets),
                "project_id": external_id(bug.get("project_id", bug.get("project"))),
                "product_id": external_id(bug.get("product_id", bug.get("product"))),
                "assets": assets,
                "modules": modules[:20],
                "evidence_ids": sorted(
                    {ref for module in modules[:20] for ref in module["evidence_ids"]}
                ),
                "warnings": warnings,
                "uncertainties": ["Module associations require human verification."]
                if "BUSINESS_MAPPING_UNCONFIRMED" in warnings
                else [],
                "next_action": "Review mapping evidence before selecting a module.",
                "truncated": len(text) > 1800 or len(modules) > 20 or len(urls) > 10,
                "verification": "live_read_only" if live else "synthetic",
            }

    def _bug_modules(
        self, bug: dict[str, Any], source: str, ephemeral: Any
    ) -> list[dict[str, Any]]:
        graph = self.catalog.read_graph()
        entities = {entity.id: entity for entity in graph.entities}
        if ephemeral is not None:
            entities.update({entity.id: entity for entity in ephemeral.entities})
        project = bug.get("project_id", bug.get("project"))
        if isinstance(project, dict):
            project = project.get("id")
        business = {
            entity.id
            for entity in entities.values()
            if entity.source_instance == source
            and entity.kind == "business_project"
            and entity.external_id == str(project)
        }
        rows: list[dict[str, Any]] = []
        has_persisted_mapping = False
        offset = 0
        while True:
            page = self.catalog.list_edges(limit=100, offset=offset)
            has_persisted_mapping |= any(e["source_id"] in business for e in page["items"])
            rows.extend(
                e
                for e in page["items"]
                if e["source_id"] in business and not e["stale"] and e["status"] not in {"rejected"}
            )
            if not page["more_available"]:
                break
            offset += 100
        if not rows and not has_persisted_mapping and ephemeral is not None:
            rows = [
                {"id": edge.id, **edge.model_dump()}
                for edge in suggestions(ephemeral).edges
                if edge.source_id in business
            ]
        return [
            {
                "module_id": row["target_id"],
                "path": entities[row["target_id"]].attributes.get("path"),
                "status": row["status"],
                "confidence": row["confidence"],
                "evidence_ids": row["evidence_ids"],
                "mapping_id": row["id"],
            }
            for row in rows
            if row["target_id"] in entities and entities[row["target_id"]].kind == "module"
        ]

    def pipeline_diagnose(
        self, project: str, pipeline: str, *, live: bool = False, read_only: bool = False
    ) -> dict[str, Any]:
        resource_key(project), resource_key(pipeline)
        self.require_live(live, read_only)
        if live:
            with self.reader("gitlab") as reader:
                adapter = GitLab(reader)
                repo = adapter.project(project)
                data = adapter.pipeline(project, pipeline)
                jobs = list(adapter.jobs(project, pipeline))
                for job in jobs:
                    if job.get("status") == "failed":
                        if external_id(job.get("id")) is None:
                            raise DceError(ErrorCode.API_INCOMPATIBLE, "Failed job ID is missing.")
                        job["trace_excerpt"] = adapter.trace(project, str(job["id"])).splitlines()[
                            -100:
                        ]
        else:
            fixture = load_fixture(self.fixture)
            fixture_pipeline = next(
                (
                    item
                    for item in fixture["gitlab"]["pipelines"]
                    if str(item["id"]) == pipeline and str(item["project_id"]) == project
                ),
                None,
            )
            if fixture_pipeline is None:
                raise DceError(ErrorCode.NOT_FOUND, "Pipeline was not found.")
            data = fixture_pipeline
            repo = next(
                (item for item in fixture["gitlab"]["source_repos"] if str(item["id"]) == project),
                {},
            )
            jobs = data["jobs"]
        if not isinstance(data.get("status"), str):
            raise DceError(ErrorCode.API_INCOMPATIBLE, "Pipeline status is missing.")
        failures = []
        secrets = tuple(
            config.token.get_secret_value()
            for config in (self.settings.gitlab, self.settings.zentao, self.settings.portainer)
            if config
        )
        for job in jobs:
            if job.get("status") != "failed":
                continue
            if external_id(job.get("id")) is None:
                raise DceError(ErrorCode.API_INCOMPATIBLE, "Failed job ID is missing.")
            lines = [
                redact(str(line)[:300], secrets) for line in job.get("trace_excerpt", [])[-100:]
            ]
            text = "\n".join(lines)
            cause = "missing_make" if "make: not found" in text else "unresolved"
            failures.append(
                {
                    "job_id": job["id"],
                    "stage": job.get("stage"),
                    "status": "failed",
                    "root_cause": cause,
                    "secondary": ["buildx_image_unavailable"]
                    if "No such image: moby/buildkit" in text
                    else [],
                    "trace_excerpt": lines,
                }
            )
        return {
            "project_id": project,
            "pipeline_id": pipeline,
            "status": data.get("status"),
            "default_branch": repo.get("default_branch", "not_verified"),
            "failures": failures,
            "next_action": "Check the failed job prerequisites; no pipeline was triggered.",
        }

    def deployment_inspect(self, stack_key: str) -> dict[str, Any]:
        stack = self.catalog.find("stack", resource_key(stack_key))
        graph = self.catalog.read_graph()
        snapshots = [
            snapshot for snapshot in graph.snapshots if snapshot.resource_key == stack["id"]
        ]
        return {
            "stack": stack,
            "snapshots": [
                {
                    "snapshot_id": s.id,
                    "kind": s.kind,
                    "version": s.version,
                    "service_count": s.metadata.get(
                        "service_count", len(s.metadata.get("services", []))
                    ),
                    "incomplete": s.metadata.get("incomplete", False),
                }
                for s in snapshots
            ],
            "health": "unknown",
            "environment": "unresolved",
            "version_match": "not_verified",
            "trace": self.catalog.trace(stack["id"], limit=20),
        }

    def project_context(self, source: str, project_key: str, depth: int = 2) -> dict[str, Any]:
        resource_key(source), resource_key(project_key)
        try:
            project = self.catalog.find("repository", project_key, source)
        except DceError as exc:
            if exc.code != ErrorCode.NOT_FOUND:
                raise
            project = self.catalog.find("business_project", project_key, source)
        return {"project": project, "trace": self.catalog.trace(project["id"], max_depth=depth)}

    def service_trace(
        self, service_key: str, direction: str = "both", max_depth: int = 2
    ) -> dict[str, Any]:
        service = self.catalog.find("service", resource_key(service_key))
        return self.catalog.trace(service["id"], direction=direction, max_depth=max_depth)

    def discovery_status(self, scan_id: str | None = None) -> dict[str, Any]:
        page = self.catalog.scan_status(limit=20)
        if scan_id:
            resource_key(scan_id)
            page["items"] = [self.catalog.get_scan(scan_id)]
            page["more_available"] = False
        page["items"] = [
            {
                **{
                    key: row[key]
                    for key in ("id", "scope", "status", "started_at", "finished_at", "error_code")
                },
                "summary": row["summary"],
                "anomaly_count": len(row["anomalies"]),
            }
            for row in page["items"]
        ]
        page["pending_reviews"] = self.catalog.pending_reviews()
        return page
