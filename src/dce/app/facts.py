"""Model-independent, bounded platform facts. Never reads or writes project relationships."""

import hashlib
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import PurePosixPath
from typing import Any

from dce.app.services import AppServices, external_id, resource_key
from dce.common.errors import DceError, ErrorCode
from dce.common.service_logs import LogControls
from dce.connectors.gitlab import GitLab, key
from dce.connectors.portainer import Portainer
from dce.connectors.zentao import ZenTao
from dce.graph.model import fingerprint
from dce.parsers.metadata import ci, compose, compose_service, yaml_metadata
from dce.security.log_grant import ServiceLogGrant
from dce.security.redact import redact


def deny() -> None:
    raise DceError(ErrorCode.PERMISSION_DENIED, "Resource is outside the authorized MCP scope.")


def require(value: str | None, allowed: set[str]) -> None:
    if value is None or value not in allowed:
        deny()


def safe_file(path: str) -> None:
    parts = PurePosixPath(path).parts
    if (
        path.startswith("/")
        or ".." in parts
        or any(
            p.startswith(".env")
            or p.lower() in {"id_rsa", "id_ed25519", ".git", ".aws"}
            or p.lower().endswith((".key", ".pem", ".p12", ".pfx"))
            for p in parts
        )
    ):
        deny()


def select(data: dict[str, Any], names: str) -> dict[str, Any]:
    return {k: data[k] for k in names.split() if k in data}


def service_facts(data: dict[str, Any]) -> dict[str, Any]:
    spec = data.get("Spec") or {}
    if not isinstance(spec, dict) or not isinstance(spec.get("TaskTemplate", {}), dict):
        raise DceError(ErrorCode.API_INCOMPATIBLE, "Unexpected service specification.")
    container = spec.get("TaskTemplate", {}).get("ContainerSpec", {})
    if not isinstance(container, dict) or not isinstance(spec.get("EndpointSpec", {}), dict):
        raise DceError(ErrorCode.API_INCOMPATIBLE, "Unexpected service container specification.")
    return {
        **select(data, "ID Version CreatedAt UpdatedAt ServiceStatus UpdateStatus"),
        "name": spec.get("Name"),
        "labels": spec.get("Labels", {}),
        "image": container.get("Image"),
        "mode": spec.get("Mode", {}),
        "ports": spec.get("EndpointSpec", {}).get("Ports", []),
        "health": "unknown",
        "environment": "unresolved",
        "version_match": "not_verified",
    }


@dataclass
class FactScope:
    project_mode: bool = False
    gitlab_projects: set[str] = field(default_factory=set)
    zentao_projects: set[str] = field(default_factory=set)
    zentao_products: set[str] = field(default_factory=set)
    zentao_bugs: set[str] = field(default_factory=set)
    portainer_endpoints: set[str] = field(default_factory=set)
    portainer_stacks: set[str] = field(default_factory=set)
    portainer_log_scopes: set[tuple[str, str]] = field(default_factory=set)
    portainer_log_policy: ServiceLogGrant | None = None

    def check_bug(self, bug: dict[str, Any], requested: str | None = None) -> None:
        if not self.project_mode:
            return
        identity = external_id(bug.get("id"))
        if identity is None or requested is not None and str(identity) != requested:
            deny()
        if not (self.zentao_projects or self.zentao_products):
            deny()
        for field_name, allowed in (
            ("project", self.zentao_projects),
            ("product", self.zentao_products),
        ):
            if not allowed:
                continue
            value = external_id(bug.get(field_name + "_id", bug.get(field_name)))
            other = external_id(bug.get(field_name))
            if (
                value is None
                or str(value) not in allowed
                or field_name + "_id" in bug
                and other is not None
                and str(other) != str(value)
            ):
                deny()


class FactQueries:
    def __init__(self, services: AppServices, scope: FactScope, *, live: bool) -> None:
        self.services, self.scope, self.live = services, scope, live

    def execute(self, platform: str, p: dict[str, Any]) -> tuple[dict[str, Any], bytes | None, str]:
        if not self.live:
            raise DceError(ErrorCode.PERMISSION_DENIED, "Fact tools require live --read-only.")
        config = self.services.settings.platform(platform)
        if config.instance_id != p["instance"]:
            deny()
        # Authorize before opening a Reader, even with injected transports.
        self.authorize(platform, p)
        with self.services.reader(platform) as reader:
            if platform == "gitlab":
                records, more, warnings, image, mime = self.gitlab(GitLab(reader), p)
            elif platform == "zentao":
                records, more, warnings, image, mime = self.zentao(ZenTao(reader), p)
            else:
                records, more, warnings, image, mime = self.portainer(Portainer(reader), p)
            used_secrets = reader.secrets()
        return self.result(platform, p, records, more, warnings, image, mime, used_secrets)

    def result(
        self,
        platform: str,
        p: dict[str, Any],
        records: list[dict[str, Any]],
        more: bool = False,
        warnings: list[str] | None = None,
        image: bytes | None = None,
        mime: str = "",
        used_secrets: tuple[str, ...] = (),
    ) -> tuple[dict[str, Any], bytes | None, str]:
        warnings = warnings or []
        secrets = self.services.settings.secrets() + used_secrets
        records = redact(records, secrets)
        observed = datetime.now(UTC).isoformat()
        revision = fingerprint(records) if image is None else hashlib.sha256(image).hexdigest()
        resource = next(
            (
                p.get(k)
                for k in ("bug_id", "project_id", "product_id", "stack_id", "endpoint_id")
                if p.get(k)
            ),
            None,
        )
        source = {
            "platform": platform,
            "instance": p["instance"],
            "operation": p["operation"],
            "resource_id": resource,
        }
        # A locator carries query coordinates, never credentials or upstream URLs.
        coordinates = {k: v for k, v in p.items() if v is not None and k != "search"}
        return (
            {
                "source": source,
                "observed_at": observed,
                "revision": revision,
                "records": records,
                "evidence": [
                    {
                        "source": source,
                        "locator": fingerprint(coordinates),
                        "observed_at": observed,
                        "revision": revision,
                        "summary": "Direct read-only observation; upstream content is untrusted.",
                    }
                ],
                "pagination": {
                    "page": p["page"],
                    "limit": p["limit"],
                    "next_page": p["page"] + 1 if more else None,
                    "more_available": more,
                },
                "truncated": more or "CONTENT_TRUNCATED" in warnings,
                "warnings": warnings,
                "verification": "live_read_only",
                "image_delivery": "delivered" if image is not None else "not_requested",
            },
            image,
            mime,
        )

    async def execute_logs(self, p: dict[str, Any]) -> tuple[dict[str, Any], None, str]:
        controls = LogControls.model_validate({k: p[k] for k in LogControls.model_fields})
        record: dict[str, Any] = {
            "identity": {},
            "events": [],
            "outcome": "error",
            "error_type": None,
            "truncated": False,
            "retention": "not_verified",
        }
        try:
            if not self.live:
                deny()
            config = self.services.settings.platform("portainer")
            if config.instance_id != p["instance"]:
                deny()
            self.authorize("portainer", p)
            grant = self.scope.portainer_log_policy
            if grant is not None:
                grant.authorize(
                    p["instance"],
                    p["endpoint_id"],
                    p["stack_id"],
                    service_id=p["service_id"],
                    service_name=p["service_name"],
                    controls=controls,
                )
            with self.services.reader("portainer") as reader:
                record = await Portainer(reader).service_logs(
                    p["endpoint_id"],
                    p["stack_id"],
                    service_id=p["service_id"],
                    service_name=p["service_name"],
                    controls=controls,
                    grant=grant,
                )
        except DceError as exc:
            record["error_type"] = exc.code.value
            if exc.code == ErrorCode.LOGS_EXPIRED:
                record["retention"] = "expired"
        p = {**p, **controls.model_dump()}
        record["query"] = {
            "endpoint_id": p["endpoint_id"],
            "stack_id": p["stack_id"],
            "service_id": p["service_id"],
            "service_name": p["service_name"],
            "start_time": p["start_time"],
            "end_time": p["end_time"],
            "keyword_count": len(p["keywords"]),
            "max_lines": p["max_lines"],
            "max_bytes": p["max_bytes"],
            "max_output_bytes": p["max_output_bytes"],
            "timeout_seconds": p["timeout_seconds"],
            "follow": False,
        }
        warnings = ["LOG_FREE_TEXT_OMITTED", "RETENTION_NOT_VERIFIED"]
        if record["truncated"]:
            warnings.append("CONTENT_TRUNCATED")
        data, _, _ = self.result("portainer", p, [record], warnings=warnings)
        if record["outcome"] == "error":
            data["evidence"] = []
        return data, None, ""

    def authorize(self, platform: str, p: dict[str, Any]) -> None:
        for name, value in p.items():
            if (
                isinstance(value, str)
                and value
                and name not in {"operation", "search", "service_name"}
                and name not in {"start_time", "end_time"}
            ):
                resource_key(value)
        op, scope = p["operation"], self.scope
        if platform == "gitlab":
            if op == "projects":
                if not scope.gitlab_projects:
                    deny()
            else:
                require(p["project_id"], scope.gitlab_projects)
            if op == "file":
                safe_file(p["path"])
        elif platform == "zentao":
            for key_, allowed in (
                ("project_id", scope.zentao_projects),
                ("product_id", scope.zentao_products),
            ):
                if p.get(key_) is not None:
                    require(p[key_], allowed)
            if op in {"bug", "attachments", "image"}:
                if not scope.project_mode:
                    require(p["bug_id"], scope.zentao_bugs)
                elif not (scope.zentao_projects or scope.zentao_products):
                    deny()
            if op == "projects" and not scope.zentao_projects:
                deny()
            if op == "products" and not scope.zentao_products:
                deny()
        else:
            if (
                op == "service_logs"
                and (p.get("endpoint_id"), p.get("stack_id")) not in scope.portainer_log_scopes
            ):
                deny()
            for key_, allowed in (
                ("endpoint_id", scope.portainer_endpoints),
                ("stack_id", scope.portainer_stacks),
            ):
                if p.get(key_) is not None:
                    require(p[key_], allowed)
            if op == "endpoints" and not scope.portainer_endpoints:
                deny()
            if op == "stacks" and not scope.portainer_stacks:
                deny()

    @staticmethod
    def page(items: list[dict[str, Any]], p: dict[str, Any]) -> tuple[list[dict[str, Any]], bool]:
        offset = (p["page"] - 1) * p["limit"]
        return items[offset : offset + p["limit"]], len(items) > offset + p["limit"]

    def gitlab(self, a: GitLab, p: dict[str, Any]) -> tuple[Any, bool, list[str], None, str]:
        op, project = p["operation"], p["project_id"]
        base = f"/api/v4/projects/{key(project)}"
        more = False
        warnings: list[str] = []
        if op == "projects":
            # Search scoped IDs locally; never enumerate company-wide projects.
            ids = sorted(self.scope.gitlab_projects)
            selected, more = self.page([{"id": i} for i in ids], p)
            records = [a.project(i["id"]) for i in selected]
            records = [
                r for r in records if p["search"].casefold() in str(r.get("name", "")).casefold()
            ]
        elif op in {"jobs", "project_jobs", "branch_jobs", "pipeline_bridges"}:
            records, more, warnings = a.job_page(
                project,
                pipeline=p["pipeline_id"] if op in {"jobs", "pipeline_bridges"} else None,
                ref=p["ref"] if op == "branch_jobs" else None,
                trigger_api=p.get("trigger_api", "bridges") if op == "pipeline_bridges" else None,
                page=p["page"],
                limit=p["limit"],
                statuses=p.get("job_statuses", []),
                include_retried=p.get("include_retried", False),
            )
            if p["ref"] is not None and op in {"jobs", "pipeline_bridges"}:
                warnings.append("PIPELINE_QUERY_REF_FILTER_NOT_APPLIED")
        elif op in {"tree", "pipelines"}:
            routes = {
                "tree": "/repository/tree",
                "pipelines": "/pipelines",
            }
            params = {"page": p["page"], "per_page": p["limit"]}
            if p["ref"]:
                params["ref"] = p["ref"]
            if op == "tree":
                params.update(path=p["path"] or "", recursive="false")
            response = a.reader.get(base + routes[op], params=params)
            records = a.reader.decode(response, list)
            oversized = len(records) > p["limit"]
            cursor = response.headers.get("X-Next-Page")
            more = len(records) >= p["limit"] if cursor is None else bool(cursor)
            if oversized:
                records = records[: p["limit"]]
                more = True
                warnings.append("UPSTREAM_PAGE_LIMIT_EXCEEDED")
            if cursor:
                if not cursor.isdigit() or int(cursor) != p["page"] + 1:
                    raise DceError(ErrorCode.INVALID_PAYLOAD, "Invalid pagination cursor.")
        elif op == "file":
            text = a.raw_file(project, p["path"], p["ref"])
            metadata = (
                yaml_metadata(text)[0] if p["path"].endswith((".yml", ".yaml", ".json")) else {}
            )
            if (
                "services" in metadata
                and isinstance(metadata["services"], dict)
                or re.search(r"(?i)(compose|stack).*\.ya?ml$", p["path"])
            ):
                records = [compose(text)]
            elif PurePosixPath(p["path"]).name == ".gitlab-ci.yml":
                records = [ci(text)]
            else:
                lines = text.splitlines()
                start = p["start_line"] - 1
                chosen = lines[start : start + p["tail_lines"]]
                warnings = ["CONTENT_TRUNCATED"] if start or len(lines) > len(chosen) else []
                records = [
                    {
                        "path": p["path"],
                        "ref": p["ref"],
                        "start_line": p["start_line"],
                        "content": "\n".join(chosen),
                        "content_revision": hashlib.sha256(text.encode()).hexdigest(),
                    }
                ]
        elif op == "trace":
            text = a.trace(project, p["job_id"])
            lines = text.splitlines()
            warnings = ["CONTENT_TRUNCATED"] if len(lines) > p["tail_lines"] else []
            records = [{"job_id": p["job_id"], "tail": lines[-p["tail_lines"] :]}]
        else:
            records = [
                a.project(project)
                if op == "project"
                else a.commit(project, p["ref"])
                if op == "commit"
                else a.pipeline(project, p["pipeline_id"])
            ]
        # Exclude variables, runners and nested credentials in platform objects.
        if op in {"projects", "project"}:
            records = [
                select(
                    r,
                    "id name path path_with_namespace default_branch "
                    "description archived last_activity_at",
                )
                for r in records
            ]
        elif op in {
            "pipeline",
            "pipelines",
            "jobs",
            "project_jobs",
            "branch_jobs",
            "pipeline_bridges",
        }:
            safe_records = []
            for record in records:
                safe = select(
                    record,
                    "id status ref sha name stage created_at updated_at "
                    "started_at finished_at duration failure_reason allow_failure tag source",
                )
                if any(
                    not isinstance(v, (str, int, float, bool, type(None))) for v in safe.values()
                ):
                    raise DceError(ErrorCode.API_INCOMPATIBLE, "Unexpected Job metadata shape.")
                for field in ("pipeline", "downstream_pipeline"):
                    nested = record.get(field)
                    if nested is not None:
                        if not isinstance(nested, dict):
                            raise DceError(
                                ErrorCode.API_INCOMPATIBLE, "Unexpected pipeline identity."
                            )
                        safe[field] = select(nested, "id project_id status ref sha source")
                        if any(
                            not isinstance(v, (str, int, float, bool, type(None)))
                            for v in safe[field].values()
                        ):
                            raise DceError(
                                ErrorCode.API_INCOMPATIBLE, "Unexpected pipeline metadata."
                            )
                safe_records.append(safe)
            records = safe_records
        elif op == "commit":
            records = [
                select(r, "id short_id title message parent_ids authored_date committed_date")
                for r in records
            ]
        return records, more, warnings, None, ""

    def zentao(
        self, a: ZenTao, p: dict[str, Any]
    ) -> tuple[Any, bool, list[str], bytes | None, str]:
        op, warnings, more = p["operation"], [], False
        if op in {"projects", "products"}:
            ids = self.scope.zentao_projects if op == "projects" else self.scope.zentao_products
            selected, more = self.page([{"id": i} for i in sorted(ids)], p)
            records = [a.resource(op, i["id"]) for i in selected]
            records = [
                r for r in records if p["search"].casefold() in str(r.get("name", "")).casefold()
            ]
        elif op in {"project", "product"}:
            kind = op + "s"
            records = [a.resource(kind, p[op + "_id"])]
        elif op == "module_tree":
            records = a.modules(p["product_id"], p["module_type"])
            records = [
                r
                for r in records
                if p["search"].casefold()
                in (str(r.get("name", "")) + " " + str(r.get("short", ""))).casefold()
            ]
            records, more = self.page(records, p)
        elif op in {"bugs", "modules"}:
            parent = "projects" if p["project_id"] else "products"
            parent_id = p["project_id"] or p["product_id"]
            data = a.reader.json(
                f"{a.prefix}/{parent}/{key(parent_id)}/bugs",
                kind="zentao",
                params={"page": p["page"], "limit": p["limit"]},
            )
            records = data.get("bugs")
            if not isinstance(records, list) or not all(isinstance(r, dict) for r in records):
                raise DceError(ErrorCode.API_INCOMPATIBLE, "Unexpected ZenTao Bug collection.")
            more = len(records) >= p["limit"]
            if len(records) > p["limit"]:
                records = records[: p["limit"]]
                warnings.append("UPSTREAM_PAGE_LIMIT_EXCEEDED")
            if self.scope.project_mode:
                filtered = []
                for record in records:
                    try:
                        self.scope.check_bug(record)
                        filtered.append(record)
                    except DceError:
                        pass
                if len(filtered) != len(records):
                    warnings.append("BUGS_OUTSIDE_OR_UNVERIFIABLE_SCOPE_OMITTED")
                records = filtered
            if op == "modules":
                records = [
                    {"module": r["module"], "bug_id": r.get("id")}
                    for r in records
                    if r.get("module")
                ]
                warnings.append("PARTIAL_MODULE_INVENTORY_FROM_BUG_PAGE")
        else:
            bug = a.bug(p["bug_id"])
            self.scope.check_bug(bug, p["bug_id"])
            if self.scope.project_mode:
                bug = {
                    **bug,
                    **{
                        k: external_id(bug.get(k + "_id", bug.get(k)))
                        for k in ("project", "product", "module")
                    },
                    "id": external_id(bug["id"]),
                }
            text, sources = a.parse_steps(bug)
            if op == "image":
                if p["asset_index"] >= len(sources):
                    raise DceError(ErrorCode.NOT_FOUND, "Attachment index does not exist.")
                content, mime = a.image_content(sources[p["asset_index"]])
                return (
                    [
                        {
                            "bug_id": p["bug_id"],
                            "asset_index": p["asset_index"],
                            "mime": mime,
                            "bytes": len(content),
                        }
                    ],
                    False,
                    [],
                    content,
                    mime,
                )
            if op == "attachments":
                records = [
                    {"bug_id": p["bug_id"], "asset_index": i, "image_delivery": "not_delivered"}
                    for i in range(len(sources))
                ]
                records, more = self.page(records, p)
            else:
                records = [
                    {
                        **select(
                            bug,
                            "id title project product module status severity pri "
                            "openedDate lastEditedDate",
                        ),
                        "steps": text[:1800],
                    }
                ]
                if len(text) > 1800:
                    warnings.append("CONTENT_TRUNCATED")
        if op in {"projects", "project", "products", "product", "bugs"}:
            records = [
                select(
                    r, "id name title code project product module status lastEditedDate openedDate"
                )
                for r in records
            ]
        return records, more, warnings, None, ""

    def portainer(self, a: Portainer, p: dict[str, Any]) -> tuple[Any, bool, list[str], None, str]:
        op, endpoint = p["operation"], p["endpoint_id"]
        if op == "endpoints":
            records = [
                e for e in a.endpoints() if str(e.get("Id")) in self.scope.portainer_endpoints
            ]
        elif op == "endpoint":
            records = [a.endpoint(endpoint)]
        elif op == "stacks":
            records = [s for s in a.stacks() if str(s.get("Id")) in self.scope.portainer_stacks]
        elif op == "stack":
            stack = a.stack(p["stack_id"])
            if self.scope.project_mode and (
                str(stack.get("Id")) != p["stack_id"]
                or str(stack.get("EndpointId")) not in self.scope.portainer_endpoints
            ):
                deny()
            records = [stack]
        elif op in {"stack_file", "stack_service"}:
            stack = a.stack(p["stack_id"])
            if self.scope.project_mode and str(stack.get("Id")) != p["stack_id"]:
                deny()
            if str(stack.get("EndpointId")) != endpoint:
                deny()
            text = a.stack_file(p["stack_id"], endpoint)
            records = (
                [
                    {
                        **compose_service(text, p["service_name"]),
                        "stack_id": p["stack_id"],
                        "endpoint_id": endpoint,
                        "stack_file_revision": hashlib.sha256(text.encode()).hexdigest(),
                    }
                ]
                if op == "stack_service"
                else [compose(text)]
            )
        elif op == "swarm_info":
            swarm = a.docker_info(endpoint)["Swarm"]
            cluster = swarm.get("Cluster") or {}
            if not isinstance(cluster, dict):
                raise DceError(ErrorCode.API_INCOMPATIBLE, "Unexpected Swarm cluster structure.")
            records = [
                {
                    "Swarm": {
                        "NodeID": swarm.get("NodeID"),
                        "LocalNodeState": swarm.get("LocalNodeState"),
                        "Cluster": {"ID": cluster.get("ID")},
                    }
                }
            ]
        elif op in {"service", "services"} and self.scope.project_mode:
            cluster = a.docker_info(endpoint)["Swarm"].get("Cluster", {})
            if not isinstance(cluster, dict) or not cluster.get("ID"):
                deny()
            namespaces = set()
            for stack_id in sorted(self.scope.portainer_stacks):
                stack = a.stack(stack_id)
                if str(stack.get("Id")) != stack_id:
                    deny()
                if str(stack.get("EndpointId")) == endpoint and stack.get("Type") == 1:
                    if stack.get("SwarmId") != cluster["ID"]:
                        raise DceError(ErrorCode.SNAPSHOT_CONFLICT, "Project Stack Swarm is stale.")
                    namespace = stack.get("Namespace") or stack.get("Name")
                    if isinstance(namespace, str) and namespace:
                        namespaces.add(namespace)
            if not namespaces or p["namespace"] is not None and p["namespace"] not in namespaces:
                deny()
            raw = (
                [a.service(endpoint, p["service_id"])]
                if op == "service"
                else a.services(endpoint, p["namespace"])
            )
            matching = []
            for service in raw:
                labels = (service.get("Spec") or {}).get("Labels") or {}
                if not isinstance(labels, dict):
                    deny()
                if labels.get("com.docker.stack.namespace") in namespaces:
                    if op == "service" and str(service.get("ID")) != p["service_id"]:
                        deny()
                    matching.append(service_facts(service))
            if op == "service" and not matching:
                deny()
            records = matching
        elif op == "service":
            records = [service_facts(a.service(endpoint, p["service_id"]))]
        else:
            records = [service_facts(s) for s in a.services(endpoint, p["namespace"])]
        records, more = self.page(records, p)
        return records, more, [], None, ""
